# Comparação de Estratégias de Swing Trade — BTC/USDT 4H

**Mercado:** BTC/USDT Binance Spot  
**Timeframe principal:** 4H (confirmação no 1D)  
**Data da análise:** Junho 2026  
**Custo por trade:** 0.1% taxa Binance + 0.05% slippage = 0.15% por lado → 0.30% round-trip

---

## 1. Tabela Comparativa

| Métrica | Variação A: EMA 8/21 + RSI + Volume | Variação B: EMA 21/55 + ATR Stop | Variação C: RSI Mean Reversion | Variação D: BB Breakout + Volume + EMA50 |
|---|---|---|---|---|
| **Win Rate típico (4H)** | 45–52% | 40–48% | 55–65% | 38–45% |
| **Sharpe Ratio médio** | 1.0–1.5 | 0.8–1.2 | 0.6–1.0 | 0.7–1.1 |
| **Max Drawdown típico** | 18–28% | 20–30% | 25–40% | 22–35% |
| **Trades/mês estimados (4H)** | 6–12 | 4–8 | 8–15 | 5–10 |
| **Profit Factor médio** | 1.5–2.0 | 1.4–1.9 | 1.3–1.7 | 1.3–1.8 |
| **R:R típico por trade** | 2:1 | 2–3:1 | 1:1 a 1.5:1 | 2:1 a 2.5:1 |
| **Complexidade impl. (1–5)** | 3 | 2 | 2 | 4 |
| **Adequação ao Freqtrade** | Alta | Alta | Média | Média |

> **Nota sobre os dados:** métricas baseadas em backtests públicos documentados (QuantifiedStrategies, FMZQuant, Freqst, Medium/Superalgos). Valores conservadores — medianas, não picos. Resultados reais esperados em 60–70% dos valores de backtest.

---

## 2. Análise Detalhada por Variação

### Variação A — EMA 8/21 crossover + RSI(14) filtro + Volume confirmation

**Lógica:** EMA curta (8) cruza acima da EMA longa (21) = sinal de compra, mas apenas se RSI(14) estiver entre 40–65 (não sobrecomprado) e volume do candle de sinal for maior que a média de 20 períodos.

**Prós:**
- Combinação clássica e bem documentada — extenso histórico de backtests públicos
- Filtros RSI e volume reduzem entradas em falsos rompimentos
- Boa frequência de trades (suficiente para validação estatística — 30+ trades em 3–5 meses)
- Naturalmente compatível com a estrutura de estratégias do Freqtrade
- Balanceia bem trend-following com qualidade de entrada
- Sharpe Ratio mediano de 1.0–1.5 é adequado para operação real

**Contras:**
- EMA 8/21 em 4H gera algum ruído — mercado lateral produz whipsaws ocasionais
- RSI como filtro (não gerador de sinal) é menos poderoso isoladamente
- Requer parametrização cuidadosa do threshold de volume
- Em bull market extremo, filtro RSI pode bloquear entradas válidas (RSI >65 mas tendência forte)

**Considerações BTC/USDT 4H:**
BTC tem ciclos de bull/bear bem definidos. A EMA 8/21 captura bem as tendências intermediárias. O filtro RSI impede entradas quando o ativo já está muito esticado — adequado para Spot (sem alavancagem, onde preservar capital é prioridade). Custo de 0.30% round-trip é absorvido facilmente com RR 2:1 e win rate >45%.

---

### Variação B — EMA 21/55 crossover + ATR stop

**Lógica:** EMA mais lenta (21 e 55). Crossover gera sinal. Stop loss dinâmico baseado em ATR(14), posicionado a 1.5–2×ATR abaixo da entrada.

**Prós:**
- Menos ruído que 8/21 — sinais mais confiáveis, menos falsos positivos
- ATR stop se adapta à volatilidade de BTC (essencial: BTC tem volatilidade muito variável)
- Menor drawdown em mercados laterais (menos trades = menos perdas por whipsaw)
- Implementação simples — apenas 2 EMAs + ATR

**Contras:**
- Menor frequência de trades → menos dados para validação estatística (risco de não atingir 30+ trades em backtest curto)
- Entradas mais tardias — o sinal vem depois que parte do movimento já ocorreu
- Max drawdown ainda expressivo (20–30%) porque stops por ATR em BTC podem ser amplos
- Win rate mais baixo (40–48%) exige R:R maior para ser lucrativo

**Considerações BTC/USDT 4H:**
A EMA 21/55 é mais adequada para timeframe 1D. No 4H, o cruzamento pode ser lento demais, gerando entradas no meio ou fim de movimentos. Bom para traders que preferem menor intervenção, porém estatisticamente mais difícil de validar com poucos meses de backtest.

---

### Variação C — RSI(14) Mean Reversion (compra <35, vende >65, stop 2×ATR)

**Lógica:** Contratendência — compra quando RSI(14) cai abaixo de 35 (sobrevenda) e vende quando RSI sobe acima de 65 (sobrecompra) ou stop por 2×ATR é atingido.

**Prós:**
- Win rate mais alto (55–65%) — estatisticamente mais confortável para iniciantes
- Lógica intuitiva e simples de implementar
- Captura bem correções em bull market consolidado

**Contras:**
- **CRÍTICO:** Mean reversion é inadequada para crypto no longo prazo. BTC pode ficar sobrevendido (RSI <35) por semanas durante bear markets — o sistema compra em queda livre
- Drawdown elevado (25–40%) — o maior da lista, especialmente em 2022 e 2018
- R:R limitado (1:1 a 1.5:1) — win rate alto é necessário para compensar, mas não é garantido
- Custo de 0.30% round-trip corrói mais os trades com menor R:R
- Não segue a tendência principal — vai na contramão em mercados direcionais

**Considerações BTC/USDT 4H:**
BTC tem tendências prolongadas. Comprar "porque caiu muito" sem confirmar reversão vai contra a natureza do ativo. O drawdown máximo de 25–40% é inaceitável para uma estratégia iniciante em Spot. **Estratégia inadequada para o objetivo do projeto.**

---

### Variação D — Bollinger Bands breakout + Volume spike + EMA 50 trend filter

**Lógica:** Preço rompe a banda superior de Bollinger (BB 20, 2σ) com volume acima da média de 20 períodos AND preço acima da EMA 50 = entrada LONG. Stop abaixo da banda média.

**Prós:**
- Combina 3 confirmações — reduz sinais falsos
- EMA 50 como filtro de tendência é robusto
- Bom R:R potencial quando o breakout é genuíno

**Contras:**
- Maior complexidade de implementação (4/5) — 3 indicadores com mais interações
- Estratégia de breakout sofre muito em mercados laterais (false breakouts frequentes em BTC)
- Baixo win rate (38–45%) — exige R:R 2.5:1+ para ser lucrativo, o que muitas vezes não é atingido
- Volume spike em BTC no 4H é difícil de parametrizar (qual threshold exato?)
- Mais parâmetros = maior risco de overfit no backtest

**Considerações BTC/USDT 4H:**
Breakout de Bollinger funciona bem em BTC durante rompimentos de consolidação (ex: antes de ATH), mas gera muitos falsos sinais nos períodos laterais. A complexidade adicional torna a estratégia menos adequada para a Fase 3 (primeira implementação em Freqtrade).

---

## 3. Considerações de Custo (Binance Spot)

| Custo | Valor |
|---|---|
| Taxa maker/taker Binance | 0.10% por lado |
| Slippage estimado (BTC spot) | 0.05% por lado |
| **Total round-trip** | **0.30%** |

**Impacto por estratégia:**

- Com R:R 2:1 e win rate 45%: lucro esperado por trade = (0.45 × 2R) - (0.55 × R) = 0.35R bruto → custo de 0.30% é ~15–20% do ganho médio esperado → aceitável
- Com R:R 1:1 (Variação C): custo come proporção muito maior → prejudica significativamente
- Estratégias com mais trades/mês acumulam mais custo → prefira qualidade sobre quantidade de sinais

**Recomendação de execução:** Usar ordens limit (maker) sempre que possível para reduzir custo total para ~0.20% round-trip.

---

## 4. Resumo da Comparação

| Critério | A | B | C | D |
|---|---|---|---|---|
| Risco/retorno adequado | Sim | Sim | Não | Sim |
| Adequação a BTC com tendência | Sim | Sim | Não | Sim |
| Simplicidade de implementação | Boa | Ótima | Ótima | Fraca |
| Frequência de trades suficiente | Sim | Marginal | Sim | Sim |
| Drawdown controlado (<30%) | Sim | Marginal | Não | Marginal |
| Documentação pública robusta | Sim | Sim | Sim | Limitada |
| **Score geral** | **5/5** | **4/5** | **2/5** | **3/5** |

**Estratégia escolhida: Variação A — EMA 8/21 + RSI(14) + Volume confirmation**

Ver documento `estrategia-escolhida.md` para spec completa de implementação.

---

*Fontes: QuantifiedStrategies.com, FMZQuant/Medium, Freqst.com, Superalgos/Medium, TradeSearcher.ai, stoic.ai, barchart.com*
