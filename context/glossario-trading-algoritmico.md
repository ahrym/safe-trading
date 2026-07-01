# Glossário de Trading Algorítmico — Safe Trading

> Documento técnico de referência para o projeto Safe Trading. Fase 1 — Fundamentação.
> Produzido pelo sub-agente Pesquisador. Data: 2026-06-26.
> Cada termo inclui: definição técnica + relevância prática para o projeto.

---

## A

### Alpha (α)
**Definição**: Retorno de uma estratégia acima do que seria esperado dado o risco assumido (beta). Representa o "valor agregado" da estratégia ou do gestor.

**Fórmula simplificada**: `α = retorno_estratégia - (β × retorno_benchmark)`

**Relevância para o projeto**: O objetivo do Safe Trading é gerar alpha consistente. Uma estratégia com alpha positivo supera o mercado (ex: superar BTC buy-and-hold no mercado crypto). Medir alpha é fundamental para avaliar se o bot realmente agrega valor ou apenas replica o mercado.

### ATR (Average True Range)
Veja seção completa em `indicadores-tecnicos.md`. Medida de volatilidade absoluta. Indispensável para dimensionar stops e tamanhos de posição.

---

## B

### Backtesting
**Definição**: Processo de aplicar uma estratégia de trading a dados históricos para simular como ela teria se comportado no passado. Não garante performance futura, mas é o primeiro filtro de validação.

**Fases do backtesting:**
1. Coleta de dados históricos (OHLCV)
2. Definição das regras de entrada/saída
3. Simulação da execução com custos (taxas, slippage)
4. Cálculo de métricas de performance

**Riscos do backtesting:**
- Overfitting (ver abaixo)
- Look-ahead bias (ver abaixo)
- Não considerar slippage real
- Survivorship bias (usar apenas ativos que "sobreviveram")

**Relevância para o projeto**: Toda estratégia passa por backtesting rigoroso ANTES de qualquer execução real. A F3 do Safe Trading é dedicada a backtests.

**Ferramentas recomendadas**: `backtrader`, `vectorbt`, `backtesting.py`

### Beta (β)
**Definição**: Medida de correlação entre a estratégia e o mercado de referência (benchmark). Beta = 1 significa que a estratégia move igual ao mercado. Beta > 1 é mais volátil que o mercado.

**Fórmula**: `β = Cov(estratégia, benchmark) / Var(benchmark)`

**Relevância para o projeto**: Um bot com beta baixo (< 0.5) em relação ao BTC indica que ele gera retornos mais independentes do mercado — o que é desejável para uma estratégia robusta.

### Benchmark
**Definição**: Referência de performance para comparar a estratégia. 

| Mercado | Benchmark típico |
|---|---|
| Crypto | BTC/USDT buy-and-hold |
| Ações B3 | IBOVESPA (buy-and-hold) |
| Geral | CDI (taxa livre de risco brasileira) |

---

## C

### Candlestick (OHLCV)
Representação visual de preço em um período. Campos: Open, High, Low, Close, Volume.
Veja detalhes completos em `fundamentos-mercado.md`.

### Comissão
**Definição**: Taxa cobrada pela exchange ou corretora por cada transação executada.

| Exchange/Mercado | Taxa típica |
|---|---|
| Binance Spot | 0.1% por lado (maker/taker) |
| Binance Futuros | 0.02% maker / 0.05% taker |
| B3 (emolumentos) | ~0.025% por lado |
| B3 (corretora) | Variável; muitas = R$0 para ações |

**Impacto no backtest**: SEMPRE incluir comissão. Um sistema com 60% de win rate pode ser prejudicado por custos altos em alta frequência de trades.

```python
# Cálculo correto de P&L com comissão
taxa = 0.001  # 0.1%
preco_compra = 67_000
preco_venda = 68_000
quantidade = 0.01  # BTC

custo_entrada = preco_compra * quantidade * (1 + taxa)
receita_saida = preco_venda * quantidade * (1 - taxa)
lucro_liquido = receita_saida - custo_entrada
```

### Contrato (B3)
**Definição**: Instrumento derivativo padronizado negociado na B3. Cada contrato representa uma quantidade fixa do ativo subjacente.

| Contrato | Símbolo | Tamanho | Vencimento |
|---|---|---|---|
| Mini-índice | WIN | 0.2 ponto do IBOV = R$0,20 | Mensal (3ª segunda-feira) |
| Mini-dólar | WDO | R$10 por ponto | Mensal (1º dia útil) |
| Índice cheio | IND | 1 ponto = R$1,00 | Mensal |
| Dólar cheio | DOL | R$50 por ponto | Mensal |

**Relevância para o projeto**: Mini-contratos são o instrumento da F5. WIN e WDO têm altíssima liquidez na B3.

### Correlação de Ativos
**Definição**: Medida estatística (-1 a +1) de como dois ativos se movem em relação um ao outro.

| Correlação | Interpretação |
|---|---|
| +1.0 | Movimento idêntico |
| +0.7 a +0.9 | Alta correlação positiva |
| 0 | Sem relação linear |
| -0.7 a -0.9 | Alta correlação negativa |
| -1.0 | Movimento oposto perfeito |

**Relevância para o projeto**: Ao operar múltiplos ativos (ex: BTC + ETH), correlação alta = concentração de risco. Diversificação real exige ativos com baixa correlação entre si.

---

## D

### Data Leakage
**Definição**: Erro de implementação em que informações do futuro "vazam" para o cálculo de um indicador usado no passado. Similar ao look-ahead bias, mas geralmente ocorre no pré-processamento de dados para ML.

**Exemplo**: usar o preço máximo da próxima semana como feature para decidir se comprar hoje.

**Como evitar**: 
- Usar `.shift(1)` em pandas para garantir que só dados passados entrem no cálculo
- Em ML: fazer normalização DENTRO do fold de cross-validation, nunca antes

**Relevância para o projeto**: Em modelos de ML (fases avançadas), data leakage pode inflar métricas de validação e criar sistemas que "funcionam no backtest mas falham no live".

### Drawdown
Veja Max Drawdown abaixo.

---

## F

### Forward Testing (Paper Trading Live)
**Definição**: Executar a estratégia em condições reais de mercado (preços ao vivo), mas sem dinheiro real (usando conta simulada ou acompanhando manualmente).

**Diferença do backtesting**: usa dados futuros reais, não históricos. Valida o sistema em condições de mercado não vistas durante o desenvolvimento.

**Fluxo recomendado para o Safe Trading:**
```
Backtesting → Forward Testing (2-4 semanas) → Paper Trading → Live Trading
```

**Relevância**: Forward testing é a ponte obrigatória entre o backtest e o capital real. Captura erros de implementação, latência, slippage real e comportamentos inesperados da API.

---

## L

### Latência (Latency)
**Definição**: Tempo entre o sinal de entrada/saída gerado pelo bot e a confirmação de execução pela exchange.

| Tipo | Valores típicos |
|---|---|
| Binance REST API (round-trip) | 50-200ms |
| Binance WebSocket | < 10ms |
| B3 via brapi.dev | 15 min (delay regulatório) |
| B3 DMA (colocation) | < 1ms |

**Relevância para o projeto**: Em swing trade (entradas diárias), latência de 200ms é irrelevante. Em day trade ou HFT, latência é crítica. O Safe Trading (swing trade) não tem requisitos de baixíssima latência.

### Live Trading
**Definição**: Execução da estratégia com dinheiro real em condições reais de mercado.

**Pré-requisitos antes de ir live:**
1. Backtesting aprovado (Sharpe > 1, MaxDD aceitável)
2. Forward testing por pelo menos 2-4 semanas
3. Paper trading validado
4. Capital de risco definido (apenas o que se pode perder)
5. Sistema de monitoramento e alertas ativo
6. Plano de emergência (como desligar o bot rapidamente)

### Long
**Definição**: Posição comprada. O trader compra um ativo esperando que seu preço suba.

```
Compra a $67.000 → Preço sobe para $70.000 → Vende → Lucro de $3.000
```

**No mercado spot**: só é possível ir long (comprar para vender depois).
**Em futuros**: tanto long quanto short são nativos.

### Look-ahead Bias
**Definição**: Erro grave de backtesting onde o algoritmo usa informações que não estariam disponíveis no momento da decisão (ex: o fechamento do candle atual antes dele fechar).

**Exemplo clássico**:
```python
# ERRADO: usa o fechamento do candle atual para tomar decisão
if df['close'][i] > df['ema21'][i]:  # ambos referem ao mesmo candle
    comprar()

# CORRETO: usa o fechamento do candle ANTERIOR para tomar decisão
if df['close'][i-1] > df['ema21'][i-1]:  # decisão no início do candle i
    comprar()
```

**Relevância**: Um backtest com look-ahead bias pode mostrar lucros impossíveis de replicar em live. É o erro mais frequente em bots desenvolvidos por iniciantes.

### Lote
**Definição**: Quantidade mínima ou padrão de um ativo para negociação.

| Mercado | Lote mínimo |
|---|---|
| B3 Ações | 100 ações (lote padrão) ou 1 ação (fracionário "F") |
| B3 Mini-índice WIN | 1 contrato |
| Binance BTC/USDT | 0.00001 BTC (mínimo) |
| Binance (mínimo em USDT) | ~$5 por ordem |

---

## M

### Max Drawdown (MDD)
**Definição**: Maior queda percentual de pico a vale na curva de capital da estratégia durante o período analisado.

```
Curva de capital: 10.000 → 12.000 → 8.000 → 11.000

Pico: 12.000
Vale subsequente: 8.000
Max Drawdown = (12.000 - 8.000) / 12.000 = 33.3%
```

**Interpretação**:

| MDD | Avaliação |
|---|---|
| < 10% | Excelente (estratégia conservadora) |
| 10-20% | Bom (swing trade típico) |
| 20-35% | Aceitável (depende do perfil) |
| > 35% | Alto risco (difícil de seguir psicologicamente) |

**Relevância para o projeto**: O MDD define se o operador CONSEGUE psicologicamente seguir a estratégia. Um sistema com 50% de retorno anual mas 60% de MDD é inviável para a maioria.

### Mercado Lateral (Sideways/Ranging)
**Definição**: Condição de mercado onde o preço oscila entre suporte e resistência sem tendência clara.

**Impacto em estratégias de tendência**: Indicadores como MACD e EMA crossover geram muitos falsos sinais em mercados laterais (whipsaws).

**Como detectar**: ADX (Average Directional Index) < 20 indica mercado sem tendência.

---

## O

### OHLCV
**Definição**: Open, High, Low, Close, Volume — os 5 campos de dado de preço de um candlestick. É a estrutura fundamental de dados para qualquer análise técnica.

```python
# Estrutura típica em DataFrame pandas
import pandas as pd

df = pd.DataFrame({
    'open':   [67000, 67500, 67200],
    'high':   [67800, 67900, 67600],
    'low':    [66800, 67100, 66900],
    'close':  [67500, 67200, 67400],
    'volume': [1250.5, 980.3, 1100.1]  # em BTC
}, index=pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03']))
```

### Overfitting
**Definição**: Quando uma estratégia é excessivamente otimizada para dados históricos específicos, capturando ruído estatístico em vez de padrões genuínos. Resulta em performance excelente no backtest e terrível em live trading.

**Sinais de alerta:**
- Estratégia com dezenas de parâmetros otimizados
- Sharpe ratio do backtest > 3 (improvável em condições reais)
- Performance degradando muito no out-of-sample
- Regras muito específicas (ex: "entrar toda segunda-feira às 14h32")

**Como evitar:**
1. Usar poucos parâmetros (princípio da parcimônia)
2. Aplicar walk-forward validation
3. Manter um conjunto de dados out-of-sample nunca visto durante o desenvolvimento
4. Testar a estratégia em diferentes ativos e períodos

**Relevância para o projeto**: A diferença entre um bot que funciona e um que falha muitas vezes é overfitting. Validação robusta é obrigatória antes de ir a live.

---

## P

### Paper Trading
**Definição**: Trading simulado com dinheiro virtual usando condições reais de mercado (preços ao vivo). Diferente do forward testing manual, geralmente é automatizado.

**Na Binance**: disponível via Testnet (`testnet.binance.vision`) com API keys separadas.

```python
# Configurar CCXT para testnet Binance
exchange = ccxt.binance({
    'apiKey': 'KEY_DO_TESTNET',
    'secret': 'SECRET_DO_TESTNET',
})
exchange.set_sandbox_mode(True)  # Ativa o modo testnet
```

### Pip
**Definição**: Menor variação de preço em um mercado específico.

| Mercado | Pip |
|---|---|
| WDO (Mini-dólar B3) | R$0,50 por ponto = R$10/contrato |
| WIN (Mini-índice B3) | 1 ponto do IBOV = R$0,20/contrato |
| Forex EUR/USD | 0.0001 |

### Profit Factor
**Definição**: Razão entre o total de lucros brutos e o total de perdas brutas.

```
Profit Factor = Total de Ganhos Brutos / Total de Perdas Brutas

PF = 1.5 significa que para cada R$1 perdido, o sistema ganha R$1,50
```

| Profit Factor | Avaliação |
|---|---|
| < 1.0 | Sistema com prejuízo |
| 1.0 – 1.2 | Marginalmente lucrativo (frágil) |
| 1.2 – 1.5 | Aceitável |
| 1.5 – 2.0 | Bom |
| > 2.0 | Excelente |

---

## R

### Risk/Reward Ratio (RR)
**Definição**: Razão entre o lucro potencial (take profit) e a perda máxima aceita (stop loss) por trade.

```
RR 2:1 significa: para cada $1 arriscado, espero ganhar $2

Exemplo:
  Entrada: $67.000
  Stop: $66.000    → risco = $1.000
  Target: $69.000  → potencial = $2.000
  RR = 2.000 / 1.000 = 2:1
```

**Win rate mínimo por RR para ser lucrativo (antes de taxas):**

| Risk/Reward | Win Rate Mínimo |
|---|---|
| 1:1 | > 50% |
| 2:1 | > 33% |
| 3:1 | > 25% |

**Relevância para o projeto**: O Safe Trading usará RR mínimo de 2:1 em todas as estratégias. Isso significa que o sistema pode ter apenas 40% de win rate e ainda ser lucrativo.

---

## S

### Sharpe Ratio
**Definição**: Medida de retorno ajustado ao risco. Compara o retorno excedente da estratégia (acima da taxa livre de risco) com a volatilidade dos retornos.

```
Sharpe Ratio = (Retorno Médio - Taxa Livre de Risco) / Desvio Padrão dos Retornos

(Tipicamente calculado com retornos diários anualizados)
```

| Sharpe Ratio | Avaliação |
|---|---|
| < 0 | Estratégia com retorno abaixo da taxa livre de risco |
| 0 – 1.0 | Aceitável mas pode ser melhorado |
| 1.0 – 1.5 | Bom |
| 1.5 – 2.0 | Muito bom |
| > 2.0 | Excelente (difícil de sustentar) |
| > 3.0 | Suspeito de overfitting |

**Limitação**: o Sharpe penaliza tanto a volatilidade negativa quanto a positiva (ganhos grandes também aumentam o desvio padrão). Por isso, o Sortino Ratio é preferido.

**Taxa livre de risco brasileira**: CDI (~10.75% a.a. em 2025).

### Short
**Definição**: Posição vendida. O trader vende um ativo que não possui (via empréstimo ou derivativo) esperando que o preço caia para recomprar mais barato.

```
Vende BTC a $67.000 (short) → Preço cai para $64.000 → Recompra → Lucro $3.000
```

**No spot**: difícil (requer empréstimo do ativo).
**Em futuros perpétuos Binance**: nativo, simples.

**Risco do short**: teoricamente ilimitado (o preço pode subir indefinidamente). Gerenciar com stop obrigatório.

### Slippage
**Definição**: Diferença entre o preço esperado de uma ordem e o preço em que ela efetivamente executa.

```python
preco_esperado = 67_000  # preço ao emitir a ordem
preco_executado = 67_080  # preço real de execução

slippage = (preco_executado - preco_esperado) / preco_esperado * 100
# slippage = 0.119%
```

**Causas:**
- Market orders em ativos com pouca profundidade
- Movimentos rápidos de preço entre emissão e execução
- Latência alta entre sinal e ordem

**Impacto no backtest**: backtests que ignoram slippage superestimam a performance. Sempre adicionar estimativa de slippage:

```python
# Modelagem de slippage no backtest
slippage_estimado = 0.0005  # 0.05% por side

preco_compra_real = preco_sinal * (1 + slippage_estimado)
preco_venda_real = preco_sinal * (1 - slippage_estimado)
```

### Sortino Ratio
**Definição**: Variação do Sharpe Ratio que penaliza apenas a volatilidade negativa (downside), ignorando a volatilidade positiva (ganhos grandes são bem-vindos).

```
Sortino = (Retorno Médio - Taxa Livre de Risco) / Desvio Padrão dos Retornos NEGATIVOS
```

**Por que preferir o Sortino**: em trading, uma sequência de ganhos altos não é um problema. O investidor quer minimizar perdas, não variância total.

### Spread
Diferença entre preço de compra (ask) e preço de venda (bid) no order book.
Veja detalhes em `fundamentos-mercado.md`.

---

## T

### Tick
**Definição**: A menor variação de preço possível em um mercado. No B3:

| Instrumento | Tick |
|---|---|
| Mini-índice WIN | 5 pontos = R$1,00/contrato |
| Mini-dólar WDO | 0.5 pontos = R$5,00/contrato |
| Ações B3 | R$0,01 |

**Em crypto (Binance)**: depende do par. BTC/USDT: 0.01 USDT de precision.

---

## V

### Volatilidade
**Definição**: Medida do grau de variação do preço de um ativo em um período. Alta volatilidade = movimentos grandes; baixa volatilidade = movimentos pequenos.

**Medidas quantitativas:**
- **Desvio padrão dos retornos**: métrica clássica
- **ATR**: volatilidade absoluta em termos de preço
- **VIX** (para ações): índice de medo do mercado americano

**Para o projeto**: usar ATR como medida primária de volatilidade para dimensionar stops e posições.

---

## W

### Walk-Forward Validation (WFV)
**Definição**: Método de validação de estratégias que divide os dados em múltiplas janelas temporais sequenciais, otimizando em uma janela (in-sample) e testando na seguinte (out-of-sample), repetindo o processo ao longo do tempo.

```
Dados: Jan 2020 – Dez 2024

Walk-Forward com janela de 6 meses:
  Período 1: IN-SAMPLE Jan-Jun 2020 | OOS Jul-Dez 2020
  Período 2: IN-SAMPLE Jul-Dez 2020 | OOS Jan-Jun 2021
  Período 3: IN-SAMPLE Jan-Jun 2021 | OOS Jul-Dez 2021
  ...
  Performance Final = Média das performances OOS de todos os períodos
```

**Por que é superior ao backtest simples**: a estratégia deve provar sua eficiência repetidamente em dados nunca vistos, mimicando condições reais de operação.

**Relevância para o projeto**: Na F3, toda estratégia de swing trade passará por walk-forward validation antes de ser aprovada para paper trading.

### Win Rate
**Definição**: Percentual de trades com lucro sobre o total de trades.

```
Win Rate = Número de trades lucrativos / Total de trades × 100

Exemplo: 60 ganhos em 100 trades = 60% win rate
```

**Atenção**: win rate alto NÃO garante estratégia lucrativa. Um sistema com 30% de win rate mas RR 4:1 pode ser muito mais lucrativo que um com 70% de win rate e RR 0.5:1.

```python
# Cálculo de expectância matemática por trade
win_rate = 0.40       # 40% de vitórias
avg_win = 200         # ganho médio em USDT
avg_loss = 100        # perda média em USDT
taxa = 5              # custo por trade (ida + volta)

expectancia = (win_rate * avg_win) - ((1 - win_rate) * avg_loss) - taxa
# expectancia = (0.4 × 200) - (0.6 × 100) - 5 = 80 - 60 - 5 = $15 por trade
```

---

## Tabela Resumo — Métricas de Performance

| Métrica | Fórmula Simplificada | Meta Safe Trading |
|---|---|---|
| **Sharpe Ratio** | retorno / volatilidade | > 1.0 |
| **Sortino Ratio** | retorno / volatilidade negativa | > 1.5 |
| **Max Drawdown** | maior queda pico-a-vale | < 20% |
| **Win Rate** | % trades lucrativos | > 40% (com RR ≥ 2:1) |
| **Profit Factor** | ganhos brutos / perdas brutas | > 1.5 |
| **Risk/Reward** | take profit / stop loss | ≥ 2:1 |
| **Expectância** | (WR × avg_win) - (LR × avg_loss) | > $0 após taxas |

---

## Referências

- [Backtesting AI Crypto — Blockchain Council](https://www.blockchain-council.org/cryptocurrency/backtesting-ai-crypto-trading-strategies-avoiding-overfitting-lookahead-bias-data-leakage/)
- [Walk-Forward Analysis vs Backtesting — Surmount](https://surmount.ai/blogs/walk-forward-analysis-vs-backtesting-pros-cons-best-practices)
- [Trading Strategy Validation — PickMyTrade](https://blog.pickmytrade.trade/trading-strategy-validation-backtest-overfitting/)
- [Interpretable Walk-Forward Framework — ArXiv](https://arxiv.org/html/2512.12924v1)
- [Quantitative Trading Strategies — NYU Stern](https://www.stern.nyu.edu/sites/default/files/2025-05/Glucksman_Lahanis.pdf)
