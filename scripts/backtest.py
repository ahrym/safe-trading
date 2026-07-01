"""
=============================================================
SAFE TRADING — BACKTEST COMPLETO
Estratégia: EMA 8/21 Crossover + Filtro RSI + Confirmação de Volume
Mercado: BTC/USDT — Binance Spot — Timeframe 4H
=============================================================

Como rodar:
    python scripts/backtest.py

O script vai:
1. Carregar (ou baixar) dados de BTC/USDT 4H
2. Calcular indicadores técnicos
3. Simular todos os trades com gestão de risco real
4. Salvar gráfico em results/backtest_ema_resultado.png
5. Salvar métricas em results/backtest_ema_resultado.json
6. Imprimir resumo no terminal
"""

import os
import sys
import json
import math
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Renderizar sem interface gráfica (funciona em servidores)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────
# INDICADORES IMPLEMENTADOS DIRETAMENTE (sem pandas_ta)
# Mais robusto e sem problemas de compatibilidade no Windows
# ─────────────────────────────────────────────────────────────

class ta:
    @staticmethod
    def ema(series: pd.Series, length: int) -> pd.Series:
        """Média Móvel Exponencial — dá mais peso aos candles recentes"""
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, length: int) -> pd.Series:
        """Média Móvel Simples — média aritmética dos últimos N candles"""
        return series.rolling(window=length).mean()

    @staticmethod
    def rsi(series: pd.Series, length: int) -> pd.Series:
        """RSI — mede força relativa: >70 sobrecomprado, <30 sobrevendido"""
        delta = series.diff()                              # variação de preço candle a candle
        ganho = delta.clip(lower=0)                        # só as altas (zera as quedas)
        perda = -delta.clip(upper=0)                       # só as quedas (zera as altas)
        media_ganho = ganho.ewm(com=length - 1, adjust=False).mean()
        media_perda = perda.ewm(com=length - 1, adjust=False).mean()
        rs = media_ganho / media_perda.replace(0, np.nan)  # evita divisão por zero
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
        """ATR — mede volatilidade: maior = mercado mais agitado"""
        prev_close = close.shift(1)                        # fechamento do candle anterior
        tr = pd.concat([
            high - low,                                    # amplitude do candle atual
            (high - prev_close).abs(),                     # gap de alta em relação ao fechamento anterior
            (low - prev_close).abs()                       # gap de baixa em relação ao fechamento anterior
        ], axis=1).max(axis=1)                             # True Range = o maior dos três
        return tr.ewm(com=length - 1, adjust=False).mean() # média exponencial do TR

# ─────────────────────────────────────────────────────────────
# PARÂMETROS DA ESTRATÉGIA
# ─────────────────────────────────────────────────────────────
EMA_RAPIDA   = 8      # Período da EMA rápida (responde rápido a novas tendências)
EMA_LENTA    = 21     # Período da EMA lenta (~1 semana de candles 4H)
EMA_MACRO    = 50     # Período da EMA macro (confirma tendência de médio prazo)
RSI_PERIODO  = 14     # Período do RSI (padrão amplamente usado)
RSI_MIN      = 40     # RSI mínimo para entrada (evita mercado sem momentum)
RSI_MAX      = 65     # RSI máximo para entrada (evita entrar sobrecomprado)
ATR_PERIODO  = 14     # Período do ATR (captura volatilidade recente)
STOP_MULT    = 1.5    # Multiplicador do ATR para o stop loss
TP_MULT      = 3.0    # Multiplicador do ATR para o take profit (RR 2:1)
VOL_MEDIA_PER = 20    # Períodos para a média de volume (~3.3 dias de referência)

# ─────────────────────────────────────────────────────────────
# PARÂMETROS DO BACKTEST / GESTÃO DE RISCO
# ─────────────────────────────────────────────────────────────
CAPITAL_INICIAL = 1000.0  # Capital inicial em USDT (simulado)
RISCO_POR_TRADE = 0.01    # 1% do capital arriscado por trade
TAXA_ENTRADA    = 0.001   # 0.1% taxa da corretora ao entrar
TAXA_SAIDA      = 0.001   # 0.1% taxa da corretora ao sair
SLIPPAGE        = 0.0005  # 0.05% slippage por lado (deslizamento de preço)
POS_MAX_PCT     = 0.20    # Teto: no máximo 20% do capital numa única posição

# ─────────────────────────────────────────────────────────────
# CAMINHOS DOS ARQUIVOS
# ─────────────────────────────────────────────────────────────
# Pasta raiz do projeto (um nível acima de scripts/)
PASTA_RAIZ    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DATA    = os.path.join(PASTA_RAIZ, "data")
PASTA_RESULTS = os.path.join(PASTA_RAIZ, "results")
ARQUIVO_CSV   = os.path.join(PASTA_DATA,    "btc_usdt_4h.csv")
ARQUIVO_PNG   = os.path.join(PASTA_RESULTS, "backtest_ema_resultado.png")
ARQUIVO_JSON  = os.path.join(PASTA_RESULTS, "backtest_ema_resultado.json")


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Criar pastas necessárias
# ─────────────────────────────────────────────────────────────
def criar_pastas():
    """Cria as pastas data/ e results/ se ainda não existirem."""
    os.makedirs(PASTA_DATA,    exist_ok=True)
    os.makedirs(PASTA_RESULTS, exist_ok=True)
    print("✔ Pastas data/ e results/ verificadas/criadas")


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Carregar ou baixar dados de mercado
# ─────────────────────────────────────────────────────────────
def carregar_dados() -> pd.DataFrame:
    """
    Tenta carregar dados do CSV local (data/btc_usdt_4h.csv).
    Se o arquivo não existir, baixa automaticamente via CCXT (Binance)
    e salva o CSV para uso futuro.

    Retorna:
        DataFrame com colunas: timestamp, open, high, low, close, volume
    """
    # Tentar carregar do CSV primeiro (mais rápido, sem internet)
    if os.path.exists(ARQUIVO_CSV):
        print(f"✔ Carregando dados do arquivo: {ARQUIVO_CSV}")
        df = pd.read_csv(ARQUIVO_CSV, parse_dates=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        inicio = df["timestamp"].iloc[0].date()
        fim    = df["timestamp"].iloc[-1].date()
        print(f"  → {len(df)} candles carregados ({inicio} até {fim})")
        return df

    # Se não existir CSV, baixar via CCXT da Binance
    print("⚠ Arquivo CSV não encontrado. Baixando dados via CCXT (Binance)...")
    try:
        import ccxt
    except ImportError:
        print("ERRO: ccxt não instalado. Rode: pip install ccxt")
        sys.exit(1)

    exchange = ccxt.binance({"enableRateLimit": True})

    # Baixar 1500 candles de 4H (≈ 250 dias de dados)
    print("  → Conectando à Binance... pode demorar alguns segundos")
    candles_brutos = exchange.fetch_ohlcv("BTC/USDT", timeframe="4h", limit=1500)

    if not candles_brutos:
        print("ERRO: Nenhum dado retornado pela Binance.")
        sys.exit(1)

    # Converter lista de listas para DataFrame
    df = pd.DataFrame(
        candles_brutos,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    # Converter timestamp de milissegundos para datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)  # Remover timezone

    # Salvar CSV para economizar tempo nas próximas execuções
    df.to_csv(ARQUIVO_CSV, index=False)
    inicio = df["timestamp"].iloc[0].date()
    fim    = df["timestamp"].iloc[-1].date()
    print(f"✔ {len(df)} candles baixados e salvos em: {ARQUIVO_CSV}")
    print(f"  → Período: {inicio} até {fim}")

    return df


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Calcular indicadores técnicos
# ─────────────────────────────────────────────────────────────
def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todos os indicadores técnicos necessários para a estratégia:
    - EMA(8), EMA(21), EMA(50) — médias móveis exponenciais
    - RSI(14) — índice de força relativa
    - ATR(14) — average true range (medida de volatilidade)
    - Média de volume (SMA 20 períodos)

    IMPORTANTE: Os indicadores são calculados aqui, mas usados com .shift(1)
    na função gerar_sinais() para evitar look-ahead bias.
    """
    print("Calculando indicadores técnicos...")

    # Garantir que os dados estão em ordem cronológica
    df = df.sort_values("timestamp").reset_index(drop=True)

    # ── EMAs — Médias Móveis Exponenciais ─────────────────────
    df["ema8"]  = ta.ema(df["close"], length=EMA_RAPIDA)
    df["ema21"] = ta.ema(df["close"], length=EMA_LENTA)
    df["ema50"] = ta.ema(df["close"], length=EMA_MACRO)

    # ── RSI — Índice de Força Relativa ───────────────────────
    df["rsi"] = ta.rsi(df["close"], length=RSI_PERIODO)

    # ── ATR — Average True Range (volatilidade) ──────────────
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIODO)

    # ── Média de Volume dos últimos 20 candles ───────────────
    df["vol_media"] = ta.sma(df["volume"], length=VOL_MEDIA_PER)

    # Contar quantos candles têm todos os indicadores calculados
    candles_validos = df[["ema50", "rsi", "atr", "vol_media"]].notna().all(axis=1).sum()
    print(f"  → Indicadores calculados. Candles completos (sem NaN): {candles_validos}")

    if candles_validos < 50:
        print("AVISO: Poucos candles com indicadores completos. Backtest pode ter resultados limitados.")

    return df


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Gerar sinais de compra e venda
# ─────────────────────────────────────────────────────────────
def gerar_sinais(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera sinais de compra usando .shift(1) e .shift(2) em TODOS os indicadores.

    POR QUÊ .shift()?
    No trading real, quando um candle fecha, só temos acesso aos dados
    daquele candle — não do candle atual (que ainda está se formando).
    - shift(1) = dados do candle que acabou de fechar (candle anterior)
    - shift(2) = dados de dois candles atrás

    Sem shift, estaríamos usando o valor "futuro" do indicador para decidir
    a entrada, o que é trapaça (look-ahead bias) e invalida o backtest.

    CONDIÇÕES PARA COMPRA (todas devem ser verdadeiras):
    1. EMA(8) cruzou acima de EMA(21) no candle anterior
    2. RSI estava entre 40 e 65 no candle anterior
    3. Volume do candle atual maior que média dos 20 candles anteriores
    4. Preço estava acima da EMA(50) no candle anterior (tendência de alta)
    """
    print("Gerando sinais de entrada com proteção contra look-ahead bias...")

    # ── Condição 1: Cruzamento de EMA ─────────────────────────
    # No candle anterior (shift 1): EMA8 está ACIMA de EMA21
    # Dois candles atrás (shift 2): EMA8 estava ABAIXO de EMA21
    # → Isso significa que o cruzamento aconteceu no candle anterior
    cruzamento_alta = (
        (df["ema8"].shift(1) > df["ema21"].shift(1)) &    # candle anterior: EMA8 acima
        (df["ema8"].shift(2) <= df["ema21"].shift(2))      # dois atrás: EMA8 abaixo (cruzou!)
    )

    # ── Condição 2: RSI na zona de momentum válido ────────────
    # RSI entre 40 e 65 no candle anterior
    # 40 = mínimo (mercado tem momentum), 65 = máximo (não sobrecomprado)
    rsi_valido = (
        (df["rsi"].shift(1) >= RSI_MIN) &
        (df["rsi"].shift(1) <= RSI_MAX)
    )

    # ── Condição 3: Volume acima da média ─────────────────────
    # Volume do candle atual maior que média dos 20 candles anteriores
    # (a média usa shift para não incluir o volume atual no cálculo)
    volume_confirmado = df["volume"] > df["vol_media"].shift(1)

    # ── Condição 4: Tendência macro (filtro anti-bear) ────────
    # Preço de fechamento no candle anterior estava acima da EMA(50)
    # Evita entrar em tendência de baixa de médio prazo
    tendencia_alta = df["close"].shift(1) > df["ema50"].shift(1)

    # ── Sinal final: TODAS as 4 condições verdadeiras ─────────
    df["sinal_compra"] = (
        cruzamento_alta &
        rsi_valido &
        volume_confirmado &
        tendencia_alta
    )

    # ── Sinal de saída por reversão: EMA crossdown ────────────
    # EMA8 cruzou ABAIXO de EMA21 no candle anterior
    # → Indica possível reversão de tendência
    df["sinal_crossdown"] = (
        (df["ema8"].shift(1) < df["ema21"].shift(1)) &
        (df["ema8"].shift(2) >= df["ema21"].shift(2))
    )

    # Preencher valores NaN com False (candles sem dados suficientes)
    df["sinal_compra"]   = df["sinal_compra"].fillna(False)
    df["sinal_crossdown"] = df["sinal_crossdown"].fillna(False)

    total_sinais = df["sinal_compra"].sum()
    print(f"  → {total_sinais} sinais de compra encontrados no período")

    return df


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Simular os trades (coração do backtest)
# ─────────────────────────────────────────────────────────────
def simular_trades(df: pd.DataFrame):
    """
    Percorre cada candle e simula a execução dos trades com gestão de risco real.

    LÓGICA DE EXECUÇÃO:
    - Sinal gerado no candle N → entrada no OPEN do candle N+1
    - Stop Loss = entrada - (1.5 × ATR do candle de sinal)
    - Take Profit = entrada + (3.0 × ATR do candle de sinal)
    - Saída também ocorre se EMA8 cruzar abaixo de EMA21
    - Taxas e slippage aplicados em toda entrada e saída

    GESTÃO DE RISCO:
    - Tamanho da posição = (1% do capital) / distância_até_stop
    - Limite: posição não pode exceder 20% do capital total
    - Máximo 1 trade aberto simultaneamente

    Retorna:
        lista_trades (list): detalhes de cada trade finalizado
        curva_equity (list): evolução do capital candle a candle
    """
    print("Simulando trades...")

    # Remover candles com indicadores incompletos (início da série)
    df_valido = df.dropna(
        subset=["ema8", "ema21", "ema50", "rsi", "atr", "vol_media"]
    ).copy().reset_index(drop=True)

    if len(df_valido) < 10:
        print("ERRO: Dados insuficientes para simular trades (menos de 10 candles válidos).")
        sys.exit(1)

    # Variáveis de estado do backtest
    capital        = CAPITAL_INICIAL   # Capital disponível em USDT
    posicao_aberta = False             # Temos posição aberta agora?
    trade_atual    = {}                # Dados do trade em andamento
    lista_trades   = []                # Todos os trades finalizados
    curva_equity   = []                # Histórico do capital ao longo do tempo

    # ── Loop principal: percorrer candle a candle ─────────────
    for i in range(len(df_valido)):
        candle        = df_valido.iloc[i]
        ts_atual      = candle["timestamp"]
        preco_open    = candle["open"]
        preco_high    = candle["high"]
        preco_low     = candle["low"]
        preco_close   = candle["close"]

        # ── Verificar saída se temos posição aberta ───────────
        if posicao_aberta:
            saiu         = False
            preco_saida  = None
            motivo_saida = None

            # Verificar Stop Loss: o mínimo do candle tocou ou cruzou o stop?
            if preco_low <= trade_atual["stop_loss"]:
                preco_saida  = trade_atual["stop_loss"]  # Saída exatamente no stop
                motivo_saida = "stop_loss"
                saiu         = True

            # Verificar Take Profit: o máximo do candle tocou ou cruzou o alvo?
            elif preco_high >= trade_atual["take_profit"]:
                preco_saida  = trade_atual["take_profit"]  # Saída exatamente no TP
                motivo_saida = "take_profit"
                saiu         = True

            # Verificar Sinal Inverso: EMA cruzou para baixo?
            # Saímos no open deste candle (primeiro preço disponível após o sinal)
            elif candle["sinal_crossdown"]:
                preco_saida  = preco_open
                motivo_saida = "sinal_inverso"
                saiu         = True

            # Se saiu, calcular resultado do trade
            if saiu:
                # Custo total de saída: taxa da corretora + slippage
                # (o preço efetivo de saída é ligeiramente pior que o alvo)
                custo_saida_pct  = TAXA_SAIDA + SLIPPAGE
                preco_saida_real = preco_saida * (1 - custo_saida_pct)

                # Calcular P&L (lucro ou prejuízo)
                quantidade     = trade_atual["quantidade"]
                preco_entrada  = trade_atual["preco_entrada_real"]
                valor_saida    = quantidade * preco_saida_real
                valor_entrada  = quantidade * preco_entrada  # já foi debitado no momento da entrada

                pnl_usdt   = valor_saida - valor_entrada
                retorno_pct = (preco_saida_real / preco_entrada - 1) * 100

                # Retornar o valor da posição (com lucro ou prejuízo) ao capital
                capital += valor_saida

                # Registrar trade finalizado
                lista_trades.append({
                    "entrada_timestamp": str(trade_atual["ts_entrada"]),
                    "saida_timestamp":   str(ts_atual),
                    "preco_entrada":     round(preco_entrada, 2),
                    "preco_saida":       round(preco_saida_real, 2),
                    "stop_loss":         round(trade_atual["stop_loss"], 2),
                    "take_profit":       round(trade_atual["take_profit"], 2),
                    "quantidade_btc":    round(quantidade, 6),
                    "pnl_usdt":          round(pnl_usdt, 2),
                    "retorno_pct":       round(retorno_pct, 4),
                    "resultado":         "win" if pnl_usdt > 0 else "loss",
                    "motivo_saida":      motivo_saida,
                    "duracao_candles":   i - trade_atual["idx_entrada"],
                    "capital_apos":      round(capital, 2),
                })

                posicao_aberta = False
                trade_atual    = {}

        # ── Verificar entrada se não temos posição aberta ─────
        # Condição: sinal de compra neste candle E existe um próximo candle
        if not posicao_aberta and candle["sinal_compra"] and (i + 1) < len(df_valido):
            # Entrar no OPEN do candle seguinte ao sinal
            proximo = df_valido.iloc[i + 1]
            preco_entrada = proximo["open"]

            # Custo de entrada: taxa + slippage (preço efetivo fica um pouco acima)
            custo_entrada_pct  = TAXA_ENTRADA + SLIPPAGE
            preco_entrada_real = preco_entrada * (1 + custo_entrada_pct)

            # Stop e Take Profit calculados com o ATR do candle de SINAL (não do próximo)
            atr_sinal   = candle["atr"]
            stop_loss   = preco_entrada_real - (STOP_MULT * atr_sinal)
            take_profit = preco_entrada_real + (TP_MULT  * atr_sinal)

            # Cálculo do tamanho da posição baseado no risco de 1%
            risco_usdt     = capital * RISCO_POR_TRADE         # Ex: $1000 × 1% = $10
            distancia_stop = preco_entrada_real - stop_loss    # Quantos $ até o stop

            # Proteção: evitar divisão por zero
            if distancia_stop <= 0:
                continue

            # Quantidade de BTC = quanto risco disposto / risco por unidade
            quantidade     = risco_usdt / distancia_stop
            valor_posicao  = quantidade * preco_entrada_real

            # Aplicar teto: não usar mais de 20% do capital numa posição
            if valor_posicao > capital * POS_MAX_PCT:
                quantidade    = (capital * POS_MAX_PCT) / preco_entrada_real
                valor_posicao = capital * POS_MAX_PCT

            # Verificar se temos capital suficiente para abrir a posição
            if valor_posicao > capital or valor_posicao <= 0:
                continue

            # Debitar o valor da posição do capital disponível
            capital -= valor_posicao

            # Guardar dados do trade em andamento
            trade_atual = {
                "ts_entrada":        proximo["timestamp"],
                "idx_entrada":       i + 1,
                "preco_entrada_real": preco_entrada_real,
                "stop_loss":         stop_loss,
                "take_profit":       take_profit,
                "quantidade":        quantidade,
                "atr_entrada":       atr_sinal,
            }
            posicao_aberta = True

        # ── Registrar equidade ao final do candle ─────────────
        # Se há posição aberta: avaliar a mercado com o preço de fechamento
        if posicao_aberta:
            valor_em_btc    = trade_atual["quantidade"] * preco_close
            capital_total   = capital + valor_em_btc
        else:
            capital_total   = capital

        curva_equity.append({
            "timestamp": ts_atual,
            "capital":   round(capital_total, 2),
        })

    # ── Fechar posição em aberto no final do período ──────────
    if posicao_aberta and len(df_valido) > 0:
        ultimo          = df_valido.iloc[-1]
        custo_saida     = TAXA_SAIDA + SLIPPAGE
        preco_saida_final = ultimo["close"] * (1 - custo_saida)
        quantidade      = trade_atual["quantidade"]
        preco_entrada   = trade_atual["preco_entrada_real"]
        valor_saida     = quantidade * preco_saida_final
        pnl_usdt        = valor_saida - (quantidade * preco_entrada)
        capital        += valor_saida
        retorno_pct     = (preco_saida_final / preco_entrada - 1) * 100

        lista_trades.append({
            "entrada_timestamp": str(trade_atual["ts_entrada"]),
            "saida_timestamp":   str(ultimo["timestamp"]),
            "preco_entrada":     round(preco_entrada, 2),
            "preco_saida":       round(preco_saida_final, 2),
            "stop_loss":         round(trade_atual["stop_loss"], 2),
            "take_profit":       round(trade_atual["take_profit"], 2),
            "quantidade_btc":    round(quantidade, 6),
            "pnl_usdt":          round(pnl_usdt, 2),
            "retorno_pct":       round(retorno_pct, 4),
            "resultado":         "win" if pnl_usdt > 0 else "loss",
            "motivo_saida":      "fim_periodo",
            "duracao_candles":   len(df_valido) - 1 - trade_atual["idx_entrada"],
            "capital_apos":      round(capital, 2),
        })

    print(f"  → {len(lista_trades)} trades simulados. Capital final: ${capital:.2f}")
    return lista_trades, curva_equity


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Calcular métricas de performance
# ─────────────────────────────────────────────────────────────
def calcular_metricas(lista_trades: list, curva_equity: list) -> dict:
    """
    Calcula todas as métricas de performance do backtest:

    - Win Rate: % de trades com lucro
    - Profit Factor: soma dos ganhos / soma das perdas
    - Sharpe Ratio: retorno ajustado pelo risco (anualizado)
    - Max Drawdown: maior queda da curva de capital desde o pico
    - Duração média: quantos candles os trades duraram em média
    """
    if not lista_trades:
        return {"erro": "Nenhum trade realizado no período"}

    # Separar ganhos e perdas
    ganhos = [t["pnl_usdt"] for t in lista_trades if t["pnl_usdt"] > 0]
    perdas = [t["pnl_usdt"] for t in lista_trades if t["pnl_usdt"] <= 0]

    total_trades     = len(lista_trades)
    total_vencedores = len(ganhos)
    total_perdedores = len(perdas)

    # Win Rate: porcentagem de trades que terminaram no lucro
    win_rate = (total_vencedores / total_trades * 100) if total_trades > 0 else 0

    # Soma de ganhos e perdas
    soma_ganhos = sum(ganhos) if ganhos else 0
    soma_perdas = abs(sum(perdas)) if perdas else 0

    # Profit Factor: quantos $ ganhamos para cada $ perdido
    # PF > 1.5 é considerado bom
    profit_factor = (soma_ganhos / soma_perdas) if soma_perdas > 0 else float("inf")

    # Retorno total do período
    capital_final = lista_trades[-1]["capital_apos"] if lista_trades else CAPITAL_INICIAL
    retorno_total = (capital_final / CAPITAL_INICIAL - 1) * 100

    # ── Sharpe Ratio Anualizado ───────────────────────────────
    # Mede o retorno ajustado pelo risco
    # Sharpe > 1.0 é aceitável, > 1.5 é bom, > 2.0 é ótimo
    retornos = [t["retorno_pct"] / 100 for t in lista_trades]
    if len(retornos) > 1:
        media_ret  = np.mean(retornos)
        desvio_ret = np.std(retornos, ddof=1)

        # Estimar quantos trades por ano para anualizar
        if len(curva_equity) > 0:
            # Candles de 4H: 6 candles/dia × 365 dias = 2190 candles/ano
            candles_total   = len(curva_equity)
            anos_total      = candles_total / 2190
            trades_por_ano  = total_trades / max(anos_total, 0.1)
        else:
            trades_por_ano  = total_trades  # Fallback

        fator_anual = math.sqrt(max(trades_por_ano, 1))
        sharpe = (media_ret / desvio_ret * fator_anual) if desvio_ret > 0 else 0.0
    else:
        sharpe = 0.0

    # ── Max Drawdown ──────────────────────────────────────────
    # Maior queda percentual desde o último pico da curva de capital
    if curva_equity:
        capitais   = [c["capital"] for c in curva_equity]
        pico_atual = capitais[0]
        max_dd     = 0.0
        for cap in capitais:
            if cap > pico_atual:
                pico_atual = cap
            dd = (pico_atual - cap) / pico_atual * 100
            if dd > max_dd:
                max_dd = dd
    else:
        max_dd = 0.0

    # Médias de ganho e perda por trade (em %)
    media_ganho = np.mean([t["retorno_pct"] for t in lista_trades if t["pnl_usdt"] > 0]) if ganhos else 0.0
    media_perda = np.mean([t["retorno_pct"] for t in lista_trades if t["pnl_usdt"] <= 0]) if perdas else 0.0

    # Duração média dos trades (em candles de 4H)
    duracao_media = np.mean([t["duracao_candles"] for t in lista_trades]) if lista_trades else 0.0

    return {
        "total_trades":          total_trades,
        "total_vencedores":      total_vencedores,
        "total_perdedores":      total_perdedores,
        "win_rate_pct":          round(win_rate, 2),
        "profit_factor":         round(profit_factor, 4),
        "retorno_total_pct":     round(retorno_total, 2),
        "capital_inicial":       CAPITAL_INICIAL,
        "capital_final":         round(capital_final, 2),
        "sharpe_ratio":          round(sharpe, 4),
        "max_drawdown_pct":      round(max_dd, 2),
        "media_ganho_pct":       round(media_ganho, 4),
        "media_perda_pct":       round(media_perda, 4),
        "duracao_media_candles": round(duracao_media, 1),
    }


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Gerar gráfico visual do backtest
# ─────────────────────────────────────────────────────────────
def gerar_grafico(df: pd.DataFrame, lista_trades: list, curva_equity: list):
    """
    Gera um gráfico com 3 painéis e salva em results/backtest_ema_resultado.png:

    Painel 1 (topo): Curva de equity — evolução do capital ao longo do tempo
                     Área verde = capital acima do inicial, vermelha = abaixo

    Painel 2 (meio): Gráfico de preço com EMAs sobrepostas
                     ▲ verde = entrada em posição
                     ▼ verde/vermelho = saída com lucro/prejuízo

    Painel 3 (baixo): RSI com as zonas 40 e 65 marcadas (zona válida de entrada)
    """
    print("Gerando gráfico visual...")

    # Preparar dados — usar apenas candles com indicadores completos
    df_plot = df.dropna(subset=["ema8", "ema21", "ema50", "rsi"]).copy()
    df_plot = df_plot.sort_values("timestamp").reset_index(drop=True)

    # Limitar a 600 candles para o gráfico ficar legível
    if len(df_plot) > 600:
        df_plot    = df_plot.tail(600).reset_index(drop=True)
        data_corte = df_plot["timestamp"].iloc[0]
    else:
        data_corte = df_plot["timestamp"].iloc[0]

    # Filtrar trades que estão dentro do período do gráfico
    trades_plot = []
    for t in lista_trades:
        try:
            ts_entrada = pd.to_datetime(t["entrada_timestamp"])
            if ts_entrada >= data_corte:
                trades_plot.append(t)
        except Exception:
            pass

    # Converter curva de equity para DataFrame
    eq_df = pd.DataFrame(curva_equity) if curva_equity else pd.DataFrame()

    # ── Criar figura com tema escuro ──────────────────────────
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1,
        figsize=(16, 12),
        gridspec_kw={"height_ratios": [1.5, 3.0, 1.5]},
        sharex=False
    )
    COR_FUNDO    = "#0d1117"
    COR_PAINEL   = "#161b22"
    COR_BORDA    = "#30363d"
    COR_TEXTO    = "#c9d1d9"

    fig.patch.set_facecolor(COR_FUNDO)
    for ax in (ax1, ax2, ax3):
        ax.set_facecolor(COR_PAINEL)
        ax.tick_params(colors=COR_TEXTO, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(COR_BORDA)

    # ── Painel 1: Curva de Equity ─────────────────────────────
    if not eq_df.empty:
        ax1.plot(eq_df["timestamp"], eq_df["capital"],
                 color="#58a6ff", linewidth=1.5, label="Capital")
        ax1.axhline(y=CAPITAL_INICIAL, color="#6e7681",
                    linestyle="--", linewidth=0.8, alpha=0.8, label="Capital inicial")
        # Área verde onde capital > inicial (lucro)
        ax1.fill_between(
            eq_df["timestamp"], eq_df["capital"], CAPITAL_INICIAL,
            where=(eq_df["capital"] >= CAPITAL_INICIAL),
            alpha=0.2, color="#3fb950"
        )
        # Área vermelha onde capital < inicial (prejuízo)
        ax1.fill_between(
            eq_df["timestamp"], eq_df["capital"], CAPITAL_INICIAL,
            where=(eq_df["capital"] < CAPITAL_INICIAL),
            alpha=0.2, color="#f85149"
        )

    ax1.set_ylabel("Capital (USDT)", color=COR_TEXTO, fontsize=9)
    ax1.set_title(
        "Safe Trading — Backtest: EMA 8/21 + RSI + Volume (BTC/USDT 4H)",
        color="#e6edf3", fontsize=12, fontweight="bold", pad=10
    )
    ax1.legend(loc="upper left", facecolor="#21262d", edgecolor=COR_BORDA,
               labelcolor=COR_TEXTO, fontsize=8)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # ── Painel 2: Preço + EMAs + Marcações de Trades ─────────
    datas = df_plot["timestamp"]
    ax2.plot(datas, df_plot["close"],  color="#c9d1d9", linewidth=0.7, alpha=0.8, label="Preço")
    ax2.plot(datas, df_plot["ema8"],   color="#ffa657", linewidth=1.3, label=f"EMA {EMA_RAPIDA}")
    ax2.plot(datas, df_plot["ema21"],  color="#79c0ff", linewidth=1.3, label=f"EMA {EMA_LENTA}")
    ax2.plot(datas, df_plot["ema50"],  color="#d2a8ff", linewidth=1.0,
             linestyle="--", alpha=0.7, label=f"EMA {EMA_MACRO}")

    # Marcar entradas (▲) e saídas (▼) dos trades no gráfico
    for trade in trades_plot:
        try:
            ts_entrada = pd.to_datetime(trade["entrada_timestamp"])
            ts_saida   = pd.to_datetime(trade["saida_timestamp"])
            cor_saida  = "#3fb950" if trade["resultado"] == "win" else "#f85149"
            p_entrada  = trade["preco_entrada"]
            p_saida    = trade["preco_saida"]

            # Seta de entrada: triângulo verde apontando para cima
            ax2.annotate(
                "▲",
                xy=(ts_entrada, p_entrada),
                color="#3fb950", fontsize=9, ha="center", va="top",
                fontweight="bold"
            )
            # Seta de saída: triângulo apontando para baixo (cor varia)
            ax2.annotate(
                "▼",
                xy=(ts_saida, p_saida),
                color=cor_saida, fontsize=9, ha="center", va="bottom",
                fontweight="bold"
            )
        except Exception:
            pass  # Ignorar erros de formatação individual

    ax2.set_ylabel("Preço BTC/USDT ($)", color=COR_TEXTO, fontsize=9)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # Legenda personalizada com os símbolos de entrada/saída
    legenda_itens = [
        Line2D([0], [0], color="#c9d1d9", linewidth=0.7,    label="Preço"),
        Line2D([0], [0], color="#ffa657", linewidth=1.3,    label=f"EMA {EMA_RAPIDA}"),
        Line2D([0], [0], color="#79c0ff", linewidth=1.3,    label=f"EMA {EMA_LENTA}"),
        Line2D([0], [0], color="#d2a8ff", linewidth=1.0,
               linestyle="--",                              label=f"EMA {EMA_MACRO}"),
        Line2D([0], [0], marker="^", color="#3fb950",
               markersize=8, linestyle="None",              label="Entrada"),
        Line2D([0], [0], marker="v", color="#f85149",
               markersize=8, linestyle="None",              label="Saída (loss)"),
        Line2D([0], [0], marker="v", color="#3fb950",
               markersize=8, linestyle="None",              label="Saída (win)"),
    ]
    ax2.legend(handles=legenda_itens, loc="upper left", facecolor="#21262d",
               edgecolor=COR_BORDA, labelcolor=COR_TEXTO, fontsize=7, ncol=4)

    # ── Painel 3: RSI com zonas de entrada ───────────────────
    ax3.plot(datas, df_plot["rsi"], color="#e3b341", linewidth=1.2, label="RSI 14")

    # Zona válida de entrada: entre RSI_MIN e RSI_MAX
    ax3.axhline(y=RSI_MIN, color="#3fb950", linestyle="--", linewidth=0.8, alpha=0.9,
                label=f"Mínimo entrada ({RSI_MIN})")
    ax3.axhline(y=RSI_MAX, color="#f85149", linestyle="--", linewidth=0.8, alpha=0.9,
                label=f"Máximo entrada ({RSI_MAX})")
    ax3.axhline(y=70, color="#f85149", linestyle=":",  linewidth=0.6, alpha=0.5)
    ax3.axhline(y=30, color="#3fb950", linestyle=":",  linewidth=0.6, alpha=0.5)

    # Sombrear a zona válida de entrada (RSI_MIN a RSI_MAX)
    ax3.fill_between(datas, RSI_MIN, RSI_MAX, alpha=0.10, color="#58a6ff",
                     label=f"Zona válida ({RSI_MIN}–{RSI_MAX})")

    ax3.set_ylim(0, 100)
    ax3.set_ylabel("RSI", color=COR_TEXTO, fontsize=9)
    ax3.legend(loc="upper left", facecolor="#21262d", edgecolor=COR_BORDA,
               labelcolor=COR_TEXTO, fontsize=7, ncol=3)

    # ── Formatação do eixo X ──────────────────────────────────
    for ax in (ax2, ax3):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    if not eq_df.empty:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

    plt.tight_layout(pad=1.5)

    # Salvar o gráfico em PNG de alta resolução
    fig.savefig(ARQUIVO_PNG, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  → Gráfico salvo em: {ARQUIVO_PNG}")


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Salvar resultados em JSON
# ─────────────────────────────────────────────────────────────
def salvar_json(df: pd.DataFrame, lista_trades: list, metricas: dict):
    """Salva todos os resultados e detalhes dos trades em formato JSON."""

    # Extrair datas do período (ignorando NaNs)
    df_valido   = df.dropna(subset=["ema8"]).copy()
    data_inicio = str(df_valido["timestamp"].iloc[0].date())  if len(df_valido) > 0 else "N/A"
    data_fim    = str(df_valido["timestamp"].iloc[-1].date()) if len(df_valido) > 0 else "N/A"

    # Montar estrutura completa do resultado
    resultado = {
        "estrategia":      "EMA 8/21 + RSI + Volume",
        "mercado":         "BTC/USDT 4h",
        "periodo":         {"inicio": data_inicio, "fim": data_fim},
        "capital_inicial": CAPITAL_INICIAL,
        "capital_final":   metricas.get("capital_final", CAPITAL_INICIAL),
        "parametros": {
            "ema_rapida":      EMA_RAPIDA,
            "ema_lenta":       EMA_LENTA,
            "ema_macro":       EMA_MACRO,
            "rsi_periodo":     RSI_PERIODO,
            "rsi_min":         RSI_MIN,
            "rsi_max":         RSI_MAX,
            "atr_periodo":     ATR_PERIODO,
            "stop_mult":       STOP_MULT,
            "tp_mult":         TP_MULT,
            "risco_por_trade": RISCO_POR_TRADE,
            "taxa_entrada":    TAXA_ENTRADA,
            "taxa_saida":      TAXA_SAIDA,
            "slippage":        SLIPPAGE,
        },
        "metricas": metricas,
        "trades":   lista_trades,
    }

    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

    print(f"  → JSON salvo em: {ARQUIVO_JSON}")


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Imprimir resumo no terminal
# ─────────────────────────────────────────────────────────────
def imprimir_resumo(metricas: dict):
    """Exibe um resumo bonito e formatado das métricas no terminal."""

    linha = "=" * 60
    print(f"\n{linha}")
    print("  SAFE TRADING — RESULTADO DO BACKTEST")
    print(f"  Estratégia: EMA 8/21 + RSI + Volume (BTC/USDT 4H)")
    print(f"{linha}")

    # Capital
    print(f"  Capital Inicial:        ${metricas.get('capital_inicial', 0):>10,.2f}")
    print(f"  Capital Final:          ${metricas.get('capital_final', 0):>10,.2f}")
    retorno = metricas.get("retorno_total_pct", 0)
    sinal   = "+" if retorno >= 0 else ""
    print(f"  Retorno Total:          {sinal}{retorno:>9.2f}%")
    print(f"{linha}")

    # Contagem de trades
    print(f"  Total de Trades:        {metricas.get('total_trades', 0):>10}")
    print(f"  Trades Vencedores:      {metricas.get('total_vencedores', 0):>10}")
    print(f"  Trades Perdedores:      {metricas.get('total_perdedores', 0):>10}")
    print(f"  Win Rate:               {metricas.get('win_rate_pct', 0):>9.1f}%")
    print(f"{linha}")

    # Métricas de qualidade
    print(f"  Profit Factor:          {metricas.get('profit_factor', 0):>10.4f}")
    print(f"  Sharpe Ratio:           {metricas.get('sharpe_ratio', 0):>10.4f}")
    print(f"  Max Drawdown:           {metricas.get('max_drawdown_pct', 0):>9.2f}%")
    print(f"{linha}")

    # Médias por trade
    print(f"  Média Ganho/Trade:      {metricas.get('media_ganho_pct', 0):>9.2f}%")
    print(f"  Média Perda/Trade:      {metricas.get('media_perda_pct', 0):>9.2f}%")
    dur   = metricas.get("duracao_media_candles", 0)
    horas = dur * 4
    print(f"  Duração Média:          {dur:>8.1f} candles ({horas:.0f}h aprox.)")
    print(f"{linha}")

    # ── Verificar critérios mínimos da estratégia ─────────────
    sharpe   = metricas.get("sharpe_ratio",    0)
    dd       = metricas.get("max_drawdown_pct", 100)
    pf       = metricas.get("profit_factor",   0)
    wr       = metricas.get("win_rate_pct",    0)
    n_trades = metricas.get("total_trades",    0)

    criterios = {
        "Sharpe Ratio > 1.0":   sharpe   > 1.0,
        "Max Drawdown < 20%":   dd       < 20.0,
        "Profit Factor > 1.5":  pf       > 1.5,
        "Win Rate > 40%":       wr       > 40.0,
        "Total Trades > 30":    n_trades > 30,
    }

    print("  CRITÉRIOS MÍNIMOS:")
    todos_ok = True
    for criterio, passou in criterios.items():
        icone = "✔" if passou else "✘"
        status = "PASSOU" if passou else "FALHOU"
        print(f"    {icone} {status:6}  {criterio}")
        if not passou:
            todos_ok = False

    print(f"{linha}")
    if todos_ok:
        print("  VEREDICTO: ✔ ESTRATÉGIA APROVADA — Prosseguir para F3")
    else:
        print("  VEREDICTO: ✘ ESTRATÉGIA REPROVADA — Revisar parâmetros")
    print(f"{linha}\n")


# ─────────────────────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL (ponto de entrada do script)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SAFE TRADING — INICIANDO BACKTEST")
    print("  Estratégia: EMA 8/21 + RSI + Volume")
    print("=" * 60 + "\n")

    # Passo 1: Garantir que as pastas necessárias existem
    criar_pastas()

    # Passo 2: Carregar dados (CSV local ou baixar da Binance)
    df = carregar_dados()

    # Passo 3: Calcular indicadores técnicos (EMA, RSI, ATR, Vol)
    df = calcular_indicadores(df)

    # Passo 4: Gerar sinais de entrada/saída com anti-look-ahead
    df = gerar_sinais(df)

    # Passo 5: Simular todos os trades com gestão de risco
    lista_trades, curva_equity = simular_trades(df)

    # Passo 6: Calcular métricas de performance
    metricas = calcular_metricas(lista_trades, curva_equity)

    # Passo 7: Gerar gráfico visual (3 painéis)
    gerar_grafico(df, lista_trades, curva_equity)

    # Passo 8: Salvar resultados em JSON
    salvar_json(df, lista_trades, metricas)

    # Passo 9: Imprimir resumo formatado no terminal
    imprimir_resumo(metricas)

    print("Arquivos gerados com sucesso:")
    print(f"  → Gráfico:  {ARQUIVO_PNG}")
    print(f"  → Métricas: {ARQUIVO_JSON}\n")
