# Exchanges e APIs — Safe Trading

> Documento técnico de referência para o projeto Safe Trading. Fase 1 — Fundamentação.
> Produzido pelo sub-agente Pesquisador. Data: 2026-06-26.

---

## 1. Como uma Exchange Centralizada (CEX) Funciona por Dentro

### Arquitetura de uma CEX (ex: Binance)

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────┐
│   Usuário   │────▶│  API Gateway     │────▶│   Order Book  │
│  (bot/human)│     │  (Auth + Rate    │     │   (memória)   │
└─────────────┘     │   Limiting)      │     └───────┬───────┘
                    └──────────────────┘             │
                                                     ▼
                                            ┌────────────────┐
                                            │ Matching Engine │
                                            │  (FIFO por     │
                                            │   preço/tempo) │
                                            └───────┬────────┘
                                                    │
                              ┌─────────────────────┼──────────────────┐
                              ▼                     ▼                  ▼
                    ┌──────────────┐     ┌──────────────┐   ┌──────────────┐
                    │  Liquidação  │     │  Atualização │   │  Notificação │
                    │  (settlement)│     │  de saldos   │   │  WebSocket   │
                    └──────────────┘     └──────────────┘   └──────────────┘
```

### Matching Engine

O coração da exchange. Responsável por:

1. **Receber ordens** dos participantes (via API ou interface)
2. **Manter o order book** em memória (estrutura de dados de alto desempenho)
3. **Casar ordens** seguindo regra de prioridade: **preço primeiro, tempo segundo** (FIFO)
4. **Gerar trades** quando há match e notificar as partes

**Regras de casamento:**
- Uma ordem de compra ao preço X casa com a melhor oferta de venda ≤ X
- Uma market order executa contra as melhores ordens disponíveis até esgotar o volume
- Uma limit order entra no book se não há contraparte disponível

### Liquidação

Após o casamento:
- Saldo do comprador: `- valor_pago_em_USDT, + BTC_recebido - taxa`
- Saldo do vendedor: `- BTC_vendido, + USDT_recebido - taxa`
- Tudo ocorre dentro da exchange (custódia centralizada)

### Tipos de taxa (Binance Spot)

| Nível VIP | Maker | Taker | Requisito volume 30d |
|---|---|---|---|
| Regular | 0.100% | 0.100% | < $1M |
| VIP 1 | 0.090% | 0.100% | > $1M |
| Com BNB (-25%) | 0.075% | 0.075% | Regular |

**Impacto no bot**: 0.1% de taxa em cada lado = 0.2% de custo por round-trip (entrada + saída). Estratégia com win rate de 55% e RR 1:1 pode ser lucrativa antes das taxas, mas lucrativa após?

```python
# Simulação de impacto de taxas no P&L
taxa = 0.001  # 0.1%
preco_entrada = 67_000
preco_saida = 67_500

lucro_bruto = (preco_saida - preco_entrada) / preco_entrada  # 0.746%
custo_taxas = taxa * 2  # entrada + saída = 0.2%
lucro_liquido = lucro_bruto - custo_taxas  # 0.546%
```

---

## 2. Binance API

### Tipos de API

#### REST API

- **Protocolo**: HTTP (GET, POST, DELETE)
- **Base URL spot**: `https://api.binance.com`
- **Uso**: consultar dados históricos, enviar ordens, verificar conta
- **Latência típica**: 50-200ms por requisição
- **Rate limit**: baseado em peso (weight) por IP

#### WebSocket API

- **Protocolo**: WebSocket (ws:// ou wss://)
- **Base URL streams**: `wss://stream.binance.com:9443/ws/`
- **Uso**: dados em tempo real (preço, trades, order book updates, atualizações de conta)
- **Latência típica**: < 10ms após conexão estabelecida
- **Rate limit**: 5 conexões por IP, 200 subscriptions por conexão

**Quando usar cada um:**

| Tarefa | REST | WebSocket |
|---|---|---|
| Buscar histórico de klines | Sim | Não |
| Verificar saldo da conta | Sim | Via listenKey |
| Enviar ordens | Sim | Sim (WebSocket API) |
| Monitorar preço em tempo real | Não ideal | Sim |
| Atualizar order book em tempo real | Não ideal | Sim |
| Executar bot de swing trade | Polling periódico | Recomendado para preços |

### Rate Limits

```
Tipos de rate limit na Binance:

1. REQUEST_WEIGHT (por IP)
   - Limite: 6.000 weight por minuto
   - Cada endpoint tem um peso diferente
   - Status 429 = limit atingido → aguardar
   - Status 418 = IP banido temporariamente

2. ORDERS (por conta)
   - 100 ordens por 10 segundos
   - 200.000 ordens por 24 horas (no mercado spot)

3. RAW_REQUESTS
   - 61.000 requests por 5 minutos

Pesos típicos:
  GET /api/v3/ticker/price     → weight 2
  GET /api/v3/klines           → weight 2
  GET /api/v3/depth            → weight 5-250 (depende do limit)
  POST /api/v3/order           → weight 1
  GET /api/v3/account          → weight 20
```

### Autenticação

A Binance usa dois tipos de requisição:

| Tipo | Autenticação | Endpoints |
|---|---|---|
| **PUBLIC** | Nenhuma | Klines, preços, order book |
| **SIGNED** | API Key + assinatura HMAC-SHA256 | Ordens, conta, saldos |

```python
import hmac
import hashlib
import time
from urllib.parse import urlencode

def criar_assinatura(params, api_secret):
    """Cria assinatura HMAC-SHA256 para requests assinados"""
    query_string = urlencode(params)
    return hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def requisicao_assinada(endpoint, params, api_key, api_secret):
    params['timestamp'] = int(time.time() * 1000)
    params['signature'] = criar_assinatura(params, api_secret)
    headers = {'X-MBX-APIKEY': api_key}
    # ... fazer request
```

### Endpoints Essenciais para um Bot

#### Dados de Mercado (PUBLIC)

```python
# Klines (OHLCV) — histórico de candles
GET /api/v3/klines
Parâmetros: symbol=BTCUSDT, interval=4h, limit=500
Resposta: [[open_time, open, high, low, close, volume, ...], ...]
Weight: 2

# Order Book
GET /api/v3/depth
Parâmetros: symbol=BTCUSDT, limit=20
Weight: 5 (limit<=20) até 250 (limit=5000)

# Preço atual
GET /api/v3/ticker/price
Parâmetros: symbol=BTCUSDT
Weight: 2

# Informações do mercado (limites, filtros de tamanho de ordem)
GET /api/v3/exchangeInfo
Weight: 20
```

#### Conta e Ordens (SIGNED)

```python
# Verificar saldo
GET /api/v3/account
Weight: 20

# Colocar ordem
POST /api/v3/order
Params: symbol, side (BUY/SELL), type (LIMIT/MARKET), quantity, price, timeInForce
Weight: 1

# Cancelar ordem
DELETE /api/v3/order
Weight: 1

# Listar ordens abertas
GET /api/v3/openOrders
Weight: 6

# Histórico de trades
GET /api/v3/myTrades
Weight: 20
```

#### WebSocket Streams essenciais

```python
# Stream de klines em tempo real
wss://stream.binance.com:9443/ws/btcusdt@kline_4h

# Stream de ticker (preço)
wss://stream.binance.com:9443/ws/btcusdt@ticker

# Stream de order book (diff)
wss://stream.binance.com:9443/ws/btcusdt@depth

# User Data Stream (atualizações de conta, ordens executadas)
# 1. Criar listenKey: POST /api/v3/userDataStream
# 2. Conectar: wss://stream.binance.com:9443/ws/<listenKey>
# 3. Renovar a cada 30min: PUT /api/v3/userDataStream
```

---

## 3. CCXT — CryptoCurrency eXchange Trading Library

### O que é

CCXT é uma biblioteca open-source disponível em Python, JavaScript, PHP, Go e Java que padroniza o acesso a mais de 100 exchanges de criptomoedas em uma interface unificada.

**Repositório**: [github.com/ccxt/ccxt](https://github.com/ccxt/ccxt)
**Documentação**: [docs.ccxt.com](https://docs.ccxt.com)

### Por que usar CCXT no Safe Trading

| Sem CCXT | Com CCXT |
|---|---|
| Código específico para cada exchange | Um único código funciona em 100+ exchanges |
| Gerenciar autenticação manualmente | Autenticação abstraída |
| Tratar rate limits por exchange | Rate limiting automático disponível |
| Mudar de exchange = reescrever o bot | Mudar exchange = trocar 2 linhas |
| Normalizar formatos diferentes | Formato padronizado (mercados, tickers, OHLCV) |

### Instalação

```bash
pip install ccxt
# ou para a versão pro (WebSocket em tempo real):
pip install ccxt[pro]
```

### Uso básico com Binance

```python
import ccxt

# Inicializar exchange
exchange = ccxt.binance({
    'apiKey': 'SUA_API_KEY',
    'secret': 'SEU_SECRET',
    'options': {
        'defaultType': 'spot',  # ou 'future' para futuros perpétuos
    }
})

# Buscar klines (OHLCV)
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '4h', limit=500)
# Retorna: [[timestamp, open, high, low, close, volume], ...]

# Converter para DataFrame
import pandas as pd
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Verificar saldo
balance = exchange.fetch_balance()
usdt_disponivel = balance['USDT']['free']

# Colocar ordem limit de compra
ordem = exchange.create_order(
    symbol='BTC/USDT',
    type='limit',
    side='buy',
    amount=0.001,  # BTC
    price=66_000   # USDT
)

# Cancelar ordem
exchange.cancel_order(order_id='123456', symbol='BTC/USDT')

# Buscar ordens abertas
ordens_abertas = exchange.fetch_open_orders('BTC/USDT')
```

### Estrutura padronizada de mercados

```python
# Buscar informações do mercado
mercados = exchange.load_markets()
btc_usdt = mercados['BTC/USDT']

# Campos importantes:
# btc_usdt['limits']['amount']['min']  → quantidade mínima
# btc_usdt['limits']['cost']['min']    → valor mínimo em USDT
# btc_usdt['precision']['amount']      → casas decimais para quantidade
# btc_usdt['precision']['price']       → casas decimais para preço
# btc_usdt['taker']                    → taxa taker
# btc_usdt['maker']                    → taxa maker
```

### CCXT Pro — WebSocket em tempo real

```python
import ccxt.pro as ccxtpro
import asyncio

async def monitorar_preco():
    exchange = ccxtpro.binance()
    
    while True:
        ticker = await exchange.watch_ticker('BTC/USDT')
        print(f"Preço: {ticker['last']}")
        
        # Klines em tempo real
        ohlcv = await exchange.watch_ohlcv('BTC/USDT', '4h')

asyncio.run(monitorar_preco())
```

---

## 4. brapi.dev — API B3 e Dados Financeiros Brasileiros

### O que é

brapi.dev é uma API REST brasileira que fornece dados do mercado financeiro nacional:
- Ações, FIIs, BDRs, ETFs da B3 (mais de 4.000 ativos)
- Indicadores econômicos (SELIC, IPCA, IGP-M, CDI, câmbio)
- Dados históricos e em tempo real
- Dividendos, proventos e dados fundamentalistas básicos

**Site**: [brapi.dev](https://brapi.dev)
**Docs**: [brapi.dev/docs](https://brapi.dev/docs)

### Autenticação

```python
# Opção 1: Query parameter
url = "https://brapi.dev/api/quote/PETR4?token=SEU_TOKEN"

# Opção 2: Header HTTP
headers = {"Authorization": "Bearer SEU_TOKEN"}

# Ativos gratuitos sem token (para teste):
# PETR4, VALE3, ITUB4, MGLU3
# IMPORTANTE: misturar estes com outros ativos exige token
```

### Endpoints Essenciais

#### Cotação de ativo

```python
import requests

# Cotação simples
r = requests.get("https://brapi.dev/api/quote/PETR4", 
                 headers={"Authorization": "Bearer TOKEN"})
data = r.json()

# Campos retornados:
# data['results'][0]['symbol']          → 'PETR4'
# data['results'][0]['regularMarketPrice']    → preço atual
# data['results'][0]['regularMarketChange']   → variação em R$
# data['results'][0]['regularMarketChangePercent'] → variação em %
# data['results'][0]['regularMarketVolume']   → volume
# data['results'][0]['regularMarketOpen']     → abertura
# data['results'][0]['regularMarketHigh']     → máxima do dia
# data['results'][0]['regularMarketLow']      → mínima do dia

# Múltiplos ativos de uma vez
r = requests.get("https://brapi.dev/api/quote/PETR4,VALE3,ITUB4",
                 headers={"Authorization": "Bearer TOKEN"})
```

#### Dados históricos (OHLCV)

```python
# Dados históricos com range
params = {
    "range": "1mo",       # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    "interval": "1d",     # 1d, 1wk, 1mo
    "token": "SEU_TOKEN"
}
r = requests.get("https://brapi.dev/api/quote/PETR4", params=params)

# Acessar histórico:
historico = r.json()['results'][0]['historicalDataPrice']
# [{'date': timestamp, 'open': x, 'high': x, 'low': x, 'close': x, 'volume': x}]
```

#### Indicadores econômicos

```python
# SELIC, CDI, IPCA, IGP-M, câmbio
r = requests.get("https://brapi.dev/api/v2/prime-rate",
                 headers={"Authorization": "Bearer TOKEN"})
# Retorna taxas de juros atuais

# Câmbio
r = requests.get("https://brapi.dev/api/v2/currency?currency=USD-BRL",
                 headers={"Authorization": "Bearer TOKEN"})
```

#### Listagem de ativos

```python
# Lista de todos os ativos disponíveis
r = requests.get("https://brapi.dev/api/quote/list",
                 headers={"Authorization": "Bearer TOKEN"})
# Suporta filtros: ?search=petro&limit=20&sortBy=close&sortOrder=desc
```

### Limitações para uso em bot

| Aspecto | Detalhe |
|---|---|
| **Delay de dados** | ~15 minutos (atraso regulatório B3) — sem dados tick-a-tick em tempo real no plano básico |
| **Horário de mercado B3** | Segunda a Sexta, 10h–17h (Brasília) — bot precisa respeitar |
| **Dados intraday** | Disponíveis mas com atraso; para swing trade (1D) é suficiente |
| **Rate limit** | Varia por plano; plano gratuito tem limite diário |

**Conclusão para o projeto**: brapi.dev é adequada para swing trade em ações (dados 1D são suficientes). Para day trade em B3, seria necessário uma solução com menor latência.

---

## 5. Nelogica ProfitDLL — B3 Futuros (Fase 5)

### Visão geral

ProfitDLL é a biblioteca Windows (.DLL) da Nelogica que fornece acesso programático à plataforma Profit (utilizada para operar contratos futuros na B3 via corretoras como Clear, XP, Rico, etc.).

**Documentação**: Disponibilizada via suporte técnico da Nelogica/corretora
**Linguagem**: C/C++ nativo, com wrappers disponíveis em Python (ctypes)

### Capacidades

- Execução de ordens em mini-índice (WIN) e mini-dólar (WDO)
- Dados de mercado em tempo real (nível 1 e nível 2 do book)
- Gerenciamento de posição e margem
- Callbacks para eventos de mercado (novos trades, mudanças no book)

### Relevância para o Safe Trading (F5)

```
F5 prevista: automação de contratos mini-índice (WIN) e mini-dólar (WDO)
Requisitos:
  - Windows (DLL nativa)
  - Conta em corretora parceira Nelogica (Clear, XP, etc.)
  - Python com ctypes para wrapper

Mini-contratos B3:
  WIN (mini-índice): 1 ponto = R$0,20; margem ~R$100/contrato
  WDO (mini-dólar):  1 pip = R$10,00; margem ~R$1.000/contrato
```

**Nota**: a implementação da ProfitDLL fica para a F5. Nas fases 2-4, o foco é Binance (CCXT) e B3 via brapi.dev.

---

## 6. Comparação Prática: Binance vs. B3 para um Bot Iniciante

| Critério | Binance (Crypto) | B3 (Ações) |
|---|---|---|
| **Horário de operação** | 24/7 (sem interrupcão) | Seg-Sex 10h-17h (leilão 9:45-10h) |
| **API disponível** | Excelente, REST + WebSocket | Intermediária (brapi.dev) ou cara (direto) |
| **Latência** | < 50ms (API pública) | 15min delay (brapi.dev) ou baixíssima (DMA) |
| **Custo por trade** | 0.1% (spot) | Emolumentos B3 (~0.025%) + corretagem |
| **Complexidade legal/fiscal** | Simples | IR mensal, DARF, come-cotas em FIIs |
| **Volatilidade** | Alta | Moderada |
| **Liquidez BTC/ETH** | Excelente | N/A |
| **Dados históricos** | Gratuitos via API | Gratuitos via brapi.dev |
| **Alavancagem disponível** | 1x-125x (futuros) | Até 5x (derivativos B3) |
| **Facilidade para iniciantes** | **Alta** | Média (regulação mais complexa) |
| **Ambiguidade de fuso horário** | UTC | America/Sao_Paulo (UTC-3) |

### Recomendação para o Safe Trading

**Fases 2-3: Binance** — menor fricção, API excelente, 24/7, sem preocupações com horário de mercado. Ideal para validar estratégias e aprender o desenvolvimento de bots.

**Fase 4: B3 via brapi.dev** — swing trade em ações grandes (PETR4, VALE3, ITUB4) com dados 1D. A latência de 15min não importa para swing trade.

**Fase 5: B3 Futuros via ProfitDLL** — mini-contratos com execução em tempo real. Máxima complexidade, máximo potencial.

---

## Referências

- [Binance API Docs — developers.binance.com](https://developers.binance.com/docs/binance-spot-api-docs)
- [Binance Rate Limits](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits)
- [CCXT Documentation](https://docs.ccxt.com)
- [CCXT GitHub](https://github.com/ccxt/ccxt)
- [brapi.dev Documentação](https://brapi.dev/docs)
- [brapi.dev API Ações](https://brapi.dev/docs/acoes)
