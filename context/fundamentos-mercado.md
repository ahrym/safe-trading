# Fundamentos de Mercado — Safe Trading

> Documento técnico de referência para o projeto Safe Trading. Fase 1 — Fundamentação.
> Produzido pelo sub-agente Pesquisador. Data: 2026-06-26.

---

## 1. Order Book: A Estrutura Central do Mercado

### O que é

O order book (livro de ordens) é o registro em tempo real de todas as ordens de compra e venda pendentes para um ativo em uma exchange. É a estrutura que determina o preço de mercado a cada instante — não existe "preço de mercado" sem o book.

### Componentes

| Componente | Definição |
|---|---|
| **Bid (oferta de compra)** | O maior preço que um comprador está disposto a pagar. Lado esquerdo/verde do book. |
| **Ask (oferta de venda)** | O menor preço que um vendedor aceita receber. Lado direito/vermelho do book. |
| **Spread** | Diferença entre best ask e best bid: `spread = ask - bid`. Representa o custo implícito de execução imediata. |
| **Best bid / Best ask** | As ordens mais favoráveis de cada lado — as que serão executadas primeiro pelo matching engine. |
| **Profundidade de mercado** | Quantidade acumulada de ordens em cada nível de preço. Indica o "peso" de suporte ou resistência. |
| **Mid price** | `(best_bid + best_ask) / 2` — preço de referência sem viés de compra ou venda. |

### Exemplo prático (BTC/USDT)

```
   ASKS (vendedores)
   67.260 — 0.3 BTC
   67.250 — 0.5 BTC
   67.240 — 1.2 BTC   ← Best ask
   ─────────────────── spread = $10
   67.230 — 0.8 BTC   ← Best bid
   67.220 — 2.1 BTC
   67.200 — 5.0 BTC
   BIDS (compradores)

   Mid price = (67.240 + 67.230) / 2 = 67.235
   Spread = $10 / 67.235 = 0.015%  → excelente liquidez
```

### Relevância para o Safe Trading

- O bot deve consultar o order book antes de executar ordens grandes para estimar slippage antecipado
- Spreads apertados indicam boa liquidez (BTC, ETH são ideais para começar)
- Um spread grande (ex: altcoins ilíquidas) penaliza severamente o resultado real vs. backtest
- Na Binance: endpoint `GET /api/v3/depth?symbol=BTCUSDT&limit=20` retorna o book em tempo real

---

## 2. Tipos de Ordem

### Visão geral comparativa

| Tipo | Execução | Preço garantido? | Execução garantida? | Custo (maker/taker) | Uso primário em bots |
|---|---|---|---|---|---|
| **Market** | Imediata | Não (slippage) | Sim | Taker (mais caro) | Saída de emergência, stop loss |
| **Limit** | Quando preço atinge o valor | Sim | Não | Maker (mais barato) | Entrada planejada, take profit |
| **Stop-Market** | Market order quando trigger é atingido | Não | Sim após trigger | Taker | Stop loss (prioridade: sair) |
| **Stop-Limit** | Limit order quando trigger é atingido | Sim | Não | Maker | Stop loss com controle de preço |
| **Trailing Stop** | Stop que segue o preço em % ou valor | Não | Sim após trigger | Taker | Capturar extensão de tendência |

### Market Order

Executa contra as melhores ordens disponíveis no book imediatamente, consumindo múltiplos níveis se necessário.

**Risco principal**: slippage em ativos ilíquidos — a ordem come vários níveis do book, degradando o preço.

```python
# Estimativa de slippage antes de executar market order
def estimar_slippage(order_book_asks, volume_a_comprar):
    custo_total = 0
    volume_restante = volume_a_comprar
    for preco, qtd in order_book_asks:
        executado = min(qtd, volume_restante)
        custo_total += executado * preco
        volume_restante -= executado
        if volume_restante <= 0:
            break
    preco_medio = custo_total / volume_a_comprar
    return preco_medio

# Quando usar: saída urgente, stop loss, ativos de alta liquidez (BTC/ETH)
```

### Limit Order

Fica no order book até ser preenchida ou cancelada. Adiciona liquidez ao mercado.

- **Vantagem**: paga taxa maker (menor), preço garantido
- **Risco**: pode não ser preenchida se o preço não chegar ao nível

```python
# Estratégia de entrada com limit order
# Posta a ordem 0.1% abaixo do preço atual para garantir preenchimento como maker
entry_price = current_price * 0.999
# Define timeout: se não preenchida em N minutos, cancela e reavalia
```

### Stop-Market

Coloca um trigger de preço → quando atingido, executa market order.

- **Risco em crypto**: gaps de preço em mercados voláteis podem causar execução muito abaixo do trigger
- **Quando usar**: stop loss onde a prioridade absoluta é SAIR, não o preço de saída

### Stop-Limit

Trigger de preço → coloca limit order no preço especificado.

- **Risco**: se o preço "pular" o limite na queda, a ordem não preenche e o trader fica preso
- **Prática**: definir o stop limit 0.5%-1% abaixo do trigger para reduzir esse risco

### Trailing Stop

Stop que se ajusta automaticamente acompanhando o preço favorável.

```
BTC comprado a $60.000, trailing stop de 3%:
→ Stop inicial: $60.000 × 0.97 = $58.200
→ BTC sobe a $70.000 → stop ajusta: $70.000 × 0.97 = $67.900
→ BTC cai para $67.900 → VENDE (lucro de $7.900 por BTC)
```

**Quando usar**: tendências fortes onde não queremos fixar take profit prematuramente.

### Relevância para o Safe Trading

```
Estratégia padrão recomendada para swing trade (F2):
ENTRADA:  Limit order (maker, melhor preço)
STOP LOSS: Stop-Market (garantir a saída)
TAKE PROFIT: Limit order ou Trailing Stop
```

---

## 3. Candlesticks

### Anatomia de um candle

```
       │        ← Sombra superior: tentativa de alta rejeitada
    ╔══╧══╗
    ║     ║     ← CANDLE VERDE (alta): open < close
    ║     ║        Corpo = |close - open|
    ╚══╤══╝
       │        ← Sombra inferior: tentativa de queda rejeitada

OHLCV: Open=67.000 | High=67.800 | Low=66.800 | Close=67.500 | Volume=1.250 BTC
```

| Componente | Significado técnico |
|---|---|
| **Open** | Primeiro preço negociado no período |
| **High** | Máxima atingida — ponto de rejeição de alta |
| **Low** | Mínima atingida — ponto de rejeição de baixa |
| **Close** | Último preço do período — o mais importante para indicadores |
| **Corpo grande** | Força direcional dos participantes |
| **Sombras longas** | Rejeição de nível de preço; pressão no sentido oposto |
| **Doji** | Open ≈ Close; indecisão do mercado |

### Timeframes e aplicações

| Timeframe | Período | Ruído | Uso típico |
|---|---|---|---|
| 1m | 1 minuto | Muito alto | Scalping, execução fina de ordens |
| 5m | 5 minutos | Alto | Day trade, confirmação de entrada |
| 15m | 15 minutos | Médio | Day trade, contexto intraday |
| 1h | 1 hora | Baixo | Swing trade (sub-timeframe, timing) |
| 4h | 4 horas | Muito baixo | **Swing trade (timeframe principal)** |
| 1D | 1 dia | Mínimo | **Swing trade (tendência macro)** |
| 1W | 1 semana | Mínimo | Posição longa, macro view |

### Setup multi-timeframe recomendado para Safe Trading

```
1. Checar tendência no 1D:
   - Série de topos e fundos ascendentes → tendência de alta
   - Preço acima da EMA(21) no diário → bias comprador

2. Identificar setup no 4h:
   - Pullback para zona de suporte
   - Padrão de reversão (hammer, engolfo)
   - RSI em sobrevenda relativa (< 50 em alta)

3. Timing de entrada no 1h:
   - Confirmação de candle fechando acima da resistência local
   - Volume crescente na entrada
```

**Regra fundamental**: nunca operar contra a tendência do diário no swing trade.

### Padrões de candlestick em código

```python
import pandas as pd

def detectar_hammer(df):
    """Detecta padrão Hammer (reversão de alta)"""
    corpo = abs(df['close'] - df['open'])
    sombra_inf = df[['open', 'close']].min(axis=1) - df['low']
    sombra_sup = df['high'] - df[['open', 'close']].max(axis=1)
    
    hammer = (
        (sombra_inf >= 2 * corpo) &    # sombra inferior >= 2x o corpo
        (sombra_sup <= 0.3 * corpo) &  # sombra superior mínima
        (df['close'] > df['open'])     # candle de alta (corpo verde)
    )
    return hammer

def detectar_engolfo_alta(df):
    """Detecta Bullish Engulfing"""
    candle_prev_queda = df['close'].shift(1) < df['open'].shift(1)
    engolfo = (
        (df['open'] < df['close'].shift(1)) &  # abre abaixo do fechamento anterior
        (df['close'] > df['open'].shift(1)) &  # fecha acima da abertura anterior
        candle_prev_queda
    )
    return engolfo
```

---

## 4. Volume

### Princípios fundamentais

Volume é a quantidade de ativos trocados em um período. É o indicador mais fundamental e o único que não deriva de price action.

**Interpretação por cenário:**

| Direção do preço | Volume | Sinal | Ação sugerida |
|---|---|---|---|
| ↑ Sobe | Alto | Tendência de alta sólida | Seguir a tendência |
| ↑ Sobe | Baixo | Rally fraco, sem convicção | Cautela; possível reversão |
| ↓ Cai | Alto | Distribuição ou capitulação | Aguardar estabilização |
| ↓ Cai | Baixo | Correção saudável, pullback | Possível zona de compra em tendência de alta |

### Volume anômalo como sinal de trading

```python
def detectar_volume_anomalo(df, janela=20, multiplicador=2.0):
    """
    Retorna True quando volume atual é excepcional
    Parâmetros:
      janela: períodos para calcular a média
      multiplicador: quantas vezes acima da média define 'anômalo'
    """
    volume_media = df['volume'].rolling(janela).mean()
    return df['volume'] > (volume_media * multiplicador)

# Regra: breakout com volume anômalo tem alta probabilidade de continuar
# Breakout sem volume anômalo = provável false breakout
```

### On Balance Volume (OBV) — versão simplificada

```python
def calcular_obv(df):
    """OBV acumula volume positivo em altas e negativo em quedas"""
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

# Divergência: preço faz nova máxima mas OBV não → sinal de fraqueza
```

---

## 5. Liquidez

### Por que liquidez é crítica para bots

Um bot de trading não é um humano executando a preços de tabela. Ele interage com o order book real, e a liquidez determina o custo real de execução.

**Problemas causados por baixa liquidez:**

1. **Slippage**: execução a preço pior que o esperado
   - `slippage = (preco_executado - preco_esperado) / preco_esperado * 100`
   - Meta para o Safe Trading: slippage < 0.05% por trade

2. **Preenchimento parcial**: order size excede as ordens disponíveis no nível desejado

3. **Impacto de mercado**: o bot, ao executar, move o preço contra si mesmo

4. **Divergência backtest vs. live**: backtest assume execução no preço de fechamento; live sofre slippage real

### Métricas para avaliar liquidez antes de operar

```python
def avaliar_liquidez(order_book, volume_trade):
    """
    Retorna: slippage estimado, se ativo é adequado para operar
    """
    best_ask = order_book['asks'][0][0]
    best_bid = order_book['bids'][0][0]
    
    spread_pct = (best_ask - best_bid) / best_bid * 100
    
    # Simular execução de market order
    volume_disponivel_5_niveis = sum(qtd for _, qtd in order_book['asks'][:5])
    
    adequado = (
        spread_pct < 0.05 and          # spread menor que 0.05%
        volume_disponivel_5_niveis > volume_trade * 10  # profundidade suficiente
    )
    
    return {
        'spread_pct': spread_pct,
        'profundidade_5_niveis': volume_disponivel_5_niveis,
        'adequado_para_bot': adequado
    }
```

### Ativos recomendados por liquidez (Safe Trading)

| Ativo | Volume 24h (ref.) | Spread típico | Adequado para bot |
|---|---|---|---|
| BTC/USDT | > $15B | ~0.01% | Excelente |
| ETH/USDT | > $8B | ~0.01% | Excelente |
| BNB/USDT | > $500M | ~0.02% | Bom |
| Altcoins top 20 | > $100M | ~0.05-0.1% | Aceitável com cuidado |
| Altcoins < top 50 | < $50M | > 0.1% | Evitar |

---

## 6. Spot vs. Futuros vs. Opções

### Tabela comparativa completa

| Característica | **Spot** | **Futuros Perpétuos** | **Opções** |
|---|---|---|---|
| O que você possui | O ativo real | Contrato sobre o preço | Direito (não obrigação) |
| Alavancagem | Não (padrão) | 1x–125x na Binance | Via prêmio pago |
| Risco de liquidação | Não | Sim | Limitado ao prêmio |
| Taxa de financiamento | Não | A cada 8h (±) | Não |
| Short selling | Difícil | Nativo | Via puts |
| Complexidade de API | Baixa | Média | Alta |
| Adequado para iniciantes | **Sim** | Com disciplina de risk | Não inicialmente |
| Regulação no Brasil | Simples (tributação) | Complexa | Complexa |

### Taxa de Financiamento (Funding Rate) — conceito crítico para futuros

A funding rate é trocada entre longs e shorts a cada 8h para manter o preço do futuro perpetual ancorado ao spot.

- Funding rate **positivo**: longs pagam shorts → mercado otimista demais → sinal de topo potencial
- Funding rate **negativo**: shorts pagam longs → mercado pessimista → possível sinal de fundo

```python
# Usar funding rate como filtro de entrada em futuros
# Evitar entrar long quando funding rate > 0.1% (3x a taxa base)
# Sugere posicionamento excessivo na mesma direção
```

### Recomendação por fase do projeto Safe Trading

| Fase | Mercado | Instrumento | Justificativa |
|---|---|---|---|
| **F2** | Binance | Spot BTC/ETH | Sem liquidação, sem funding rate, simples para começar |
| **F3** | Binance | Futuros Perpétuos | Permite short, hedge, maior eficiência de capital |
| **F4** | B3 | Ações à vista | Regulação conhecida, dados via brapi.dev |
| **F5** | B3 | Mini-índice (WIN), Mini-dólar (WDO) | Alta liquidez, alavancagem nativa, Nelogica ProfitDLL |

---

## Referências Técnicas

- [Binance Order Types](https://www.binance.com/en/support/faq/order-types-on-binance)
- [Order Book Depth & Slippage — BitMart](https://bitmart.zendesk.com/hc/en-us/articles/360045109174)
- [Crypto Swing Trading Timeframes — Altrady](https://www.altrady.com/blog/swing-trading/best-timeframes-swing-trading)
- [Order Book Ultimate Guide — QuantStrategy.io](https://quantstrategy.io/blog/the-ultimate-guide-to-reading-the-order-book-understanding/)
- [Liquidity Crypto Metrics — SimpleSwap](https://simpleswap.io/blog/liquidity-crypto-metrics-reading-order-books-market-depth-and-volume)
