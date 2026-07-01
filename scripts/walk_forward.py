"""
=============================================================
SAFE TRADING — WALK-FORWARD VALIDATION
Estratégia: EMA 8/21 Crossover + Filtro RSI + Confirmação de Volume
=============================================================

O que é Walk-Forward?
─────────────────────
Walk-Forward é uma técnica de validação que testa se a estratégia
funciona fora do período em que foi desenvolvida (out-of-sample).

Sem isso, correríamos o risco de "overfitting" — a estratégia funciona
apenas porque foi ajustada para os dados históricos específicos.

Como funciona?
──────────────
Os dados são divididos em 5 janelas sequenciais.
Em cada janela: 60% é "treino" (referência) e 40% é "teste" (validação).
Rodamos o backtest apenas na parte de TESTE de cada janela.

Exemplo com 1000 candles e 5 janelas:
  Janela 1: treino [0–400],    teste [400–600]
  Janela 2: treino [200–600],  teste [600–800]
  Janela 3: treino [400–800],  teste [800–1000]
  ...

Se a estratégia tiver boas métricas em TODAS as janelas de teste,
ela é robusta e não está apenas memorizando os dados históricos.

Como rodar:
    python scripts/walk_forward.py
"""

import os
import sys
import json
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Importar funções do backtest principal ────────────────────
# Adicionamos o diretório scripts/ ao path para o import funcionar
PASTA_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PASTA_RAIZ    = os.path.dirname(PASTA_SCRIPTS)
sys.path.insert(0, PASTA_SCRIPTS)

# Importar as funções do backtest.py
from backtest import (
    carregar_dados,
    calcular_indicadores,
    gerar_sinais,
    simular_trades,
    calcular_metricas,
    PASTA_RESULTS,
)

# ─────────────────────────────────────────────────────────────
# PARÂMETROS DO WALK-FORWARD
# ─────────────────────────────────────────────────────────────
N_JANELAS      = 5      # Número de janelas de validação
PROP_TREINO    = 0.60   # 60% de cada janela para treino (referência)
PROP_TESTE     = 0.40   # 40% de cada janela para teste (out-of-sample)
ARQUIVO_WF_JSON = os.path.join(PASTA_RESULTS, "walk_forward_resultado.json")


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Dividir dados em janelas walk-forward
# ─────────────────────────────────────────────────────────────
def criar_janelas(df: pd.DataFrame, n_janelas: int, prop_treino: float) -> list:
    """
    Divide o DataFrame em N janelas sobrepostas para walk-forward.

    Cada janela contém:
    - idx_treino_inicio, idx_treino_fim: índices da parte de treino
    - idx_teste_inicio, idx_teste_fim: índices da parte de teste

    A janela de teste de cada período é a parte "out-of-sample"
    que não foi usada para criar/ajustar a estratégia.
    """
    total_candles = len(df)
    tamanho_janela = total_candles // n_janelas  # Tamanho de cada fatia

    janelas = []
    for i in range(n_janelas):
        # Início e fim de cada janela (com sobreposição)
        inicio = i * (total_candles - tamanho_janela) // max(n_janelas - 1, 1)
        fim    = min(inicio + tamanho_janela, total_candles)

        # Dentro de cada janela: 60% treino, 40% teste
        tamanho_treino = int((fim - inicio) * prop_treino)
        idx_treino_ini = inicio
        idx_treino_fim = inicio + tamanho_treino
        idx_teste_ini  = idx_treino_fim
        idx_teste_fim  = fim

        # Garantir que a janela de teste tem candles suficientes
        if (idx_teste_fim - idx_teste_ini) < 50:
            continue

        janelas.append({
            "numero":          i + 1,
            "idx_treino_ini":  idx_treino_ini,
            "idx_treino_fim":  idx_treino_fim,
            "idx_teste_ini":   idx_teste_ini,
            "idx_teste_fim":   idx_teste_fim,
            "data_treino_ini": str(df["timestamp"].iloc[idx_treino_ini].date()),
            "data_treino_fim": str(df["timestamp"].iloc[idx_treino_fim - 1].date()),
            "data_teste_ini":  str(df["timestamp"].iloc[idx_teste_ini].date()),
            "data_teste_fim":  str(df["timestamp"].iloc[idx_teste_fim - 1].date()),
            "candles_treino":  tamanho_treino,
            "candles_teste":   idx_teste_fim - idx_teste_ini,
        })

    return janelas


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Rodar backtest em uma janela específica
# ─────────────────────────────────────────────────────────────
def rodar_backtest_janela(df_completo: pd.DataFrame, janela: dict) -> dict:
    """
    Executa o backtest apenas nos candles da janela de TESTE (out-of-sample).

    Importante: para calcular os indicadores corretamente,
    usamos a janela COMPLETA (treino + teste) para calcular EMAs, RSI etc.,
    mas executamos os trades apenas na parte de teste.
    Isso evita que o início da série de teste tenha indicadores NaN.

    Retorna:
        Dicionário com métricas da janela de teste
    """
    # Usar todos os dados até o fim do teste para calcular indicadores
    df_janela = df_completo.iloc[:janela["idx_teste_fim"]].copy()
    df_janela = calcular_indicadores(df_janela)
    df_janela = gerar_sinais(df_janela)

    # Extrair apenas a parte de TESTE para executar os trades
    df_teste = df_janela.iloc[janela["idx_teste_ini"]:janela["idx_teste_fim"]].copy()
    df_teste = df_teste.reset_index(drop=True)

    # Remover NaNs da parte de teste
    df_teste = df_teste.dropna(subset=["ema8", "ema21", "ema50", "rsi", "atr", "vol_media"])
    df_teste = df_teste.reset_index(drop=True)

    if len(df_teste) < 20:
        return {"erro": "Poucos candles válidos na janela de teste"}

    # Simular trades e calcular métricas
    try:
        lista_trades, curva_equity = simular_trades(df_teste)
        metricas = calcular_metricas(lista_trades, curva_equity)
        metricas["n_trades"] = len(lista_trades)
        return metricas
    except Exception as e:
        return {"erro": str(e)}


# ─────────────────────────────────────────────────────────────
# FUNÇÃO: Imprimir tabela de resultados
# ─────────────────────────────────────────────────────────────
def imprimir_tabela(janelas: list, resultados: list):
    """Imprime uma tabela comparativa das métricas por janela."""

    linha = "=" * 80
    print(f"\n{linha}")
    print("  SAFE TRADING — WALK-FORWARD VALIDATION")
    print(f"  {N_JANELAS} janelas • {int(PROP_TREINO*100)}% treino / {int(PROP_TESTE*100)}% teste (out-of-sample)")
    print(f"{linha}")

    # Cabeçalho da tabela
    print(f"  {'Janela':<8} {'Período Teste':<25} {'Trades':<8} {'Win%':<8} "
          f"{'PF':<7} {'Sharpe':<8} {'DD%':<8} {'Retorno%':<10}")
    print(f"  {'-'*8} {'-'*25} {'-'*8} {'-'*8} {'-'*7} {'-'*8} {'-'*8} {'-'*10}")

    # Uma linha por janela
    metricas_validas = []
    for janela, resultado in zip(janelas, resultados):
        if "erro" in resultado:
            periodo = f"{janela['data_teste_ini']} - {janela['data_teste_fim']}"
            print(f"  {janela['numero']:<8} {periodo:<25} ERRO: {resultado['erro']}")
            continue

        periodo  = f"{janela['data_teste_ini']} a {janela['data_teste_fim']}"
        trades   = resultado.get("total_trades",      0)
        win_rate = resultado.get("win_rate_pct",      0)
        pf       = resultado.get("profit_factor",     0)
        sharpe   = resultado.get("sharpe_ratio",      0)
        dd       = resultado.get("max_drawdown_pct",  0)
        retorno  = resultado.get("retorno_total_pct", 0)

        sinal    = "+" if retorno >= 0 else ""
        print(f"  {janela['numero']:<8} {periodo:<25} {trades:<8} {win_rate:<8.1f} "
              f"{pf:<7.2f} {sharpe:<8.2f} {dd:<8.2f} {sinal}{retorno:<10.2f}")

        metricas_validas.append(resultado)

    print(f"{linha}")

    # ── Médias e desvios padrão entre janelas ─────────────────
    if metricas_validas:
        def media_dp(chave):
            vals = [m.get(chave, 0) for m in metricas_validas]
            return np.mean(vals), np.std(vals)

        print("\n  MÉDIAS (± desvio padrão) ENTRE JANELAS DE TESTE:")
        print(f"  {'Métrica':<30} {'Média':>10}  {'Desvio':>10}")
        print(f"  {'-'*30} {'-'*10}  {'-'*10}")

        metricas_exibir = [
            ("total_trades",      "Total Trades"),
            ("win_rate_pct",      "Win Rate (%)"),
            ("profit_factor",     "Profit Factor"),
            ("sharpe_ratio",      "Sharpe Ratio"),
            ("max_drawdown_pct",  "Max Drawdown (%)"),
            ("retorno_total_pct", "Retorno Total (%)"),
        ]
        for chave, nome in metricas_exibir:
            med, dp = media_dp(chave)
            print(f"  {nome:<30} {med:>10.2f}  ±{dp:>9.2f}")

        # ── Avaliação final ────────────────────────────────────
        med_sharpe, _ = media_dp("sharpe_ratio")
        med_dd,     _ = media_dp("max_drawdown_pct")
        med_pf,     _ = media_dp("profit_factor")
        med_wr,     _ = media_dp("win_rate_pct")

        janelas_positivas = sum(
            1 for m in metricas_validas
            if m.get("retorno_total_pct", -99) > 0
        )

        print(f"\n{linha}")
        print(f"  AVALIAÇÃO WALK-FORWARD:")
        print(f"    Janelas com retorno positivo: {janelas_positivas}/{len(metricas_validas)}")
        print(f"    Consistência: {'✔ BOA' if janelas_positivas >= len(metricas_validas) * 0.6 else '✘ FRACA'}")
        print(f"    Sharpe médio: {med_sharpe:.2f} {'✔ OK' if med_sharpe > 0.8 else '✘ BAIXO'}")
        print(f"    DD médio:     {med_dd:.1f}%  {'✔ OK' if med_dd < 25 else '✘ ALTO'}")
        print(f"    PF médio:     {med_pf:.2f}  {'✔ OK' if med_pf > 1.2 else '✘ BAIXO'}")

        # Veredicto geral
        aprovado = (
            janelas_positivas >= len(metricas_validas) * 0.6 and
            med_sharpe > 0.5 and
            med_dd < 30 and
            med_pf > 1.0
        )
        print(f"\n  VEREDICTO: {'✔ ESTRATÉGIA ROBUSTA — Sem overfitting evidente' if aprovado else '✘ POSSÍVEL OVERFITTING — Revisar estratégia'}")
        print(f"{linha}\n")

    return metricas_validas


# ─────────────────────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SAFE TRADING — WALK-FORWARD VALIDATION")
    print("  Testando robustez da estratégia EMA 8/21 + RSI")
    print("=" * 60 + "\n")

    # Passo 1: Carregar dados completos
    print("Carregando dados...")
    df_raw = carregar_dados()

    # Passo 2: Calcular indicadores no dataset completo
    print("Calculando indicadores no dataset completo...")
    df_com_indicadores = calcular_indicadores(df_raw.copy())

    # Verificar se há dados suficientes para dividir em janelas
    df_valido = df_com_indicadores.dropna(
        subset=["ema8", "ema21", "ema50", "rsi", "atr", "vol_media"]
    ).reset_index(drop=True)

    if len(df_valido) < 200:
        print(f"ERRO: Dados insuficientes para walk-forward. "
              f"Necessários: 200 candles válidos. Disponíveis: {len(df_valido)}")
        sys.exit(1)

    print(f"  → {len(df_valido)} candles válidos disponíveis para validação")

    # Passo 3: Criar as janelas de walk-forward
    print(f"\nCriando {N_JANELAS} janelas de validação...")
    janelas = criar_janelas(df_valido, N_JANELAS, PROP_TREINO)
    print(f"  → {len(janelas)} janelas criadas com sucesso\n")

    # Mostrar resumo das janelas
    print(f"  {'Janela':<8} {'Treino':<28} {'Teste':<28}")
    print(f"  {'-'*8} {'-'*28} {'-'*28}")
    for j in janelas:
        treino = f"{j['data_treino_ini']} a {j['data_treino_fim']} ({j['candles_treino']} candles)"
        teste  = f"{j['data_teste_ini']} a {j['data_teste_fim']} ({j['candles_teste']} candles)"
        print(f"  {j['numero']:<8} {treino:<28} {teste:<28}")
    print()

    # Passo 4: Rodar backtest em cada janela de teste
    resultados = []
    for i, janela in enumerate(janelas):
        print(f"Rodando backtest — Janela {janela['numero']}/{len(janelas)} "
              f"(teste: {janela['data_teste_ini']} a {janela['data_teste_fim']})...")
        resultado = rodar_backtest_janela(df_valido, janela)
        resultados.append(resultado)
        trades = resultado.get("total_trades", "N/A")
        retorno = resultado.get("retorno_total_pct", "N/A")
        print(f"  → {trades} trades, retorno: {retorno}%")

    # Passo 5: Imprimir tabela comparativa
    metricas_validas = imprimir_tabela(janelas, resultados)

    # Passo 6: Salvar resultado em JSON
    os.makedirs(PASTA_RESULTS, exist_ok=True)

    resultado_completo = {
        "metodo":        "Walk-Forward Validation",
        "n_janelas":     N_JANELAS,
        "prop_treino":   PROP_TREINO,
        "prop_teste":    PROP_TESTE,
        "janelas":       janelas,
        "resultados":    resultados,
    }

    if metricas_validas:
        # Adicionar estatísticas consolidadas
        def media_dp_chave(chave):
            vals = [m.get(chave, 0) for m in metricas_validas]
            return {"media": round(float(np.mean(vals)), 4),
                    "desvio": round(float(np.std(vals)), 4)}

        resultado_completo["resumo"] = {
            "total_trades":          media_dp_chave("total_trades"),
            "win_rate_pct":          media_dp_chave("win_rate_pct"),
            "profit_factor":         media_dp_chave("profit_factor"),
            "sharpe_ratio":          media_dp_chave("sharpe_ratio"),
            "max_drawdown_pct":      media_dp_chave("max_drawdown_pct"),
            "retorno_total_pct":     media_dp_chave("retorno_total_pct"),
        }

    with open(ARQUIVO_WF_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado_completo, f, indent=2, ensure_ascii=False, default=str)

    print(f"Resultado salvo em: {ARQUIVO_WF_JSON}")
    print("Walk-forward concluído!\n")
