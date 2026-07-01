"""
Script wrapper para rodar as 3 variações de backtest sem sobrescrever o baseline.
Executa V1, V2, V3 e salva os resultados individualmente + comparação.
"""

import os
import sys
import json
import math
import warnings
import importlib

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

warnings.filterwarnings("ignore")

# Pasta raiz do projeto
PASTA_RAIZ    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DATA    = os.path.join(PASTA_RAIZ, "data")
PASTA_RESULTS = os.path.join(PASTA_RAIZ, "results")
ARQUIVO_CSV   = os.path.join(PASTA_DATA, "btc_usdt_4h.csv")

# Adicionar scripts/ ao path para importar backtest
sys.path.insert(0, os.path.join(PASTA_RAIZ, "scripts"))

# Reusar as classes de indicadores do backtest original
class ta:
    @staticmethod
    def ema(series, length):
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def sma(series, length):
        return series.rolling(window=length).mean()

    @staticmethod
    def rsi(series, length):
        delta = series.diff()
        ganho = delta.clip(lower=0)
        perda = -delta.clip(upper=0)
        media_ganho = ganho.ewm(com=length - 1, adjust=False).mean()
        media_perda = perda.ewm(com=length - 1, adjust=False).mean()
        rs = media_ganho / media_perda.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high, low, close, length):
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        return tr.ewm(com=length - 1, adjust=False).mean()


def rodar_backtest(params: dict) -> dict:
    """Roda um backtest completo com os parâmetros dados. Retorna as métricas."""

    EMA_RAPIDA   = params["ema_rapida"]
    EMA_LENTA    = params["ema_lenta"]
    EMA_MACRO    = params.get("ema_macro", 50)
    RSI_PERIODO  = params.get("rsi_periodo", 14)
    RSI_MIN      = params["rsi_min"]
    RSI_MAX      = params["rsi_max"]
    ATR_PERIODO  = params.get("atr_periodo", 14)
    STOP_MULT    = params.get("stop_mult", 1.5)
    TP_MULT      = params["tp_mult"]
    VOL_MEDIA_PER = params.get("vol_media_per", 20)
    CAPITAL_INICIAL = params.get("capital_inicial", 1000.0)
    RISCO_POR_TRADE = params.get("risco_por_trade", 0.01)
    TAXA_ENTRADA    = params.get("taxa_entrada", 0.001)
    TAXA_SAIDA      = params.get("taxa_saida", 0.001)
    SLIPPAGE        = params.get("slippage", 0.0005)
    POS_MAX_PCT     = params.get("pos_max_pct", 0.20)

    # Carregar dados
    df = pd.read_csv(ARQUIVO_CSV, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Calcular indicadores
    df["ema_r"]    = ta.ema(df["close"], length=EMA_RAPIDA)
    df["ema_l"]    = ta.ema(df["close"], length=EMA_LENTA)
    df["ema50"]    = ta.ema(df["close"], length=EMA_MACRO)
    df["rsi"]      = ta.rsi(df["close"], length=RSI_PERIODO)
    df["atr"]      = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIODO)
    df["vol_media"] = ta.sma(df["volume"], length=VOL_MEDIA_PER)

    # Gerar sinais
    cruzamento_alta = (
        (df["ema_r"].shift(1) > df["ema_l"].shift(1)) &
        (df["ema_r"].shift(2) <= df["ema_l"].shift(2))
    )
    rsi_valido = (
        (df["rsi"].shift(1) >= RSI_MIN) &
        (df["rsi"].shift(1) <= RSI_MAX)
    )
    volume_confirmado = df["volume"] > df["vol_media"].shift(1)
    tendencia_alta    = df["close"].shift(1) > df["ema50"].shift(1)

    df["sinal_compra"] = (cruzamento_alta & rsi_valido & volume_confirmado & tendencia_alta).fillna(False)
    df["sinal_crossdown"] = (
        (df["ema_r"].shift(1) < df["ema_l"].shift(1)) &
        (df["ema_r"].shift(2) >= df["ema_l"].shift(2))
    ).fillna(False)

    # Simular trades
    df_valido = df.dropna(subset=["ema_r", "ema_l", "ema50", "rsi", "atr", "vol_media"]).copy().reset_index(drop=True)

    capital        = CAPITAL_INICIAL
    posicao_aberta = False
    trade_atual    = {}
    lista_trades   = []
    curva_equity   = []

    for i in range(len(df_valido)):
        candle      = df_valido.iloc[i]
        ts_atual    = candle["timestamp"]
        preco_open  = candle["open"]
        preco_high  = candle["high"]
        preco_low   = candle["low"]
        preco_close = candle["close"]

        if posicao_aberta:
            saiu = False
            preco_saida = None
            motivo_saida = None

            if preco_low <= trade_atual["stop_loss"]:
                preco_saida  = trade_atual["stop_loss"]
                motivo_saida = "stop_loss"
                saiu         = True
            elif preco_high >= trade_atual["take_profit"]:
                preco_saida  = trade_atual["take_profit"]
                motivo_saida = "take_profit"
                saiu         = True
            elif candle["sinal_crossdown"]:
                preco_saida  = preco_open
                motivo_saida = "sinal_inverso"
                saiu         = True

            if saiu:
                custo_saida_pct  = TAXA_SAIDA + SLIPPAGE
                preco_saida_real = preco_saida * (1 - custo_saida_pct)
                quantidade       = trade_atual["quantidade"]
                preco_entrada    = trade_atual["preco_entrada_real"]
                valor_saida      = quantidade * preco_saida_real
                pnl_usdt         = valor_saida - (quantidade * preco_entrada)
                retorno_pct      = (preco_saida_real / preco_entrada - 1) * 100

                capital += valor_saida

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

        if not posicao_aberta and candle["sinal_compra"] and (i + 1) < len(df_valido):
            proximo            = df_valido.iloc[i + 1]
            preco_entrada      = proximo["open"]
            custo_entrada_pct  = TAXA_ENTRADA + SLIPPAGE
            preco_entrada_real = preco_entrada * (1 + custo_entrada_pct)

            atr_sinal    = candle["atr"]
            stop_loss    = preco_entrada_real - (STOP_MULT * atr_sinal)
            take_profit  = preco_entrada_real + (TP_MULT  * atr_sinal)

            risco_usdt     = capital * RISCO_POR_TRADE
            distancia_stop = preco_entrada_real - stop_loss

            if distancia_stop <= 0:
                continue

            quantidade    = risco_usdt / distancia_stop
            valor_posicao = quantidade * preco_entrada_real

            if valor_posicao > capital * POS_MAX_PCT:
                quantidade    = (capital * POS_MAX_PCT) / preco_entrada_real
                valor_posicao = capital * POS_MAX_PCT

            if valor_posicao > capital or valor_posicao <= 0:
                continue

            capital -= valor_posicao

            trade_atual = {
                "ts_entrada":         proximo["timestamp"],
                "idx_entrada":        i + 1,
                "preco_entrada_real": preco_entrada_real,
                "stop_loss":          stop_loss,
                "take_profit":        take_profit,
                "quantidade":         quantidade,
                "atr_entrada":        atr_sinal,
            }
            posicao_aberta = True

        if posicao_aberta:
            valor_em_btc  = trade_atual["quantidade"] * preco_close
            capital_total = capital + valor_em_btc
        else:
            capital_total = capital

        curva_equity.append({"timestamp": ts_atual, "capital": round(capital_total, 2)})

    # Fechar posição em aberto no fim
    if posicao_aberta and len(df_valido) > 0:
        ultimo             = df_valido.iloc[-1]
        custo_saida        = TAXA_SAIDA + SLIPPAGE
        preco_saida_final  = ultimo["close"] * (1 - custo_saida)
        quantidade         = trade_atual["quantidade"]
        preco_entrada      = trade_atual["preco_entrada_real"]
        valor_saida        = quantidade * preco_saida_final
        pnl_usdt           = valor_saida - (quantidade * preco_entrada)
        capital           += valor_saida
        retorno_pct        = (preco_saida_final / preco_entrada - 1) * 100

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

    # Calcular métricas
    if not lista_trades:
        return {"erro": "Nenhum trade realizado"}

    ganhos = [t["pnl_usdt"] for t in lista_trades if t["pnl_usdt"] > 0]
    perdas = [t["pnl_usdt"] for t in lista_trades if t["pnl_usdt"] <= 0]

    total_trades     = len(lista_trades)
    total_vencedores = len(ganhos)
    total_perdedores = len(perdas)

    win_rate      = (total_vencedores / total_trades * 100) if total_trades > 0 else 0
    soma_ganhos   = sum(ganhos) if ganhos else 0
    soma_perdas   = abs(sum(perdas)) if perdas else 0
    profit_factor = (soma_ganhos / soma_perdas) if soma_perdas > 0 else float("inf")

    capital_final = lista_trades[-1]["capital_apos"]
    retorno_total = (capital_final / CAPITAL_INICIAL - 1) * 100

    retornos = [t["retorno_pct"] / 100 for t in lista_trades]
    if len(retornos) > 1:
        media_ret      = np.mean(retornos)
        desvio_ret     = np.std(retornos, ddof=1)
        candles_total  = len(curva_equity)
        anos_total     = candles_total / 2190
        trades_por_ano = total_trades / max(anos_total, 0.1)
        fator_anual    = math.sqrt(max(trades_por_ano, 1))
        sharpe         = (media_ret / desvio_ret * fator_anual) if desvio_ret > 0 else 0.0
    else:
        sharpe = 0.0

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

    media_ganho    = np.mean([t["retorno_pct"] for t in lista_trades if t["pnl_usdt"] > 0]) if ganhos else 0.0
    media_perda    = np.mean([t["retorno_pct"] for t in lista_trades if t["pnl_usdt"] <= 0]) if perdas else 0.0
    duracao_media  = np.mean([t["duracao_candles"] for t in lista_trades]) if lista_trades else 0.0

    metricas = {
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

    df_valido2 = df.dropna(subset=["ema_r"]).copy()
    data_inicio = str(df_valido2["timestamp"].iloc[0].date())
    data_fim    = str(df_valido2["timestamp"].iloc[-1].date())

    resultado = {
        "estrategia":      f"EMA {EMA_RAPIDA}/{EMA_LENTA} + RSI + Volume",
        "mercado":         "BTC/USDT 4h",
        "periodo":         {"inicio": data_inicio, "fim": data_fim},
        "capital_inicial": CAPITAL_INICIAL,
        "capital_final":   metricas["capital_final"],
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

    return resultado


# ─── DEFINIR AS 3 VARIAÇÕES ───────────────────────────────────
VARIACOES = {
    "v1": {
        "nome": "V1 — EMA Conservadora",
        "arquivo": os.path.join(PASTA_RESULTS, "backtest_v1.json"),
        "params": {
            "ema_rapida": 13,
            "ema_lenta":  21,
            "rsi_min":    45,
            "rsi_max":    65,
            "tp_mult":    3.0,
        },
    },
    "v2": {
        "nome": "V2 — TP Menor",
        "arquivo": os.path.join(PASTA_RESULTS, "backtest_v2.json"),
        "params": {
            "ema_rapida": 8,
            "ema_lenta":  21,
            "rsi_min":    40,
            "rsi_max":    65,
            "tp_mult":    2.0,
        },
    },
    "v3": {
        "nome": "V3 — Combinada",
        "arquivo": os.path.join(PASTA_RESULTS, "backtest_v3.json"),
        "params": {
            "ema_rapida": 10,
            "ema_lenta":  21,
            "rsi_min":    42,
            "rsi_max":    70,
            "tp_mult":    2.5,
        },
    },
}

os.makedirs(PASTA_RESULTS, exist_ok=True)


# ─── RODAR CADA VARIAÇÃO ───────────────────────────────────────
resultados_variacoes = {}

for chave, variacao in VARIACOES.items():
    print(f"\n{'='*60}")
    print(f"  Rodando: {variacao['nome']}")
    print(f"  Params: {variacao['params']}")
    print(f"{'='*60}")

    resultado = rodar_backtest(variacao["params"])
    resultados_variacoes[chave] = resultado

    with open(variacao["arquivo"], "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

    m = resultado["metricas"]
    print(f"  Trades: {m['total_trades']} | Sharpe: {m['sharpe_ratio']:.4f} | "
          f"PF: {m['profit_factor']:.4f} | DD: {m['max_drawdown_pct']:.2f}% | "
          f"Retorno: {m['retorno_total_pct']:.2f}%")
    print(f"  Salvo em: {variacao['arquivo']}")


# ─── CARREGAR BASELINE ────────────────────────────────────────
ARQUIVO_BASELINE = os.path.join(PASTA_RESULTS, "backtest_ema_resultado.json")
with open(ARQUIVO_BASELINE, "r", encoding="utf-8") as f:
    baseline = json.load(f)


# ─── CRIAR COMPARAÇÃO ────────────────────────────────────────
def resumo(nome, resultado, params_label=None):
    m = resultado["metricas"]
    p = resultado["parametros"]
    return {
        "variacao":          nome,
        "ema_rapida":        p["ema_rapida"],
        "ema_lenta":         p["ema_lenta"],
        "rsi_min":           p["rsi_min"],
        "rsi_max":           p["rsi_max"],
        "tp_mult":           p["tp_mult"],
        "total_trades":      m["total_trades"],
        "win_rate_pct":      m["win_rate_pct"],
        "profit_factor":     m["profit_factor"],
        "sharpe_ratio":      m["sharpe_ratio"],
        "max_drawdown_pct":  m["max_drawdown_pct"],
        "retorno_total_pct": m["retorno_total_pct"],
        "capital_final":     m["capital_final"],
    }

comparacao = {
    "descricao": "Comparação de variações de parâmetros — Safe Trading F3.2",
    "mercado":   "BTC/USDT 4H (2022-01-01 a 2026-06-27)",
    "capital_inicial": 1000.0,
    "variacoes": [
        resumo("Baseline (EMA 8/21, RSI 40-65, TP 3.0)", baseline),
        resumo("V1 — EMA Conservadora (13/21, RSI 45-65, TP 3.0)", resultados_variacoes["v1"]),
        resumo("V2 — TP Menor (8/21, RSI 40-65, TP 2.0)",          resultados_variacoes["v2"]),
        resumo("V3 — Combinada (10/21, RSI 42-70, TP 2.5)",         resultados_variacoes["v3"]),
    ]
}

ARQUIVO_COMP = os.path.join(PASTA_RESULTS, "comparacao_variacoes.json")
with open(ARQUIVO_COMP, "w", encoding="utf-8") as f:
    json.dump(comparacao, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print("  COMPARAÇÃO FINAL")
print(f"{'='*60}")
print(f"{'Variação':<40} {'Trades':>6} {'Sharpe':>8} {'PF':>7} {'MaxDD%':>8} {'Ret%':>8}")
print("-" * 80)
for v in comparacao["variacoes"]:
    print(f"{v['variacao'][:40]:<40} {v['total_trades']:>6} {v['sharpe_ratio']:>8.4f} "
          f"{v['profit_factor']:>7.4f} {v['max_drawdown_pct']:>8.2f} {v['retorno_total_pct']:>8.2f}")

print(f"\nComparação salva em: {ARQUIVO_COMP}")
