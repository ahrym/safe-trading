# Roadmap de Features para ML — Safe Trading F4
## XGBoost para Filtro de Sinais EMA 8/21 + RSI no BTC/USDT 4h

**Data:** 01/07/2026  
**Fase:** F4 — Machine Learning (pesquisa inicial)  
**Problema a resolver:** 46 de 77 trades (59.7%) da estratégia EMA 8/21 encerraram no stop loss — o modelo deve aprender a filtrar os sinais falsos antes da entrada.

---

## 1. LABEL A PREVER (Variável Alvo)

**Definição clara:** classificação binária por trade.

```
label = 1  → trade atingiu o Take Profit antes do Stop Loss
label = 0  → trade atingiu o Stop Loss antes do Take Profit
```

**Como calcular (sem look-ahead bias):**

```python
def calcular_label(df, idx_entrada, stop_loss, take_profit, max_candles=30):
    """
    Olha PARA FRENTE a partir do candle de entrada (isso é válido porque
    a label é calculada APÓS o trade fechar — nunca é usada como feature).
    """
    for i in range(1, max_candles + 1):
        if idx_entrada + i >= len(df):
            return 0  # trade expirou sem atingir alvo
        low = df.iloc[idx_entrada + i]['low']
        high = df.iloc[idx_entrada + i]['high']
        if low <= stop_loss:
            return 0  # stop loss atingido primeiro
        if high >= take_profit:
            return 1  # take profit atingido primeiro
    return 0  # expirou
```

**Por que esta label:**
- Diretamente alinhada com o objetivo operacional (RR 2:1)
- Evita prever "sobe ou desce" (pergunta mais difícil e menos útil)
- Permite calcular precision/recall para a classe 1 ("compra válida")

**Alternativa para explorar na fase 2:**  
Label contínua = retorno percentual no fechamento após N candles (problema de regressão, mais complexo, deixar para depois).

---

## 2. FEATURES RECOMENDADAS

### 2.1 Features de Momentum

| Feature | Fórmula / Parâmetro | Justificativa |
|---|---|---|
| `rsi_14` | RSI(14), valor bruto | Indicador mais citado em estudos XGBoost/crypto (top 2 em feature importance) |
| `rsi_14_norm` | RSI(14) normalizado: `(rsi - 50) / 50` → range [-1, 1] | Facilita aprendizado do XGBoost |
| `rsi_slope` | `rsi_14.diff(3).shift(1)` | Direção do RSI nos últimos 3 candles — momentum do momentum |
| `rsi_divergence` | `(close.diff(5) > 0).astype(int) - (rsi_14.diff(5) > 0).astype(int)` | Divergência preço vs RSI (sinal clássico de reversão) |
| `macd_hist` | MACD(12,26,9) histograma | Diferença entre MACD e sinal — indica aceleração/desaceleração |
| `macd_hist_norm` | `macd_hist / atr_14.shift(1)` | Normalizado por ATR para comparabilidade entre períodos |
| `stoch_k` | Stocástico %K(14,3) | Complementa RSI em identificar sobrecompra/sobrevenda |
| `stoch_d` | Stocástico %D (média de %K) | Linha de sinal do estocástico |
| `mom_5` | `(close / close.shift(5) - 1).shift(1)` | Retorno dos últimos 5 candles (20h) |
| `mom_10` | `(close / close.shift(10) - 1).shift(1)` | Retorno dos últimos 10 candles (40h) |
| `mom_20` | `(close / close.shift(20) - 1).shift(1)` | Retorno dos últimos 20 candles (80h) |

**Nota `.shift(1)` obrigatório:** todas as features calculadas com dados do candle atual devem usar `.shift(1)` para garantir que o modelo só vê dados disponíveis NO MOMENTO da entrada — o candle atual ainda não fechou quando o sinal é gerado.

---

### 2.2 Features de Tendência

| Feature | Fórmula / Parâmetro | Justificativa |
|---|---|---|
| `ema8_slope` | `(ema_8 / ema_8.shift(3) - 1).shift(1)` | Inclinação da EMA rápida — quão forte é a tendência de curto prazo |
| `ema21_slope` | `(ema_21 / ema_21.shift(5) - 1).shift(1)` | Inclinação da EMA média |
| `ema_spread_8_21` | `((ema_8 - ema_21) / ema_21).shift(1)` | Separação entre as EMAs como % — quanto maior, mais forte o cruzamento |
| `ema_spread_21_50` | `((ema_21 - ema_50) / ema_50).shift(1)` | Alinhamento da tendência de médio prazo |
| `price_vs_ema50` | `((close - ema_50) / ema_50).shift(1)` | Preço acima/abaixo da EMA macro (filtro de tendência) |
| `adx_14` | ADX(14) | Força da tendência (não direção). ADX > 25 = tendência forte |
| `di_plus` | DI+(14) | Pressão compradora |
| `di_minus` | DI-(14) | Pressão vendedora |
| `di_spread` | `(di_plus - di_minus).shift(1)` | Saldo de pressão — positivo = bulls dominando |
| `ema200_regime` | `(close > ema_200).astype(int).shift(1)` | Feature binária: preço acima da EMA 200 = bull macro |

---

### 2.3 Features de Volatilidade

| Feature | Fórmula / Parâmetro | Justificativa |
|---|---|---|
| `atr_14_norm` | `(atr_14 / close).shift(1)` | ATR normalizado pelo preço — volatilidade relativa |
| `atr_ratio` | `(atr_14 / atr_14.rolling(50).mean()).shift(1)` | ATR atual vs média histórica — expansão ou contração de volatilidade |
| `bb_width` | `((bb_upper - bb_lower) / bb_middle).shift(1)` | Largura das Bandas de Bollinger — squeeze ou expansão |
| `bb_position` | `((close - bb_lower) / (bb_upper - bb_lower)).shift(1)` | Posição relativa dentro das Bandas (0=fundo, 1=topo) |
| `hv_10` | Volatilidade histórica 10 candles: `close.pct_change().rolling(10).std().shift(1)` | Volatilidade realizada de curto prazo |
| `hv_50` | Volatilidade histórica 50 candles: `close.pct_change().rolling(50).std().shift(1)` | Volatilidade realizada de médio prazo |
| `hv_ratio` | `(hv_10 / hv_50).shift(1)` | Razão: > 1 = vol crescente (momentum de volatilidade) |
| `candle_body_ratio` | `(abs(close - open) / (high - low)).shift(1)` | Tamanho do corpo vs sombras — candle com corpo grande = convicção |
| `upper_shadow` | `((high - close.clip(lower=open)) / atr_14).shift(1)` | Sombra superior normalizada — pressão vendedora no candle |

---

### 2.4 Features de Volume

| Feature | Fórmula / Parâmetro | Justificativa |
|---|---|---|
| `volume_ratio_20` | `(volume / volume.rolling(20).mean()).shift(1)` | Volume atual vs média 20 candles — pico de volume é sinal de convicção |
| `volume_ratio_50` | `(volume / volume.rolling(50).mean()).shift(1)` | Volume vs média 50 candles — contexto mais amplo |
| `obv_slope` | `obv.diff(5).shift(1)` | Inclinação do On-Balance Volume — acumulação ou distribuição |
| `obv_norm` | `((obv - obv.rolling(50).min()) / (obv.rolling(50).max() - obv.rolling(50).min())).shift(1)` | OBV normalizado em janela de 50 candles |
| `vwap_spread` | `((close - vwap_diario) / close).shift(1)` | Preço vs VWAP — acima do VWAP = bulls pagando mais |
| `volume_price_trend` | `(close.pct_change() * volume).rolling(10).sum().shift(1)` | Tendência volume-preço — similar ao OBV mas ponderado por retorno |
| `up_volume_ratio` | Proporção dos últimos 10 candles onde `close > open` ponderada pelo volume | Volume em candles de alta vs baixa |

---

### 2.5 Features de Regime de Mercado

Estas features respondem à pergunta: "em que tipo de mercado estamos quando o sinal ocorre?"

| Feature | Fórmula / Parâmetro | Justificativa |
|---|---|---|
| `regime_ema` | Codificação ordinal: `ema8 > ema21 > ema50 > ema200` = 4, etc. | Quantas EMAs estão alinhadas em alta — proxy de força da tendência |
| `regime_adx` | `(adx_14 > 25).astype(int).shift(1)` | Binário: mercado em tendência (1) ou lateral (0) |
| `slope_50` | `(ema_50 / ema_50.shift(10) - 1).shift(1)` | Inclinação da EMA 50 — identifica bull/bear de médio prazo |
| `slope_200` | `(ema_200 / ema_200.shift(20) - 1).shift(1)` | Inclinação da EMA 200 — tendência macro |
| `drawdown_from_peak` | `(close / close.rolling(100).max() - 1).shift(1)` | Queda do pico recente — em drawdown profundo = bear market |
| `days_since_ath_ratio` | Normalização da distância do ATH histórico | Contexto de ciclo longo do BTC |

**Técnica avançada (opcional F4.2):** usar Hidden Markov Model (HMM) para classificar o regime em {bull, bear, lateral} de forma não supervisionada e incluir essa classificação como feature categórica.

---

### 2.6 Features de Contexto Temporal

Cripto opera 24/7 — hora e dia da semana têm impacto estatístico documentado.

| Feature | Fórmula | Justificativa |
|---|---|---|
| `hora_sin` | `sin(2π × hora_utc / 24)` | Codificação cíclica da hora — hora 23 próxima de hora 0 |
| `hora_cos` | `cos(2π × hora_utc / 24)` | Par necessário para codificação cíclica |
| `dia_semana_sin` | `sin(2π × dia_semana / 7)` | Codificação cíclica do dia (0=segunda, 6=domingo) |
| `dia_semana_cos` | `cos(2π × dia_semana / 7)` | Par necessário |
| `is_weekend` | `(dia_semana >= 5).astype(int)` | Final de semana tem padrão de volume diferente em cripto |
| `hora_abertura_ny` | `(hora_utc >= 13) & (hora_utc <= 21)` | Abertura de NY (13h-21h UTC) — maior liquidez |
| `hora_asiatica` | `(hora_utc >= 0) & (hora_utc <= 8)` | Sessão asiática — padrões diferentes |

**Por que codificação cíclica (sin/cos) e não label encoding:**  
O XGBoost trataria hora 23 como muito diferente de hora 0 se usasse valores inteiros brutos. A codificação cíclica preserva a continuidade temporal.

---

### 2.7 Features de Contexto do Sinal (específicas da estratégia EMA 8/21)

Estas features capturam a "qualidade" do próprio sinal de entrada.

| Feature | Fórmula | Justificativa |
|---|---|---|
| `candles_desde_cruzamento` | Quantos candles desde o cruzamento EMA 8/21 | Sinal muito atrasado pode ser falso |
| `rsi_no_cruzamento` | RSI(14) no candle exato do cruzamento | RSI no momento da geração do sinal |
| `volume_no_cruzamento` | `volume / volume.rolling(20).mean()` no cruzamento | Volume no momento do sinal |
| `atr_percentil` | Percentil do ATR atual vs últimos 100 candles | Volatilidade alta no momento = stop mais largo = mais risco |
| `spread_no_sinal` | `(ema_8 - ema_21) / ema_21` no candle de entrada | Separação das EMAs — cruzamento com gap grande = mais forte |

---

## 3. LABEL ENGINEERING — EVITAR LOOK-AHEAD BIAS

### Regra de Ouro

**A label (TP ou SL) é o único lugar onde é permitido olhar para frente.** Todas as features devem usar apenas dados do passado.

### Armadilhas Específicas deste Projeto

| Armadilha | Descrição | Correção |
|---|---|---|
| **Normalização com o futuro** | Calcular `(close - rolling_mean) / rolling_std` onde o rolling inclui dados futuros | Usar `.shift(1)` antes de qualquer rolling; ou calcular rolling só com dados até t-1 |
| **RSI calculado sobre candle atual** | RSI usa o fechamento do candle atual, que ainda não existe no momento do sinal | Sempre `.shift(1)` no RSI antes de usar como feature |
| **ATR com high/low do candle atual** | O candle de entrada ainda não fechou quando o sinal é gerado | Features do candle atual só usam open; high/low/close requerem `.shift(1)` |
| **Normalização por máximo histórico** | `close / close.rolling(N).max()` inclui o próprio close atual | `.shift(1)` no rolling ou excluir o ponto atual: `.rolling(N, min_periods=1).max().shift(1)` |
| **VWAP intradiário** | VWAP calculado com dados do dia atual que ainda não ocorreram | Usar VWAP do dia anterior (`.shift(num_candles_no_dia)`) |
| **Fit do scaler com dados futuros** | Fazer `StandardScaler().fit(X_total)` antes do split treino/teste | Fit do scaler APENAS no conjunto de treino; aplicar o scaler treinado no teste |

### Template de Feature Segura

```python
def calcular_features_seguras(df):
    """Todas as features usam .shift(1) — só veem o passado"""
    
    # Calcular indicadores brutos (podem usar candle atual)
    df['rsi_raw'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ema_8_raw'] = df['close'].ewm(span=8).mean()
    df['atr_raw'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    
    # Features para o modelo: SEMPRE .shift(1)
    df['rsi_14'] = df['rsi_raw'].shift(1)
    df['rsi_14_norm'] = ((df['rsi_raw'] - 50) / 50).shift(1)
    df['rsi_slope'] = df['rsi_raw'].diff(3).shift(1)
    df['ema8_slope'] = (df['ema_8_raw'] / df['ema_8_raw'].shift(3) - 1).shift(1)
    df['atr_norm'] = (df['atr_raw'] / df['close']).shift(1)
    df['volume_ratio'] = (df['volume'] / df['volume'].rolling(20).mean()).shift(1)
    
    # Remover NaNs introduzidos pelo shift e rolling
    df = df.dropna()
    
    return df
```

---

## 4. PIPELINE DE ML RECOMENDADO

### 4.1 Pré-processamento

```
1. Calcular todas as features com .shift(1)
2. Calcular labels por trade (olha para frente — permitido)
3. Criar DataFrame com uma linha por trade (não por candle)
4. Separar features (X) e label (y)
5. NÃO usar StandardScaler no XGBoost puro → XGBoost é robusto a escala
   (usar apenas para LSTM, que requer normalização)
6. Tratar valores ausentes: df.fillna(method='ffill').dropna()
```

**Por que NÃO normalizar para XGBoost:**  
O XGBoost faz splits em valores absolutos — ele encontra o limiar ideal independente de escala. Normalização não melhora performance e pode ocultar o valor real das features nas análises de importância.

**Quando normalizar:**  
Para LSTM (fase F4.3): normalização por rolling window é obrigatória:
```python
# Normalização por z-score com janela de 100 candles (sem look-ahead)
df['rsi_norm'] = (df['rsi_raw'] - df['rsi_raw'].rolling(100).mean().shift(1)) / df['rsi_raw'].rolling(100).std().shift(1)
```

---

### 4.2 Walk-Forward Validation — Implementação Correta

**Por que não usar train/test split simples:**  
Um split em 80/20 aleatório em dados de tempo introduz look-ahead bias estrutural. O modelo veria padrões de 2024 para prever sinais de 2022.

**Estrutura recomendada para este projeto (77 trades em 4,5 anos):**

```
Problema: 77 trades é pouco para walk-forward tradicional
Solução: usar expanding window (âncora fixa no início)

Janela 1:
  Train: trades de 2022 (estimativa: ~20 trades)
  Test:  trades de 2023 (~20 trades)
  
Janela 2:
  Train: trades de 2022+2023 (~40 trades)
  Test:  trades de 2024 (~20 trades)

Janela 3:
  Train: trades de 2022+2023+2024 (~60 trades)
  Test:  trades de 2025-2026 (~17 trades)
```

**Embargo Period:** adicionar 5 candles de gap entre o último candle de treino e o primeiro candle de teste para evitar vazamento de correlação serial.

**Código esqueleto:**

```python
from sklearn.model_selection import TimeSeriesSplit

# Configurar splits temporais
tscv = TimeSeriesSplit(n_splits=3, gap=5)  # gap=5 candles de embargo

resultados_oos = []  # out-of-sample

for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    
    # Fit APENAS no treino
    modelo = xgb.XGBClassifier(...)
    modelo.fit(X_train, y_train)
    
    # Predizer no teste (out-of-sample)
    y_pred = modelo.predict(X_test)
    y_prob = modelo.predict_proba(X_test)[:, 1]
    
    resultados_oos.append({
        'fold': fold,
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'n_trades_test': len(y_test)
    })
```

---

### 4.3 Métricas de Avaliação

**Não usar accuracy** — com 40% de win rate base, um modelo que sempre prediz "não entra" teria 60% de accuracy.

| Métrica | O que mede | Alvo |
|---|---|---|
| **Precision (classe 1)** | Dos sinais que o modelo aprovou, quantos viraram TP? | > 55% (acima do base de 40%) |
| **Recall (classe 1)** | Dos trades que teriam ido ao TP, quantos o modelo identificou? | > 60% (não filtrar trades bons demais) |
| **F1-Score (classe 1)** | Harmônica entre precision e recall | > 0.55 |
| **ROC-AUC** | Poder discriminativo geral do modelo | > 0.60 |
| **Profit Factor filtrado** | PF calculado apenas nos trades que o modelo aprovou | > 1.8 (melhoria vs 1.28 atual) |
| **Win Rate filtrado** | Win rate dos trades que o modelo aprovou | > 52% (acima do break-even com RR 2:1) |

**Métricas financeiras são mais importantes que métricas de ML:**  
Um modelo com F1 = 0.55 que aumenta o Profit Factor de 1.28 para 1.8 é um sucesso, mesmo que a accuracy seja medíocre.

---

## 5. ORDEM DE IMPLEMENTAÇÃO

### Fase F4.1 — XGBoost (implementar PRIMEIRO)

**Por quê primeiro:**
- Mais simples de debugar (sem hiperparâmetros de arquitetura de rede)
- Feature importance nativa: XGBoost mostra quais features realmente importam
- Não requer normalização das features
- Treinamento rápido mesmo em datasets pequenos (77 trades é suficiente para um primeiro modelo)
- Literatura 2024-2025 mostra que XGBoost supera LSTM em datasets tabulares com ruído — exatamente o caso de features de indicadores técnicos

**Conjunto mínimo de features para começar (top 10 priorizadas):**
1. `rsi_14` — mais consistente em estudos de feature importance
2. `rsi_slope` — direção do RSI
3. `ema_spread_8_21` — força do cruzamento
4. `adx_14` — mercado em tendência ou lateral
5. `atr_norm` — volatilidade relativa
6. `volume_ratio_20` — volume do sinal vs média
7. `bb_width` — squeeze de volatilidade
8. `macd_hist_norm` — aceleração da tendência
9. `regime_ema` — alinhamento macro
10. `hora_sin` + `hora_cos` — contexto temporal

**Hiperparâmetros iniciais (conservadores):**
```python
xgb.XGBClassifier(
    n_estimators=100,
    max_depth=3,          # raso para evitar overfitting (77 trades é pequeno)
    learning_rate=0.05,   # lento e estável
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=1.48,  # 46/31 — balancear classes (mais perdedores que vencedores)
    eval_metric='logloss',
    random_state=42
)
```

### Fase F4.2 — Ampliar Dataset e Features

Após validar que o pipeline funciona:
- Adicionar features de regime (HMM ou baseado em EMA 200)
- Testar com mais trades: rodar backtest com parâmetros mais relaxados para gerar 200+ trades
- Adicionar features de candle pattern (doji, engolfo, martelo)

### Fase F4.3 — LSTM (implementar DEPOIS do XGBoost validado)

**Quando faz sentido:**
- Dataset com 500+ trades (janela temporal para LSTM aprender dependências)
- Features de preço bruto em sequência (LSTM captura padrões sequenciais que XGBoost não captura)
- Como complemento ao XGBoost, não substituto

**Arquitetura inicial:**
```
Input: sequência de 20 candles × N features
LSTM(64 units) → Dropout(0.2) → Dense(32) → Dense(1, sigmoid)
```

### Fase F4.4 — Ensemble (opcional, se F4.1 e F4.3 mostrarem resultados)

Combinar XGBoost + LSTM: aprovar trade apenas quando ambos concordam → aumenta precision às custas de recall.

---

## 6. ARMADILHAS COMUNS — ESPECÍFICAS PARA ESTE PROJETO

### 6.1 Overfitting em Dataset Pequeno (crítico)

**Problema:** 77 trades é muito pouco para modelos complexos. Um XGBoost com `max_depth=8` vai memorizar os dados de treino.

**Solução:**
- Manter `max_depth <= 4` até ter 300+ trades
- Usar regularização: `reg_alpha=0.1, reg_lambda=1.0`
- Monitorar diferença entre performance de treino e teste: se treino >> teste, overfitting

### 6.2 Distribuição de Classes Desbalanceada

**Problema:** 40% de win rate → mais perdedores que vencedores → modelo pode aprender a sempre prever 0.

**Solução:**
```python
scale_pos_weight = num_negativos / num_positivos  # 46/31 ≈ 1.48
# Passar para XGBClassifier
```

### 6.3 Calcular Features Sobre o Candle de Sinal (não o anterior)

**Problema específico deste projeto:** o sinal EMA 8/21 é gerado quando `ema_8 cruza ema_21`. O cruzamento é detectado no fechamento do candle. Se usarmos as features desse mesmo candle como input, estamos usando informação que só existe APÓS o fechamento.

**Solução:** usar `.shift(1)` em todas as features — o modelo deve ver apenas o candle ANTERIOR ao sinal.

### 6.4 Normalização com Vazamento de Dados

**Problema:** fazer `scaler.fit(X_total)` antes do split treino/teste contamina o teste com estatísticas do futuro.

**Solução:**
```python
X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
scaler = StandardScaler()
X_train_scaled = scaler.fit(X_train).transform(X_train)  # fit SÓ no treino
X_test_scaled = scaler.transform(X_test)                  # apply no teste
```

### 6.5 Selecionar Features com Todo o Dataset

**Problema:** usar feature importance ou correlação calculada sobre todo o dataset para selecionar quais features incluir — isso introduz look-ahead bias na seleção.

**Solução:** fazer feature selection dentro do loop de walk-forward, apenas com dados de treino do fold atual.

### 6.6 Usar Retorno do Trade Futuro para Calcular Features

**Exemplo perigoso:** `feature_retorno = (preco_saida / preco_entrada - 1)` como feature (óbvio, mas já foi feito em projetos reais). Mais sutil: usar janelas temporais que se sobrepõem com o período do trade.

**Solução:** features devem ser calculadas apenas com dados do candle de entrada e candles anteriores. Nada que dependa do que acontece APÓS a entrada.

---

## 7. REFERÊNCIAS E FONTES

- **XGBoost + Bitcoin (2025):** [Hybrid TLBO–XGBoost Model for Bitcoin Price Prediction](https://onlinelibrary.wiley.com/doi/full/10.1155/int/6674437) — WIJIS, 2025
- **LSTM + XGBoost Híbrido (2025):** [Crypto Price Prediction Using LSTM+XGBoost](https://arxiv.org/abs/2506.22055) — arXiv, junho 2025
- **Comparação XGBoost vs LSTM em crypto:** [Machine learning approaches to cryptocurrency trading optimization](https://link.springer.com/article/10.1007/s44163-025-00519-y) — Springer, 2025
- **Feature importance XGBoost:** [XGBoost Forecasting with Walk Forward Validation](https://arxiv.org/pdf/2601.08896) — RSI e rolling mean como top features
- **Walk-Forward Validation:** [Interpretable Hypothesis-Driven Trading: Walk-Forward Framework](https://arxiv.org/html/2512.12924v1) — arXiv, dez 2025
- **Look-Ahead Bias:** [Machine Learning & Volatility Forecasting: Avoiding the Look-Ahead Trap](https://medium.com/@contact_9367/machine-learning-volatility-forecasting-avoiding-the-look-ahead-trap-6ff63c8c703c)
- **Market Regime Detection:** [Regime-Aware Adaptive Forecasting Framework for Bitcoin](https://link.springer.com/article/10.1007/s10614-026-11338-3) — Springer Computational Economics, 2026
- **Walk-Forward na prática:** [Walk-Forward Optimization: QuantInsti](https://blog.quantinsti.com/walk-forward-optimization-introduction/)

---

## 8. RESUMO EXECUTIVO PARA O ORQUESTRADOR

**Situação:** estratégia EMA 8/21 com 59.7% de trades no stop. XGBoost pode filtrar falsos sinais.

**Label:** classificação binária — trade vai ao TP (1) ou ao SL (0).

**Features prioritárias (top 10 para começar):**
1. RSI(14) e sua inclinação — maior poder preditivo em literatura
2. Spread EMA 8/21 normalizado — força do cruzamento
3. ADX(14) — mercado em tendência vs lateral
4. ATR normalizado — volatilidade relativa
5. Volume ratio 20 candles — volume do sinal vs média
6. BB Width — contexto de squeeze
7. MACD histograma normalizado — aceleração
8. Regime EMA (quantas EMAs alinhadas) — contexto macro
9. Codificação temporal cíclica (hora_sin, hora_cos) — padrões 24/7
10. Candle body ratio — convicção do candle de sinal

**Ordem de implementação:**
1. **XGBoost primeiro** — mais simples, interpretável, rápido de validar
2. **LSTM depois** — apenas quando tiver 500+ trades e o pipeline validado
3. **Ensemble opcional** — combinar ambos se os resultados justificarem

**Risco principal:** 77 trades é estatisticamente insuficiente para ML robusto. O Desenvolvedor deve primeiro ampliar o dataset (período 2022-2026 completo = estimativa de 150-200+ trades) antes de treinar modelos.

**Próxima ação:** despachar Agente Desenvolvedor para:
1. Rodar backtest completo 2022-2026 (ampliar dataset)
2. Implementar script de feature engineering seguindo este roadmap
3. Treinar XGBoost com walk-forward validation (3 folds temporais)
4. Reportar métricas: precision, recall, F1 e profit factor filtrado

---

*Documento gerado em 01/07/2026 pelo Agente Pesquisador — Projeto Safe Trading F4*  
*Baseado em pesquisa de literatura 2024-2026 e análise do backtest atual (77 trades, PF 1.288)*
