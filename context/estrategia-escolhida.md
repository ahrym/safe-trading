# Estratégia Escolhida: EMA 8/21 Crossover com Filtro RSI e Confirmação de Volume

**Mercado:** BTC/USDT — Binance Spot  
**Timeframe principal:** 4H  
**Timeframe de confirmação:** 1D (tendência macro)  
**Versão:** 1.0 — Junho 2026  
**Status:** Pronta para implementação na Fase 3

---

## Justificativa da Escolha

A Variação A foi escolhida por reunir o melhor equilíbrio entre simplicidade de implementação e robustez estatística: é trend-following (adequada para BTC, que tem ciclos direcionais prolongados), possui documentação pública extensa em backtests, e seus três filtros (EMA crossover + RSI + volume) reduzem entradas em ruído sem tornar a estratégia excessivamente complexa. As demais variações foram descartadas porque a Variação B gera poucos trades (difícil de validar), a Variação C tem drawdown inaceitável em bear markets, e a Variação D é complexa demais para uma primeira implementação em Freqtrade.

---

## Regras de Entrada (LONG)

A entrada é gerada apenas quando **todas** as condições abaixo são verdadeiras no fechamento do candle 4H:

- **Condição 1 — Cruzamento de EMA:** EMA(8) cruza acima de EMA(21) no candle atual (ou seja, EMA8 > EMA21 no candle atual E EMA8 <= EMA21 no candle anterior)
- **Condição 2 — Filtro RSI:** RSI(14) está entre 40 e 65 no candle de sinal (não sobrecomprado, não sobrevendido — zona de momentum saudável)
- **Condição 3 — Confirmação de volume:** Volume do candle de sinal é maior que a média de volume dos últimos 20 períodos (volume_atual > volume_media_20)
- **Condição 4 — Tendência macro (opcional mas recomendada):** Preço de fechamento no 4H está acima da EMA(50) no mesmo timeframe, confirmando tendência de alta

**Entrada:** Compra no **fechamento do candle** que gerou o sinal (não antecipe a entrada no candle em formação).

---

## Regras de Saída

### Take Profit
- **Método:** ATR múltiplo fixo (não trailing no início)
- **Alvo:** Entrada + (2 × ATR(14) × 2) → equivalente a RR 2:1 em relação ao stop
- **Alternativa:** Se o preço atingir o alvo parcialmente, fechar 100% da posição (sem parciais na v1)

### Stop Loss
- **Método:** ATR dinâmico abaixo do ponto de entrada
- **Posição:** Entrada − (1.5 × ATR(14)) calculado no candle de sinal
- **Regra:** Stop é fixo após a entrada (não move o stop para breakeven na v1 para manter simplicidade)

### Saída por Sinal Inverso
- **Sim:** Se EMA(8) cruzar abaixo de EMA(21) enquanto a posição está aberta, fechar a posição independentemente do P&L atual
- Isso protege contra reversões prolongadas que o stop não teria capturado

### Stop Diário (Gestão de Risco Operacional)
- Se a conta registrar perda de 3% ou mais em um único dia, o bot para de operar pelo restante do dia

---

## Parâmetros

| Parâmetro | Valor | Justificativa |
|---|---|---|
| EMA rápida | 8 | Responde rapidamente a novas tendências sem gerar ruído excessivo no 4H |
| EMA lenta | 21 | Representa aproximadamente 1 semana de candles 4H (6 candles/dia × 3.5 dias) |
| RSI período | 14 | Padrão amplamente testado — 14 períodos no 4H ≈ ~2.3 dias |
| RSI mínimo entrada | 40 | Evita entradas em mercado sem momentum |
| RSI máximo entrada | 65 | Evita entradas quando ativo já está sobrecomprado |
| ATR período | 14 | Mesmo período do RSI — captura volatilidade recente adequada |
| Stop loss | 1.5 × ATR(14) | Suficiente para absorver ruído intracandle sem ser excessivamente amplo |
| Take profit | 3.0 × ATR(14) | Garante RR 2:1 em relação ao stop de 1.5×ATR |
| Volume média | 20 períodos | ~3.3 dias — referência de volume "normal" recente |
| EMA filtro macro | 50 períodos | ~8 dias no 4H — confirma tendência de médio prazo |
| Risco por trade | 1% do capital | Risco máximo aceitável para preservação de capital |

---

## Gestão de Risco

- **Risco por trade:** 1% do capital total da conta
- **Cálculo do tamanho da posição:**
  ```
  risco_em_usdt = capital_total × 0.01
  distancia_stop = 1.5 × ATR(14)
  tamanho_posicao = risco_em_usdt / distancia_stop
  ```
- **Posição máxima:** 20% do capital total (teto de segurança)
- **Máximo de trades simultâneos:** 1 (iniciante — foco total em BTC/USDT)
- **Stop diário:** Se P&L do dia atingir -3%, parar operações até o dia seguinte
- **Stop semanal:** Se drawdown acumulado atingir -8% na semana, revisar estratégia manualmente antes de retomar

---

## Pseudocódigo Completo

```python
# ============================================================
# ESTRATÉGIA: EMA 8/21 + RSI(14) + Volume — BTC/USDT 4H
# ============================================================

# PARÂMETROS
EMA_RAPIDA = 8
EMA_LENTA = 21
EMA_MACRO = 50
RSI_PERIODO = 14
RSI_MIN = 40
RSI_MAX = 65
ATR_PERIODO = 14
STOP_MULTIPLICADOR = 1.5
TP_MULTIPLICADOR = 3.0     # = STOP × 2 → RR 2:1
VOLUME_MEDIA = 20
RISCO_POR_TRADE = 0.01     # 1% do capital

# INDICADORES (calculados a cada candle fechado)
ema8 = EMA(close, EMA_RAPIDA)
ema21 = EMA(close, EMA_LENTA)
ema50 = EMA(close, EMA_MACRO)
rsi = RSI(close, RSI_PERIODO)
atr = ATR(high, low, close, ATR_PERIODO)
vol_media = SMA(volume, VOLUME_MEDIA)

# SINAL DE ENTRADA
crossover_ocorreu = (ema8[0] > ema21[0]) AND (ema8[1] <= ema21[1])
rsi_ok = (rsi[0] >= RSI_MIN) AND (rsi[0] <= RSI_MAX)
volume_ok = volume[0] > vol_media[0]
tendencia_macro_ok = close[0] > ema50[0]   # opcional mas recomendado

sinal_entrada = crossover_ocorreu AND rsi_ok AND volume_ok AND tendencia_macro_ok

# EXECUÇÃO DA ENTRADA
SE sinal_entrada E sem_posicao_aberta:
    preco_entrada = close[0]
    stop_loss = preco_entrada - (STOP_MULTIPLICADOR × atr[0])
    take_profit = preco_entrada + (TP_MULTIPLICADOR × atr[0])

    # Cálculo do tamanho da posição
    risco_usdt = capital_total × RISCO_POR_TRADE
    distancia_stop = preco_entrada - stop_loss
    quantidade_btc = risco_usdt / distancia_stop

    # Validação de segurança
    valor_posicao = quantidade_btc × preco_entrada
    SE valor_posicao > capital_total × 0.20:
        quantidade_btc = (capital_total × 0.20) / preco_entrada

    EXECUTAR ordem_compra(quantidade_btc, preco_entrada)
    REGISTRAR stop_loss, take_profit, preco_entrada

# SAÍDA — TAKE PROFIT
SE posicao_aberta E close[0] >= take_profit:
    EXECUTAR ordem_venda(quantidade_total)
    REGISTRAR resultado("take_profit")

# SAÍDA — STOP LOSS
SE posicao_aberta E close[0] <= stop_loss:
    EXECUTAR ordem_venda(quantidade_total)
    REGISTRAR resultado("stop_loss")

# SAÍDA — SINAL INVERSO (crossdown)
crossdown_ocorreu = (ema8[0] < ema21[0]) AND (ema8[1] >= ema21[1])
SE posicao_aberta E crossdown_ocorreu:
    EXECUTAR ordem_venda(quantidade_total)
    REGISTRAR resultado("sinal_inverso")

# STOP DIÁRIO
pnl_hoje = calcular_pnl_do_dia()
SE pnl_hoje <= -0.03 × capital_total:
    DESATIVAR_BOT_ATÉ_AMANHÃ()
    LOGAR("Stop diário atingido: " + pnl_hoje)
```

---

## Métricas Alvo no Backtest

| Métrica | Meta Mínima | Meta Ideal |
|---|---|---|
| Sharpe Ratio | > 1.0 | > 1.5 |
| Max Drawdown | < 20% | < 15% |
| Win Rate | > 40% | > 48% |
| Profit Factor | > 1.5 | > 1.8 |
| Total de trades (período) | > 30 | > 50 |
| R:R médio realizado | > 1.8:1 | > 2:1 |

**Período mínimo de backtest:** 12 meses (pelo menos 1 ciclo de bull + bear ou lateral)  
**Período recomendado:** 2021–2026 (inclui bull 2021, bear 2022, recuperação 2023, bull 2024–2025)

---

## Notas para o Desenvolvedor (Fase 3)

1. **Freqtrade:** Implementar como estratégia customizada. Os indicadores `ema`, `rsi`, `atr` e `sma` estão todos disponíveis via `ta-lib` ou `pandas-ta`.
2. **Candle fechado:** Usar `process_only_new_candles = True` e garantir que os sinais são avaliados apenas no fechamento do candle (não intracandle).
3. **Ordem de compra:** Usar ordem limit no preço de fechamento (ou levemente acima) para capturar sinais sem slippage excessivo.
4. **Stop e TP:** Implementar via `stoploss` e `minimal_roi` do Freqtrade, ou via `custom_stoploss` para o ATR dinâmico.
5. **Backtest inicial:** Rodar de 2022-01-01 a 2026-06-01 com capital inicial de $1.000 (simulação).
6. **Otimização:** Após backtest base aprovado, usar `hyperopt` do Freqtrade para ajustar RSI_MIN, RSI_MAX e multiplicadores de ATR.
7. **Atenção ao overfitting:** Não otimizar com mais de 3–4 parâmetros simultaneamente na primeira rodada.

---

*Documento gerado pelo sub-agente Analista — Fase 2 do projeto Safe Trading*
