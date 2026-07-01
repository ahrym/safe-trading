# Indicadores Técnicos — Safe Trading

> Documento técnico de referência para o projeto Safe Trading. Fase 1 — Fundamentação.
> Produzido pelo sub-agente Pesquisador. Data: 2026-06-26.
> Para cada indicador: fórmula, interpretação, parâmetros padrão e regras de bot em pseudocódigo.

---

## 1. SMA — Simple Moving Average (Média Móvel Simples)

### Fórmula

```
SMA(n) = (P1 + P2 + ... + Pn) / n

onde P = preço de fechamento, n = número de períodos
```

### Interpretação prática

A SMA suaviza o ruído do preço e revela a tendência subjacente. Cada candle tem o mesmo peso.

| Situação | Interpretação |
|---|---|
| Preço > SMA | Tendência de alta; viés comprador |
| Preço < SMA | Tendência de baixa; viés vendedor |
| SMA curta cruza acima da SMA longa | Golden Cross → sinal de compra |
| SMA curta cruza abaixo da SMA longa | Death Cross → sinal de venda |

**Parâmetros padrão:**
- SMA(20): tendência de curto prazo
- SMA(50): tendência de médio prazo
- SMA(200): tendência de longo prazo (referência institucional)

**Limitação**: a SMA é um indicador de atraso (lagging). Em mercados laterais, gera muitos falsos sinais (whipsaws).

### Regra de bot — Crossover SMA

```python
# SE SMA curta cruza acima da SMA longa E preço está em tendência de alta:
SE SMA(20) cruza_acima SMA(50) E preço > SMA(200):
    COMPRAR com stop abaixo da mínima dos últimos 5 candles
    take_profit = entrada + 2 * ATR(14)

# SE SMA curta cruza abaixo da SMA longa:
SE SMA(20) cruza_abaixo SMA(50):
    FECHAR posição long
    # Ou iniciar short se futuros habilitados
```

---

## 2. EMA — Exponential Moving Average (Média Móvel Exponencial)

### Fórmula

```
Multiplicador = 2 / (n + 1)
EMA(hoje) = Preço(hoje) × Multiplicador + EMA(ontem) × (1 - Multiplicador)

Exemplo para EMA(21):
Multiplicador = 2 / (21 + 1) = 0.0909
→ preço de hoje tem peso de 9.09%
→ EMA de ontem tem peso de 90.91%
```

### Diferença EMA vs. SMA

| Característica | SMA | EMA |
|---|---|---|
| Peso dos candles | Igual para todos | Mais peso para os recentes |
| Velocidade de reação | Lenta | Rápida |
| Falsos sinais | Mais | Menos em tendência |
| Aderência ao preço | Mais defasada | Mais próxima |

**A EMA é preferida em trading algorítmico por reagir mais rápido a mudanças de tendência.**

**Parâmetros padrão para swing trade:**
- EMA(8): sinalização rápida
- EMA(21): tendência de curto prazo (muito usada em crypto)
- EMA(55): tendência de médio prazo
- EMA(200): tendência macro (nível institucional)

### Regra de bot — EMA Crossover + Filtro de Tendência

```python
# Entrada: EMA rápida cruza EMA lenta, com confirmação de tendência macro
SE EMA(8) cruza_acima EMA(21) E preço > EMA(200):
    COMPRAR com limit order no fechamento do candle de sinal
    stop_loss = mínima dos últimos 3 candles
    take_profit = entrada + (entrada - stop_loss) * 2  # RR de 2:1

# Saída: EMA rápida cruza abaixo da EMA lenta
SE EMA(8) cruza_abaixo EMA(21):
    ENCERRAR posição long

# Filtro adicional: não entrar se EMA(21) está apontando para baixo
SE inclinacao(EMA(21)) < 0:
    IGNORAR sinal de compra
```

### Implementação Python (pandas-ta)

```python
import pandas_ta as ta

df['ema8'] = ta.ema(df['close'], length=8)
df['ema21'] = ta.ema(df['close'], length=21)
df['ema200'] = ta.ema(df['close'], length=200)

# Detectar crossover
df['cross_up'] = (df['ema8'] > df['ema21']) & (df['ema8'].shift(1) < df['ema21'].shift(1))
df['cross_down'] = (df['ema8'] < df['ema21']) & (df['ema8'].shift(1) > df['ema21'].shift(1))
```

---

## 3. RSI — Relative Strength Index

### Fórmula simplificada

```
RS = Média dos ganhos (n períodos) / Média das perdas (n períodos)
RSI = 100 - (100 / (1 + RS))

Onde ganhos = (close - close_anterior) quando positivo, 0 caso contrário
      perdas = (close_anterior - close) quando negativo, 0 caso contrário
```

### Interpretação prática

**Parâmetro padrão: RSI(14)**

| Nível RSI | Zona | Interpretação |
|---|---|---|
| > 70 | Sobrecomprado | Potencial reversão de alta; momento de reduzir compras |
| 50–70 | Força | Tendência de alta confirmada; manter posições |
| 50 | Linha do meio | Transição — cruzamento indica mudança de momentum |
| 30–50 | Fraqueza | Tendência de baixa; cautela |
| < 30 | Sobrevendido | Potencial reversão de baixa; possível zona de compra |

**Importante**: em mercados em forte tendência, o RSI pode permanecer em sobrecomprado/sobrevendido por longos períodos sem reverter. Usar como filtro, não como único sinal.

### Divergências — o sinal mais poderoso do RSI

```
Divergência Altista (Bullish):
  Preço: faz mínima mais baixa → nova mínima MENOR
  RSI:   faz mínima mais alta → RSI NÃO confirma a nova mínima
  Resultado: pressão de venda fraca; reversão provável

Divergência Baixista (Bearish):
  Preço: faz máxima mais alta → nova máxima MAIOR
  RSI:   faz máxima mais baixa → RSI NÃO confirma a nova máxima
  Resultado: compra fraca; reversão provável
```

### Regras de bot com RSI

```python
# Regra 1: RSI sobrevendido com confirmação de tendência de alta
SE RSI(14) < 30 E preço > EMA(21) E EMA(21) inclinação > 0:
    COMPRAR com limit order
    stop_loss = mínima dos últimos 3 candles
    take_profit = resistência mais próxima ou RSI > 65

# Regra 2: Divergência altista
SE preço faz_nova_minima E RSI(14) NÃO faz_nova_minima E RSI(14) < 40:
    COMPRAR na confirmação (candle de alta após a mínima)
    stop_loss = mínima do padrão de divergência

# Regra 3: Saída por sobrecompra
SE RSI(14) > 70 E posição_aberta:
    CONSIDERAR reduzir posição ou mover stop para breakeven

# Filtro de tendência com RSI(14):
# Em tendência de alta, RSI entre 40-80 é zona saudável
# Em tendência de baixa, RSI entre 20-60 é zona saudável
```

### Implementação Python

```python
import pandas_ta as ta

df['rsi'] = ta.rsi(df['close'], length=14)

# Detectar divergência bullish (simplificado)
def detectar_divergencia_bullish(df, janela=10):
    price_min_anterior = df['low'].rolling(janela).min().shift(1)
    rsi_min_anterior = df['rsi'].rolling(janela).min().shift(1)
    
    divergencia = (
        (df['low'] < price_min_anterior) &      # preço faz nova mínima
        (df['rsi'] > rsi_min_anterior) &         # RSI NÃO confirma
        (df['rsi'] < 40)                          # em zona de sobrevenda relativa
    )
    return divergencia
```

---

## 4. MACD — Moving Average Convergence Divergence

### Fórmula

```
MACD Line  = EMA(12) - EMA(26)
Signal Line = EMA(9) da MACD Line
Histograma  = MACD Line - Signal Line

Parâmetros padrão: (12, 26, 9)
```

### Componentes e interpretação

| Componente | O que mede | Sinal |
|---|---|---|
| **MACD Line** | Diferença entre EMAs → momentum | Acima de zero = momentum positivo |
| **Signal Line** | Suavização da MACD | Cruzamentos com MACD = entradas/saídas |
| **Histograma** | Distância entre MACD e Signal | Barras crescendo = momentum acelerando |

**Leitura dos cruzamentos:**

| Cruzamento | Sinal |
|---|---|
| MACD cruza acima do Signal | Compra (bullish crossover) |
| MACD cruza abaixo do Signal | Venda (bearish crossover) |
| MACD cruza acima de zero | Tendência de alta confirmada |
| MACD cruza abaixo de zero | Tendência de baixa confirmada |
| Histograma diminui após pico | Momentum enfraquecendo |

**Parâmetros alternativos para swing trade em crypto:**
- (5, 13, 8): mais sensível, menos atraso — útil no 4h
- (12, 26, 9): padrão, melhor no 1D

### Regras de bot com MACD

```python
# Regra 1: Cruzamento clássico com confirmação de zona
SE MACD(12,26,9).line cruza_acima MACD(12,26,9).signal
   E MACD(12,26,9).line > 0
   E RSI(14) > 45:
    COMPRAR
    stop_loss = mínima do candle de sinal
    take_profit = stop × 2.0 (RR 2:1)

# Regra 2: Histograma crescendo do lado positivo
SE histograma > 0 E histograma > histograma_anterior E histograma_anterior > histograma_2anterior:
    SINAL DE ACELERAÇÃO DE ALTA → confirmar com preço acima de suporte

# Regra 3: Divergência baixista
SE preço faz_nova_maxima E MACD NÃO faz_nova_maxima:
    SINAL DE ALERTA → preparar saída de posição long
```

### Implementação Python

```python
import pandas_ta as ta

macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
df['macd_line'] = macd['MACD_12_26_9']
df['macd_signal'] = macd['MACDs_12_26_9']
df['macd_hist'] = macd['MACDh_12_26_9']

# Cruzamento
df['macd_cross_up'] = (
    (df['macd_line'] > df['macd_signal']) & 
    (df['macd_line'].shift(1) <= df['macd_signal'].shift(1))
)
```

---

## 5. Bollinger Bands

### Fórmula

```
Middle Band = SMA(20)
Upper Band  = SMA(20) + (2 × Desvio Padrão de 20 períodos)
Lower Band  = SMA(20) - (2 × Desvio Padrão de 20 períodos)

Parâmetros padrão: (20, 2)
```

### Interpretação prática

As Bollinger Bands medem **volatilidade** e identificam extremos de preço relativos à média.

| Situação | Interpretação |
|---|---|
| Preço toca a banda superior | Sobrecomprado relativo (no contexto atual de volatilidade) |
| Preço toca a banda inferior | Sobrevendido relativo |
| **Squeeze** (bandas muito próximas) | Volatilidade comprimida → explosão iminente de movimento |
| **Breakout após squeeze** | Início de nova tendência; entrada de alta probabilidade |
| Preço "passeia" pela banda superior | Tendência de alta forte (não reverter neste caso) |
| %B próximo a 0 | Preço na banda inferior |
| %B próximo a 1 | Preço na banda superior |

### Bollinger Bandwidth — métrica de squeeze

```
Bandwidth = (Upper Band - Lower Band) / Middle Band × 100

Squeeze = Bandwidth está no menor valor dos últimos N períodos
→ Breakout = Bandwidth começa a expandir após squeeze
```

### Regras de bot com Bollinger Bands

```python
# Regra 1: Mean Reversion (em mercados laterais)
SE preço toca/cruza abaixo lower_band E RSI(14) < 35 E preço_anterior > lower_band:
    COMPRAR (entrada contra-tendência)
    stop_loss = lower_band - (0.5 × ATR(14))
    take_profit = middle_band (SMA 20)

# Regra 2: Breakout após squeeze (em tendências)
SE bandwidth < percentil_20(bandwidth, 50) E  # squeeze detectado
   preço cruza_acima upper_band E
   volume > volume_media × 1.5:              # volume confirma
    COMPRAR (breakout)
    stop_loss = middle_band
    take_profit = upper_band + (upper_band - middle_band)  # projeção simétrica

# Regra 3: Não operar mean reversion quando bandas estão expandindo
# (indica tendência forte — preço pode "caminhar" na banda)
SE bandwidth > percentil_80(bandwidth, 50):
    PREFERIR estratégia de tendência, não reversão
```

### Implementação Python

```python
import pandas_ta as ta

bb = ta.bbands(df['close'], length=20, std=2)
df['bb_upper'] = bb['BBU_20_2.0']
df['bb_middle'] = bb['BBM_20_2.0']
df['bb_lower'] = bb['BBL_20_2.0']
df['bb_bandwidth'] = bb['BBB_20_2.0']
df['bb_percent'] = bb['BBP_20_2.0']  # %B

# Detectar squeeze
df['bb_squeeze'] = df['bb_bandwidth'] == df['bb_bandwidth'].rolling(50).min()
```

---

## 6. ATR — Average True Range

### Fórmula

```
True Range = max(
    high - low,                    # variação do candle
    abs(high - close_anterior),    # gap de alta
    abs(low - close_anterior)      # gap de baixa
)

ATR(n) = Média Exponencial do True Range dos últimos n períodos

Parâmetro padrão: ATR(14)
```

### Por que o ATR é indispensável para bots

O ATR mede a **volatilidade absoluta** do ativo em termos de preço. Ele responde: "quanto esse ativo tipicamente se move em um período?"

**Aplicações críticas:**

| Aplicação | Fórmula | Benefício |
|---|---|---|
| **Stop loss dinâmico** | `stop = entrada - N × ATR(14)` | Stop adaptado à volatilidade atual |
| **Tamanho de posição** | `qtd = risco_em_R$ / (N × ATR)` | Position sizing correto |
| **Take profit** | `tp = entrada + N × ATR(14)` | TP realista baseado em alcance típico |
| **Filtro de volatilidade** | Evitar entrada se ATR > 3× média | Não entrar em mercados caóticos |

### Stop Loss dinâmico com ATR — o padrão do mercado

```python
# Método padrão para stop loss baseado em ATR
# Muito mais robusto que stops em % fixo

atr = ta.atr(df['high'], df['low'], df['close'], length=14)

# Stop conservador (swing trade): 2× ATR
stop_loss_swing = entrada - (2.0 * atr)

# Stop agressivo (day trade): 1× ATR
stop_loss_day = entrada - (1.0 * atr)

# Take profit típico: 2× o risco (RR 2:1 com ATR)
take_profit = entrada + (2.0 * (entrada - stop_loss_swing))

# Position sizing: arriscar 1% do capital por trade
capital = 10_000  # USDT
risco_por_trade = capital * 0.01  # $100
distancia_stop = entrada - stop_loss_swing
quantidade = risco_por_trade / distancia_stop  # BTC a comprar
```

### Regras de bot com ATR

```python
# Regra 1: Stop loss padrão para swing trade
SE entrada = 67.000 E ATR(14) = 800:
    stop_loss = 67.000 - (2 × 800) = 65.400
    take_profit = 67.000 + (4 × 800) = 70.200  # RR 2:1

# Regra 2: Filtro de entrada por volatilidade
atr_media = ATR(14).rolling(50).mean()
SE ATR(14) > atr_media × 2.5:
    NÃO ENTRAR (mercado muito volátil, stop seria muito largo)

# Regra 3: Trailing stop dinâmico com ATR
trailing_stop = max_preco_desde_entrada - (2.5 × ATR(14))
SE preço <= trailing_stop:
    FECHAR posição
```

---

## 7. VWAP — Volume Weighted Average Price

### Fórmula

```
VWAP = Σ(Preço_típico × Volume) / Σ(Volume)

Preço_típico = (High + Low + Close) / 3

O VWAP é calculado de forma acumulativa durante a sessão
e reinicia a cada novo dia de negociação.
```

### Interpretação prática

O VWAP representa o **preço médio pago por todos os participantes** durante a sessão, ponderado pelo volume. É a referência institucional mais importante.

| Situação | Interpretação |
|---|---|
| Preço > VWAP | Compras dominantes; mercado "caro" para quem entra agora |
| Preço < VWAP | Vendas dominantes; mercado "barato" vs. média do dia |
| Preço retorna ao VWAP após afastamento | Oportunidade de entrada (pullback para a média) |
| VWAP inclinado para cima | Sessão em tendência de alta |
| Múltiplos toques no VWAP como suporte | VWAP funcionando como suporte dinâmico |

**Limitação**: o VWAP é mais relevante em timeframes intraday (1m a 1h). Em swing trade (1D), perde relevância pois reinicia diariamente. Em crypto, pode ser calculado sobre janelas de tempo personalizadas (ex: VWAP ancorado).

### Uso em swing trade crypto: VWAP ancorado

```python
def calcular_vwap_ancorado(df, data_ancora):
    """
    VWAP ancorado a um ponto específico (ex: fundo de uma correção)
    Útil em swing trade para identificar zonas de equilíbrio
    """
    df_filtrado = df[df.index >= data_ancora].copy()
    df_filtrado['tp'] = (df_filtrado['high'] + df_filtrado['low'] + df_filtrado['close']) / 3
    df_filtrado['tp_vol'] = df_filtrado['tp'] * df_filtrado['volume']
    df_filtrado['vwap'] = df_filtrado['tp_vol'].cumsum() / df_filtrado['volume'].cumsum()
    return df_filtrado['vwap']
```

### Regras de bot com VWAP

```python
# Regra 1: Entrada no pullback ao VWAP (tendência de alta)
SE preço > VWAP (sessão em alta)
   E preço recua para toca VWAP
   E RSI(14) > 45 (não sobrevendido):
    COMPRAR no toque do VWAP
    stop_loss = VWAP - ATR(14)
    take_profit = máxima recente da sessão

# Regra 2: VWAP como filtro de viés
SE preço > VWAP:
    APENAS sinais de COMPRA são válidos
SE preço < VWAP:
    APENAS sinais de VENDA são válidos (em futuros/short)

# Regra 3: Breakout do VWAP com volume
SE preço cruza_acima VWAP E volume > volume_media × 1.5:
    COMPRAR (breakout de equilíbrio)
```

### Implementação Python

```python
import pandas_ta as ta

# VWAP padrão diário
df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])

# Alternativa manual para crypto (sem reinício diário)
df['tp'] = (df['high'] + df['low'] + df['close']) / 3
df['vwap_manual'] = (df['tp'] * df['volume']).cumsum() / df['volume'].cumsum()
```

---

## 8. Estratégia Combinada — Sistema Multi-Indicador

O maior erro de iniciantes é usar indicadores isolados. A combinação certa aumenta a taxa de acerto e reduz falsos sinais.

### Framework de entrada para o Safe Trading (Swing Trade)

```python
def sinal_compra(df, i):
    """
    Sistema de pontuação: cada condição adiciona 1 ponto
    Entrar apenas se score >= 4 de 6
    """
    score = 0
    
    # 1. Tendência macro favorável
    if df['close'][i] > df['ema200'][i]:
        score += 1
    
    # 2. EMA crossover de alta
    if df['cross_up_ema'][i]:
        score += 1
    
    # 3. RSI em zona saudável (não sobrecomprado)
    if 35 < df['rsi'][i] < 65:
        score += 1
    
    # 4. MACD positivo e crescendo
    if df['macd_hist'][i] > 0 and df['macd_hist'][i] > df['macd_hist'][i-1]:
        score += 1
    
    # 5. Preço próximo da banda inferior ou médio das Bollinger
    if df['bb_percent'][i] < 0.4:  # preço no terço inferior do canal
        score += 1
    
    # 6. Volume confirmando
    if df['volume'][i] > df['volume'].rolling(20).mean()[i] * 1.2:
        score += 1
    
    return score >= 4

def calcular_stop_loss(df, i):
    return df['close'][i] - (2.0 * df['atr'][i])

def calcular_take_profit(df, i, stop):
    risco = df['close'][i] - stop
    return df['close'][i] + (risco * 2.0)  # RR 2:1
```

---

## Referências

- [RSI, MACD, Bollinger Bands — Investopedia](https://www.investopedia.com)
- [VWAP Indicator Guide — ForexTester](https://forextester.com/blog/vwap/)
- [Bollinger Bands & MACD Entry Rules — LuxAlgo](https://www.luxalgo.com/blog/bollinger-bands-and-macd-entry-rules-explained/)
- [Swing Trading Technical Indicators — Altrady](https://www.altrady.com/blog/swing-trading/technical-indicators-crypto-trading-setups)
- [Algorithmic Trading Signals — TradersPost](https://blog.traderspost.io/article/technical-indicators-algo-trading)
- [pandas-ta documentation](https://github.com/twopirllc/pandas-ta)
