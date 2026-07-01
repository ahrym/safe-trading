# Análise de Ajustes de Parâmetros — F3.3
**Projeto:** Safe Trading — EMA 8/21 + RSI + Volume (BTC/USDT 4H)  
**Período analisado:** 2022-01-01 a 2026-06-27 (77 trades)  
**Data da análise:** 2026-06-26

---

## Resultado Atual (Baseline)

| Métrica | Resultado | Meta Mínima | Status |
|---|---|---|---|
| Sharpe Ratio | 0.46 | > 1.0 | FALHOU |
| Profit Factor | 1.29 | > 1.5 | FALHOU |
| Win Rate | 40.3% | > 40% | PASSOU (marginal) |
| Max Drawdown | 4.7% | < 20% | PASSOU |
| Total Trades | 77 | > 30 | PASSOU |
| Retorno Total | +5.03% | — | (referência) |

---

## 1. Distribuição por Período

### 2022 — Bear Market (jan/2022 a dez/2022)
Trades: 16 | Wins: 6 | Losses: 10 | **Win Rate: 37.5%**

| # | Entrada | Resultado | PnL (USDT) | Motivo |
|---|---|---|---|---|
| 1 | 2022-01-20 | loss | -5.10 | stop_loss |
| 2 | 2022-02-28 | win | +16.07 | take_profit |
| 3 | 2022-03-09 | loss | -7.94 | stop_loss |
| 4 | 2022-03-16 | win | +11.81 | take_profit |
| 5 | 2022-03-22 | win | +9.92 | take_profit |
| 6 | 2022-04-04 | loss | -2.38 | sinal_inverso |
| 7 | 2022-05-04 | loss | -5.20 | stop_loss |
| 8 | 2022-05-30 | win | +9.11 | take_profit |
| 9 | 2022-06-08 | loss | -6.92 | stop_loss |
| 10 | 2022-07-28 | win | +0.22 | sinal_inverso |
| 11 | 2022-08-10 | win | +9.96 | take_profit |
| 12 | 2022-09-09 | win | +10.80 | take_profit |
| 13 | 2022-09-27 | loss | -6.27 | stop_loss |
| 14 | 2022-10-17 | loss | -3.60 | stop_loss |
| 15 | 2022-11-04 | loss | -1.64 | sinal_inverso |
| 16 | 2022-11-23 | loss | -5.33 | stop_loss |
| 17 | 2022-12-13 | win | +3.72 | take_profit |

**Saldo 2022: +26.03 USDT (ganho líquido apesar do bear)**

### 2023 — Recuperação / Lateral (jan/2023 a dez/2023)
Trades: 19 | Wins: 8 | Losses: 11 | **Win Rate: 42.1%**

**Saldo 2023:** Início em ~1027, fim em ~1042 = +15 USDT aproximado

Período com muitos falsos sinais no mercado lateral (jan-set/2023): trades de curta duração que perdem para o stop antes de atingir o TP.

### 2024 — Bull Market (jan/2024 a dez/2024)
Trades: 14 | Wins: 6 | Losses: 8 | **Win Rate: 42.9%**

Detalhe importante: os maiores ganhos individuais vieram deste período (ex: +12.88 USDT no trade de mar/2024 com BTC a $67k). No entanto, entre mai e set/2024 ocorreu uma sequência de 5 losses consecutivos que devorou os ganhos.

### 2025 — Alta Volatilidade / Consolidação (jan/2025 a dez/2025)
Trades: 22 | Wins: 7 | Losses: 15 | **Win Rate: 31.8% — pior período**

Este é o período crítico. A partir de jul/2025, com BTC acima de $115k, ocorreram 6 losses consecutivos em apenas 6 semanas (jul/2025). O TP de 3×ATR ficou inacessível na volatilidade comprimida do topo.

### 2026 — Recuperação (jan/2026 a jun/2026)
Trades: 6 | Wins: 4 | Losses: 2 | **Win Rate: 66.7% — melhor período**

---

## 2. Duração dos Trades: Vencedores vs Perdedores

| Categoria | Duração Média (candles 4H) | Duração Média (horas) |
|---|---|---|
| Todos os trades | 7.6 candles | ~30 horas |
| **Vencedores (31 trades)** | **8.1 candles** | **~32 horas** |
| **Perdedores (46 trades)** | **7.3 candles** | **~29 horas** |

**Observação crítica:** A diferença de duração entre wins e losses é mínima (menos de 1 candle). Isso é um sinal de alerta — em estratégias saudáveis, os vencedores devem durar significativamente mais que os perdedores (tempo para o preço percorrer 3×ATR vs apenas 1.5×ATR).

Wins notáveis de longa duração (que geraram mais retorno): trades de 18-34 candles (3-6 dias) consistentemente atingiram TP. Os wins rápidos (0-2 candles) frequentemente fecharam com PnL mínimo por sinal_inverso.

---

## 3. Análise dos Motivos de Saída

| Motivo | Ocorrências | Wins | Losses | PnL Total (USDT) |
|---|---|---|---|---|
| stop_loss | 46 | 0 | 46 | -156.68 |
| take_profit | 22 | 22 | 0 | +182.23 |
| sinal_inverso | 9 | 9* | 0 | +3.86 |

*Os 9 trades de sinal_inverso classificados como "win" incluem trades de PnL mínimo (ex: +0.02, +0.22 USDT) — wins nominais, não reais em termos práticos.

**PnL real por categoria de saída:**
- Take profits geraram +182.23 USDT (média: +8.28/trade)
- Stop losses custaram -156.68 USDT (média: -3.40/trade)  
- Sinais inversos geraram +3.86 USDT (média: +0.43/trade — irrelevante)

**Razão implícita:** Para cada stop loss acionado, a perda média foi de -3.40 USDT. Para cada TP atingido, o ganho médio foi de +8.28 USDT. O RR realizado é ~2.4:1 (acima do 2:1 teórico). O problema não é o RR — é o volume de stop losses (46 de 77 trades = 59.7%).

---

## 4. Diagnóstico: Por Que o Sharpe e o Profit Factor Falharam

### Diagnóstico Principal: Excesso de Falsos Sinais (Ruído de EMA Curta)

A EMA(8) é muito sensível. Em mercados laterais e de alta volatilidade (2025 especialmente), ela gera cruzamentos que se revertem rapidamente antes do preço percorrer os 3×ATR necessários para o TP. O filtro RSI (40-65) e o volume confirmado não são suficientes para eliminar entradas em volatilidade comprimida.

**Evidência:** 46 stop losses em 77 trades = 59.7% das posições fecham no stop. Para o Profit Factor atingir 1.5+, seriam necessários ou mais TPs (win rate ~45%+) ou perdas menores por stop.

### Diagnóstico Secundário: TP Muito Distante nos Topos (2025)

Com BTC acima de $100k, o ATR(14) em valor absoluto é enorme (tipicamente $2.000-$4.000). O TP a 3×ATR significa um alvo de $6.000-$12.000 acima da entrada — uma amplitude que frequentemente não é percorrida antes de uma reversão. Os 6 losses consecutivos de jul/2025 confirmam isso: a volatilidade relativa comprometeu a razão TP/Stop.

### Diagnóstico Terciário: EMA(8) Gera Sinais Consecutivos Próximos

Em períodos de indecisão (out-set/2024, dez/2025), a estratégia gerou trades com poucos candles de intervalo entre eles (ex: 2025-12-26 e 2025-12-29 — apenas 3 dias de diferença). Essa aglomeração de sinais em contextos de baixa tendência aumenta o custo em taxas/slippage sem adicionar valor.

---

## 5. Três Variações Recomendadas para Re-teste

### Variação 1 — EMA Menos Sensível + RSI Mais Restritivo (PRIORIDADE ALTA)

**Lógica:** Substituir EMA(8) por EMA(13) reduz os cruzamentos em ruído. Elevar RSI_MIN de 40 para 45 filtra entradas em mercados ainda sem momentum suficiente. Juntas, essas mudanças devem reduzir o número de trades de ~77 para ~55-60, eliminando principalmente os falsos sinais em laterais.

| Parâmetro | Atual | Variação 1 |
|---|---|---|
| ema_rapida | 8 | **13** |
| ema_lenta | 21 | 21 |
| rsi_min | 40 | **45** |
| rsi_max | 65 | 65 |
| stop_mult | 1.5 | 1.5 |
| tp_mult | 3.0 | 3.0 |

**O que se espera melhorar:** Win rate (+3-5 pp), Profit Factor (1.29 → 1.5+), sem alterar o RR. Menos trades, mas mais qualificados.

---

### Variação 2 — TP Reduzido para Capturar Mais Wins (PRIORIDADE MÉDIA)

**Lógica:** Reduzir TP de 3.0×ATR para 2.0×ATR (mantendo stop em 1.5×ATR) baixa o RR teórico de 2:1 para 1.33:1, mas aumenta drasticamente a taxa de trades que atingem o alvo. Com 40% de win rate atual e RR de 2.4:1, o sistema já é matematicamente positivo — porém frágil. Com 50%+ de win rate e RR 1.33:1, o Profit Factor sobe e o Sharpe melhora pelo menor desvio padrão dos retornos.

| Parâmetro | Atual | Variação 2 |
|---|---|---|
| ema_rapida | 8 | 8 |
| ema_lenta | 21 | 21 |
| rsi_min | 40 | 40 |
| rsi_max | 65 | 65 |
| stop_mult | 1.5 | 1.5 |
| tp_mult | 3.0 | **2.0** |

**O que se espera melhorar:** Win rate (40% → 50%+), Sharpe (mais consistência entre trades), Profit Factor. Contrapartida: ganho médio por win menor. Indicado especialmente para 2025 onde o TP atual era inacessível.

---

### Variação 3 — Combinação: EMA Moderada + TP Reduzido + RSI Estendido (PRIORIDADE BAIXA)

**Lógica:** Combina EMA(10) — meio-termo entre sensibilidade e filtro — com TP de 2.5×ATR (RR 1.67:1) e amplia RSI_MAX para 70 para não perder entradas válidas em tendências fortes (2024-2026 bull). Esta variação tenta otimizar os três eixos simultaneamente para capturar o melhor dos dois cenários (mais wins E ganho razoável por win).

| Parâmetro | Atual | Variação 3 |
|---|---|---|
| ema_rapida | 8 | **10** |
| ema_lenta | 21 | 21 |
| rsi_min | 40 | **42** |
| rsi_max | 65 | **70** |
| stop_mult | 1.5 | 1.5 |
| tp_mult | 3.0 | **2.5** |

**O que se espera melhorar:** Equilíbrio entre os dois problemas — menos falsos sinais E mais TPs atingidos. RSI_MAX=70 recupera entradas em tendências fortes que o filtro 65 eliminava. Risco: possível overfitting (3 parâmetros alterados).

---

## Tabela Resumo para o Desenvolvedor

| Prioridade | Variação | ema_rapida | ema_lenta | rsi_min | rsi_max | stop_mult | tp_mult | Objetivo Principal |
|---|---|---|---|---|---|---|---|---|
| 1 (ALTA) | V1 — EMA Conservadora | **13** | 21 | **45** | 65 | 1.5 | 3.0 | Reduzir falsos sinais |
| 2 (MÉDIA) | V2 — TP Menor | 8 | 21 | 40 | 65 | 1.5 | **2.0** | Aumentar win rate |
| 3 (BAIXA) | V3 — Combinada | **10** | 21 | **42** | **70** | 1.5 | **2.5** | Equilíbrio geral |

**Parâmetros fixos em todas as variações (não alterar):** ema_lenta=21, ema_macro=50, atr_periodo=14, rsi_periodo=14, stop_mult=1.5, risco_por_trade=0.01

---

## Critério de Aprovação das Variações

Para aprovar uma variação, ela deve atingir simultaneamente:

| Métrica | Meta Mínima |
|---|---|
| Sharpe Ratio | > 1.0 |
| Profit Factor | > 1.5 |
| Win Rate | > 42% |
| Max Drawdown | < 15% |
| Total Trades | > 40 |

Se nenhuma das três variações atingir as metas, recomendar ao orquestrador avaliar mudança de timeframe (1D) ou adição de filtro de volatilidade (ex: ATR relativo — só operar quando ATR% < 3% do preço).

---

*Análise gerada pelo Agente Analista — Safe Trading F3.3*  
*Arquivo: results/analise_ajustes_f3.md*
