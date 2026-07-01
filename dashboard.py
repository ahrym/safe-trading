# =============================================================================
# Safe Trading Dashboard — Dash + Plotly
# Dashboard visual completo com 4 módulos interativos
# =============================================================================

import json
import os
import traceback
from datetime import datetime, timezone

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import requests
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from flask import request, Response
from plotly.subplots import make_subplots
from apscheduler.schedulers.background import BackgroundScheduler

# Carrega variáveis de ambiente do .env (se existir — só em dev local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =============================================================================
# CONFIGURAÇÃO GERAL
# =============================================================================

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_RESULTS = os.path.join(DIRETORIO_BASE, "results")
DIRETORIO_DATA = os.path.join(DIRETORIO_BASE, "data")

# Paleta de cores do tema dark
COR_FUNDO = "#0d1117"
COR_CARD = "#161b22"
COR_BORDA = "#30363d"
COR_VERDE = "#00ff88"
COR_VERMELHO = "#ff4444"
COR_LARANJA = "#ff8800"
COR_AZUL = "#4488ff"
COR_CINZA = "#8b949e"
COR_TEXTO = "#e6edf3"
COR_TEXTO_SECUNDARIO = "#8b949e"

# Tema Plotly customizado
LAYOUT_GRAFICO = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0d1117",
    font=dict(color=COR_TEXTO, family="monospace"),
    xaxis=dict(
        gridcolor="#21262d",
        linecolor="#30363d",
        tickcolor=COR_CINZA,
        zerolinecolor="#21262d",
    ),
    yaxis=dict(
        gridcolor="#21262d",
        linecolor="#30363d",
        tickcolor=COR_CINZA,
        zerolinecolor="#21262d",
    ),
    legend=dict(
        bgcolor="rgba(22,27,34,0.8)",
        bordercolor="#30363d",
        borderwidth=1,
    ),
    margin=dict(l=50, r=30, t=50, b=50),
)

os.makedirs(DIRETORIO_RESULTS, exist_ok=True)

# =============================================================================
# FUNÇÕES AUXILIARES — LEITURA DE DADOS
# =============================================================================

def carregar_json(caminho_arquivo, fallback=None):
    """Carrega JSON com tratamento de erro gracioso."""
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def calcular_ema(serie, periodo):
    """Calcula EMA (Exponential Moving Average)."""
    return serie.ewm(span=periodo, adjust=False).mean()


def calcular_rsi(serie, periodo=14):
    """Calcula RSI (Relative Strength Index)."""
    delta = serie.diff()
    ganho = delta.where(delta > 0, 0.0)
    perda = -delta.where(delta < 0, 0.0)
    media_ganho = ganho.ewm(com=periodo - 1, adjust=False).mean()
    media_perda = perda.ewm(com=periodo - 1, adjust=False).mean()
    rs = media_ganho / media_perda
    return 100 - (100 / (1 + rs))


def calcular_atr(df, periodo=14):
    """Calcula ATR (Average True Range)."""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - close_prev).abs(),
            (low - close_prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=periodo).mean()


def buscar_freqtrade_status():
    """
    Busca o status do Freqtrade via API REST.
    Lê a URL base da variável de ambiente FREQTRADE_URL (Railway)
    ou usa o padrão localhost:8081 em desenvolvimento local.
    Retorna dict com dados ou None se Freqtrade estiver offline.
    """
    url_base = os.environ.get("FREQTRADE_URL", "http://localhost:8081")
    auth = ("freqtrade", "safetrading123")
    resultado = {}

    try:
        # Status geral do bot
        resp_status = requests.get(
            f"{url_base}/api/v1/status",
            auth=auth,
            timeout=5,
        )
        if resp_status.status_code == 200:
            resultado["trades_abertos"] = resp_status.json()
        else:
            resultado["trades_abertos"] = []

        # Balanço / capital atual
        resp_balance = requests.get(
            f"{url_base}/api/v1/balance",
            auth=auth,
            timeout=5,
        )
        if resp_balance.status_code == 200:
            resultado["balance"] = resp_balance.json()

        # P&L do dia (profit)
        resp_profit = requests.get(
            f"{url_base}/api/v1/profit",
            auth=auth,
            timeout=5,
        )
        if resp_profit.status_code == 200:
            resultado["profit"] = resp_profit.json()

        # Informações do bot (estratégia ativa, modo, etc.)
        resp_show = requests.get(
            f"{url_base}/api/v1/show_config",
            auth=auth,
            timeout=5,
        )
        if resp_show.status_code == 200:
            resultado["config"] = resp_show.json()

        resultado["online"] = True
        return resultado

    except Exception:
        return None


def buscar_preco_btc():
    """Busca preço atual do BTC/USDT na API pública da Binance."""
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=5,
        )
        dados = resp.json()
        return float(dados["price"])
    except Exception:
        return None


def _parse_binance_klines(raw):
    df = pd.DataFrame(raw, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df.sort_values("timestamp").reset_index(drop=True)


def carregar_dados_btc():
    """Busca candles BTC/USDT 4h — tenta 3 fontes em cascata."""
    params = {"symbol": "BTCUSDT", "interval": "4h", "limit": 500}

    # Fonte 1: Binance principal
    try:
        resp = requests.get("https://api.binance.com/api/v3/klines", params=params, timeout=10)
        resp.raise_for_status()
        return _parse_binance_klines(resp.json())
    except Exception as e:
        print(f"[WARN] Binance principal falhou: {e}")

    # Fonte 2: Binance data mirror (mais permissivo para cloud)
    try:
        resp = requests.get("https://data-api.binance.vision/api/v3/klines", params=params, timeout=10)
        resp.raise_for_status()
        return _parse_binance_klines(resp.json())
    except Exception as e:
        print(f"[WARN] Binance mirror falhou: {e}")

    # Fonte 3: CoinGecko — não bloqueia IPs de cloud
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc",
            params={"vs_currency": "usd", "days": "90"},
            timeout=15
        )
        resp.raise_for_status()
        raw = resp.json()  # [[timestamp_ms, open, high, low, close], ...]
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["volume"] = 0.0
        return df.sort_values("timestamp").reset_index(drop=True)
    except Exception as e:
        print(f"[ERRO] Todas as fontes falharam: {e}")
        return pd.DataFrame()


def verificar_sinal_paper(df):
    """
    Verifica se há sinal de compra/venda nas últimas velas.
    Retorna dict com estado atual do paper trading.
    """
    if df.empty or len(df) < 50:
        return None

    df = df.copy()
    df["ema8"] = calcular_ema(df["close"], 8)
    df["ema21"] = calcular_ema(df["close"], 21)
    df["ema50"] = calcular_ema(df["close"], 50)
    df["rsi"] = calcular_rsi(df["close"], 14)
    df["atr"] = calcular_atr(df, 14)

    # Usa penúltima vela para evitar look-ahead bias
    idx = -2
    r = df.iloc[idx]
    r_prev = df.iloc[idx - 1]

    cruzamento_alta = (r_prev["ema8"] <= r_prev["ema21"]) and (r["ema8"] > r["ema21"])
    acima_ema50 = r["close"] > r["ema50"]
    rsi_ok = 40 <= r["rsi"] <= 65

    if cruzamento_alta and acima_ema50 and rsi_ok:
        return {
            "sinal": "COMPRA",
            "preco_entrada": r["close"],
            "stop": r["close"] - 1.5 * r["atr"],
            "tp": r["close"] + 3.0 * r["atr"],
            "rsi": r["rsi"],
            "ema8": r["ema8"],
            "ema21": r["ema21"],
            "timestamp": str(r["timestamp"]),
        }
    return {"sinal": "NEUTRO"}


def atualizar_paper_trading(df):
    """
    Roda lógica simples de paper trading e salva em results/paper_trades.json.
    Retorna o estado atual.
    """
    caminho_paper = os.path.join(DIRETORIO_RESULTS, "paper_trades.json")

    # Carrega estado existente
    estado = carregar_json(
        caminho_paper,
        fallback={
            "capital_inicial": 1000.0,
            "capital_atual": 1000.0,
            "posicao_aberta": None,
            "trades": [],
        },
    )

    if df.empty or len(df) < 50:
        return estado

    df = df.copy()
    df["ema8"] = calcular_ema(df["close"], 8)
    df["ema21"] = calcular_ema(df["close"], 21)
    df["ema50"] = calcular_ema(df["close"], 50)
    df["rsi"] = calcular_rsi(df["close"], 14)
    df["atr"] = calcular_atr(df, 14)

    # Verifica último sinal (penúltima vela para evitar look-ahead)
    r = df.iloc[-2]
    r_prev = df.iloc[-3]
    preco_atual = df.iloc[-1]["close"]

    posicao = estado.get("posicao_aberta")

    # Se há posição aberta, verifica stop/TP
    if posicao:
        pnl = 0.0
        motivo = None

        if preco_atual <= posicao["stop"]:
            pnl = (posicao["stop"] - posicao["entrada"]) / posicao["entrada"]
            motivo = "stop_loss"
        elif preco_atual >= posicao["tp"]:
            pnl = (posicao["tp"] - posicao["entrada"]) / posicao["entrada"]
            motivo = "take_profit"

        if motivo:
            capital_anterior = estado["capital_atual"]
            risco = capital_anterior * 0.01
            resultado_usdt = risco * (pnl / abs(posicao["stop"] - posicao["entrada"]) * posicao["entrada"])
            # Simplificado: 1% de risco por trade
            if motivo == "stop_loss":
                resultado_usdt = -capital_anterior * 0.01
            else:
                resultado_usdt = capital_anterior * 0.01 * 2.0  # RR 2:1

            estado["capital_atual"] += resultado_usdt
            estado["trades"].append(
                {
                    "entrada_ts": posicao["timestamp"],
                    "saida_ts": str(df.iloc[-1]["timestamp"]),
                    "preco_entrada": posicao["entrada"],
                    "preco_saida": preco_atual if motivo == "stop_loss" else posicao["tp"],
                    "stop": posicao["stop"],
                    "tp": posicao["tp"],
                    "resultado_usdt": round(resultado_usdt, 2),
                    "retorno_pct": round(resultado_usdt / capital_anterior * 100, 2),
                    "motivo": motivo,
                }
            )
            estado["posicao_aberta"] = None

    # Se sem posição, verifica sinal de entrada
    if not estado.get("posicao_aberta"):
        cruzamento_alta = (r_prev["ema8"] <= r_prev["ema21"]) and (r["ema8"] > r["ema21"])
        acima_ema50 = r["close"] > r["ema50"]
        rsi_ok = 40 <= r["rsi"] <= 65

        if cruzamento_alta and acima_ema50 and rsi_ok:
            estado["posicao_aberta"] = {
                "entrada": preco_atual,
                "stop": preco_atual - 1.5 * r["atr"],
                "tp": preco_atual + 3.0 * r["atr"],
                "timestamp": str(df.iloc[-1]["timestamp"]),
                "rsi": round(r["rsi"], 1),
            }

    # Salva estado atualizado
    try:
        with open(caminho_paper, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return estado


# =============================================================================
# MÓDULO 1 — TIMELINE DO PROJETO
# =============================================================================

MILESTONES = [
    {
        "fase": "F1",
        "nome": "Base de Conhecimento",
        "status": "concluido",
        "detalhe": "4 documentos fundacionais produzidos:\n• fundamentos-mercado.md\n• indicadores-tecnicos.md\n• exchanges-e-apis.md\n• glossario-trading-algoritmico.md",
    },
    {
        "fase": "F2",
        "nome": "Estratégia Definida",
        "status": "concluido",
        "detalhe": "Estratégia escolhida: EMA 8/21 + RSI(14) + Volume\nMercado: BTC/USDT 4h | Stop: 1.5×ATR | TP: 3×ATR\n4 estratégias comparadas pelo Agente Analista",
    },
    {
        "fase": "F3.1",
        "nome": "Ambiente Configurado",
        "status": "concluido",
        "detalhe": "Scripts criados: fetch_data.py, backtest.py, walk_forward.py\nDados baixados: btc_usdt_4h.csv (2022–2026)\nDependências instaladas via requirements.txt",
    },
    {
        "fase": "F3.2",
        "nome": "Backtest Rodado",
        "status": "concluido",
        "detalhe": "77 trades | Período: 2022–2026 | Dados reais Binance\nWin Rate: 40.26% | Profit Factor: 1.29\nMax Drawdown: 4.7% | Retorno: +5.03%",
    },
    {
        "fase": "F3.3",
        "nome": "Otimização Concluída",
        "status": "concluido",
        "detalhe": "3 variações testadas além do Baseline:\n• V1 (EMA 13/21): Sharpe -0.76 ❌\n• V2 (TP 2.0×): Sharpe 0.28 ❌\n• V3 (EMA 10/21): Sharpe -0.15 ❌\nBaseline venceu: Sharpe 0.46, PF 1.29 ✅",
    },
    {
        "fase": "F4",
        "nome": "Machine Learning",
        "status": "andamento",
        "detalhe": "Próxima fase — pré-requisito: F3 concluída ✅\nMódulos planejados:\n• XGBoost classificador (scikit-learn)\n• LSTM séries temporais\n• FinRL (Reinforcement Learning: PPO/A2C/SAC)\n• Comparação ML vs estratégia clássica",
    },
    {
        "fase": "F5",
        "nome": "Produção",
        "status": "pendente",
        "detalhe": "Aguardando F4 — pré-requisito: modelo ML validado\nEntregas:\n• VPS Linux (DigitalOcean/Hetzner)\n• Freqtrade + Docker em produção\n• Telegram Bot para alertas\n• Integração B3 (Nelogica ProfitDLL)",
    },
]

COR_STATUS = {
    "concluido": COR_VERDE,
    "andamento": COR_LARANJA,
    "pendente": COR_CINZA,
}


def criar_grafico_timeline():
    """Cria o gráfico de timeline horizontal do projeto."""
    fig = go.Figure()

    n = len(MILESTONES)
    y_linha = 0.5
    x_posicoes = list(range(n))

    # Linha de conexão
    fig.add_trace(
        go.Scatter(
            x=x_posicoes,
            y=[y_linha] * n,
            mode="lines",
            line=dict(color="#30363d", width=3),
            showlegend=False,
            hoverinfo="none",
        )
    )

    # Círculos e labels por milestone
    for i, ms in enumerate(MILESTONES):
        cor = COR_STATUS[ms["status"]]
        simbolo = "✅" if ms["status"] == "concluido" else ("🔶" if ms["status"] == "andamento" else "🔲")

        # Círculo preenchido
        fig.add_trace(
            go.Scatter(
                x=[i],
                y=[y_linha],
                mode="markers+text",
                marker=dict(
                    size=30,
                    color=cor,
                    line=dict(color=COR_FUNDO, width=3),
                    opacity=0.9,
                ),
                text=[ms["fase"]],
                textposition="middle center",
                textfont=dict(color=COR_FUNDO, size=10, family="monospace"),
                showlegend=False,
                hovertemplate=(
                    f"<b>{ms['fase']} — {ms['nome']}</b><br>"
                    + ms["detalhe"].replace("\n", "<br>")
                    + "<extra></extra>"
                ),
                name=ms["fase"],
            )
        )

        # Nome do milestone (alternando cima/baixo)
        y_texto = y_linha + 0.25 if i % 2 == 0 else y_linha - 0.25
        y_ancora = "bottom" if i % 2 == 0 else "top"

        fig.add_annotation(
            x=i,
            y=y_texto,
            text=f"<b>{simbolo} {ms['nome']}</b>",
            showarrow=False,
            font=dict(color=cor, size=11, family="monospace"),
            yanchor=y_ancora,
            align="center",
        )

    layout = dict(LAYOUT_GRAFICO)
    layout.update(
        dict(
            height=320,
            xaxis=dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                range=[-0.5, n - 0.5],
            ),
            yaxis=dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                range=[0, 1],
            ),
            title=dict(
                text="<b>Roadmap Safe Trading</b>",
                font=dict(color=COR_TEXTO, size=16),
                x=0.5,
            ),
        )
    )
    fig.update_layout(**layout)
    return fig


# =============================================================================
# MÓDULO 2 — HISTÓRICO DE BACKTESTS
# =============================================================================

def criar_graficos_backtests():
    """Cria os gráficos comparativos das variações de backtest."""
    caminho = os.path.join(DIRETORIO_RESULTS, "comparacao_variacoes.json")
    dados = carregar_json(caminho)

    if not dados:
        return (
            go.Figure().add_annotation(text="Dados não disponíveis", **dict(showarrow=False, font=dict(color=COR_CINZA, size=16), x=0.5, y=0.5)),
            go.Figure().add_annotation(text="Dados não disponíveis", **dict(showarrow=False, font=dict(color=COR_CINZA, size=16), x=0.5, y=0.5)),
            [],
        )

    variacoes = dados.get("variacoes", [])
    nomes = [v["variacao"].split("(")[0].strip() for v in variacoes]
    sharpes = [v["sharpe_ratio"] for v in variacoes]
    pfs = [v["profit_factor"] for v in variacoes]
    cores_sharpe = [COR_VERDE if s > 0 else COR_VERMELHO for s in sharpes]
    cores_pf = [COR_VERDE if p > 1 else COR_VERMELHO for p in pfs]

    # Gráfico Sharpe
    fig_sharpe = go.Figure()
    fig_sharpe.add_trace(
        go.Bar(
            x=nomes,
            y=sharpes,
            marker_color=cores_sharpe,
            marker_line_color="#30363d",
            marker_line_width=1,
            text=[f"{s:.3f}" for s in sharpes],
            textposition="outside",
            textfont=dict(color=COR_TEXTO),
            hovertemplate="<b>%{x}</b><br>Sharpe: %{y:.4f}<extra></extra>",
        )
    )
    layout_sharpe = dict(LAYOUT_GRAFICO)
    layout_sharpe.update(
        dict(
            height=300,
            title=dict(text="<b>Sharpe Ratio por Variação</b>", font=dict(color=COR_TEXTO, size=14), x=0.5),
            yaxis=dict(**LAYOUT_GRAFICO["yaxis"], title="Sharpe Ratio"),
            shapes=[dict(type="line", y0=0, y1=0, x0=-0.5, x1=len(nomes) - 0.5, line=dict(color=COR_CINZA, dash="dash", width=1))],
        )
    )
    fig_sharpe.update_layout(**layout_sharpe)

    # Gráfico Profit Factor
    fig_pf = go.Figure()
    fig_pf.add_trace(
        go.Bar(
            x=nomes,
            y=pfs,
            marker_color=cores_pf,
            marker_line_color="#30363d",
            marker_line_width=1,
            text=[f"{p:.3f}" for p in pfs],
            textposition="outside",
            textfont=dict(color=COR_TEXTO),
            hovertemplate="<b>%{x}</b><br>Profit Factor: %{y:.4f}<extra></extra>",
        )
    )
    layout_pf = dict(LAYOUT_GRAFICO)
    layout_pf.update(
        dict(
            height=300,
            title=dict(text="<b>Profit Factor por Variação</b>", font=dict(color=COR_TEXTO, size=14), x=0.5),
            yaxis=dict(**LAYOUT_GRAFICO["yaxis"], title="Profit Factor"),
            shapes=[dict(type="line", y0=1, y1=1, x0=-0.5, x1=len(nomes) - 0.5, line=dict(color=COR_CINZA, dash="dash", width=1))],
        )
    )
    fig_pf.update_layout(**layout_pf)

    # Dados para tabela
    tabela_dados = [
        {
            "Variação": v["variacao"],
            "Trades": v["total_trades"],
            "Win Rate": f"{v['win_rate_pct']:.1f}%",
            "Profit Factor": f"{v['profit_factor']:.3f}",
            "Sharpe": f"{v['sharpe_ratio']:.4f}",
            "Max DD": f"{v['max_drawdown_pct']:.1f}%",
            "Retorno": f"{v['retorno_total_pct']:.2f}%",
            "Capital Final": f"${v['capital_final']:.2f}",
        }
        for v in variacoes
    ]

    return fig_sharpe, fig_pf, tabela_dados


def criar_cards_destaque():
    """Cria cards com destaques dos resultados de backtest."""
    caminho = os.path.join(DIRETORIO_RESULTS, "comparacao_variacoes.json")
    dados = carregar_json(caminho)

    if not dados:
        return [html.P("Dados não disponíveis", style={"color": COR_CINZA})]

    variacoes = dados.get("variacoes", [])
    melhor_sharpe = max(variacoes, key=lambda v: v["sharpe_ratio"])
    menor_dd = min(variacoes, key=lambda v: v["max_drawdown_pct"])
    mais_trades = max(variacoes, key=lambda v: v["total_trades"])

    def card_destaque(titulo, valor, subtitulo, cor):
        return dbc.Card(
            dbc.CardBody([
                html.P(titulo, style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "12px", "marginBottom": "4px", "textTransform": "uppercase", "letterSpacing": "1px"}),
                html.H4(valor, style={"color": cor, "fontFamily": "monospace", "marginBottom": "2px"}),
                html.P(subtitulo, style={"color": COR_CINZA, "fontSize": "11px", "marginBottom": "0"}),
            ]),
            style={"backgroundColor": COR_CARD, "border": f"1px solid {cor}33", "borderRadius": "8px"},
        )

    return dbc.Row([
        dbc.Col(card_destaque(
            "Melhor Sharpe",
            f"{melhor_sharpe['sharpe_ratio']:.4f}",
            melhor_sharpe["variacao"].split("(")[0].strip(),
            COR_VERDE,
        ), width=4),
        dbc.Col(card_destaque(
            "Menor Drawdown",
            f"{menor_dd['max_drawdown_pct']:.1f}%",
            menor_dd["variacao"].split("(")[0].strip(),
            COR_AZUL,
        ), width=4),
        dbc.Col(card_destaque(
            "Mais Trades",
            str(mais_trades["total_trades"]),
            mais_trades["variacao"].split("(")[0].strip(),
            COR_LARANJA,
        ), width=4),
    ], className="mb-3")


# =============================================================================
# MÓDULO 3 — GRÁFICO BTC AO VIVO COM SINAIS
# =============================================================================

def criar_grafico_btc(preco_atual=None):
    """Cria o candlestick chart com EMAs, RSI e sinais de trade."""
    df = carregar_dados_btc()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aguardando dados da Binance...", showarrow=False, font=dict(color=COR_CINZA, size=14), x=0.5, y=0.5)
        fig.update_layout(**LAYOUT_GRAFICO, height=600)
        return fig

    # Últimas 200 velas
    df = df.tail(200).copy()
    df["ema8"] = calcular_ema(df["close"], 8)
    df["ema21"] = calcular_ema(df["close"], 21)
    df["ema50"] = calcular_ema(df["close"], 50)
    df["rsi"] = calcular_rsi(df["close"], 14)

    # Carrega trades do backtest para sinais
    resultado = carregar_json(os.path.join(DIRETORIO_RESULTS, "backtest_ema_resultado.json"))
    trades = resultado.get("trades", []) if resultado else []

    # Converte timestamps dos trades
    ts_compras = []
    precos_compras = []
    ts_vendas = []
    precos_vendas = []

    datas_df = set(df["timestamp"].astype(str).tolist())

    for t in trades:
        ts_e = t.get("entrada_timestamp", "")
        ts_s = t.get("saida_timestamp", "")
        if ts_e in datas_df:
            row = df[df["timestamp"].astype(str) == ts_e]
            if not row.empty:
                ts_compras.append(ts_e)
                precos_compras.append(row["low"].values[0] * 0.995)
        if ts_s in datas_df:
            row = df[df["timestamp"].astype(str) == ts_s]
            if not row.empty:
                ts_vendas.append(ts_s)
                precos_vendas.append(row["high"].values[0] * 1.005)

    # Subplot: candlestick + RSI
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.04,
        subplot_titles=("BTC/USDT 4H — Candlestick + EMAs", "RSI (14)"),
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="BTC/USDT",
            increasing_line_color=COR_VERDE,
            decreasing_line_color=COR_VERMELHO,
            increasing_fillcolor="rgba(0,255,136,0.4)",
            decreasing_fillcolor="rgba(255,68,68,0.4)",
        ),
        row=1, col=1,
    )

    # EMAs
    for periodo, cor, nome in [(8, COR_AZUL, "EMA 8"), (21, COR_LARANJA, "EMA 21"), (50, "#ff88ff", "EMA 50")]:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df[f"ema{periodo}"],
                mode="lines",
                name=nome,
                line=dict(color=cor, width=1.5),
                opacity=0.8,
            ),
            row=1, col=1,
        )

    # Sinais de compra
    if ts_compras:
        fig.add_trace(
            go.Scatter(
                x=ts_compras,
                y=precos_compras,
                mode="markers",
                name="Sinal Compra",
                marker=dict(symbol="triangle-up", size=12, color=COR_VERDE, line=dict(color=COR_FUNDO, width=1)),
                hovertemplate="<b>COMPRA</b><br>%{x}<br>Preço: $%{y:,.0f}<extra></extra>",
            ),
            row=1, col=1,
        )

    # Sinais de venda
    if ts_vendas:
        fig.add_trace(
            go.Scatter(
                x=ts_vendas,
                y=precos_vendas,
                mode="markers",
                name="Sinal Venda",
                marker=dict(symbol="triangle-down", size=12, color=COR_VERMELHO, line=dict(color=COR_FUNDO, width=1)),
                hovertemplate="<b>VENDA</b><br>%{x}<br>Preço: $%{y:,.0f}<extra></extra>",
            ),
            row=1, col=1,
        )

    # Preço atual (linha horizontal)
    if preco_atual:
        fig.add_hline(
            y=preco_atual,
            line_dash="dot",
            line_color="rgba(255,255,255,0.27)",
            row=1, col=1,
        )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["rsi"],
            mode="lines",
            name="RSI(14)",
            line=dict(color=COR_AZUL, width=1.5),
        ),
        row=2, col=1,
    )
    fig.add_hrect(y0=40, y1=65, fillcolor="rgba(0,255,136,0.07)", line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,68,68,0.4)", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,255,136,0.4)", row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(139,148,158,0.3)", row=2, col=1)

    # Layout geral
    fig.update_layout(
        height=650,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0d1117",
        font=dict(color=COR_TEXTO, family="monospace"),
        legend=dict(bgcolor="rgba(22,27,34,0.8)", bordercolor="#30363d", borderwidth=1, orientation="h", y=1.02),
        margin=dict(l=60, r=30, t=80, b=40),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor="#21262d", linecolor="#30363d")
    fig.update_yaxes(gridcolor="#21262d", linecolor="#30363d")
    fig.update_yaxes(title_text="Preço (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])

    return fig


# =============================================================================
# MÓDULO 4 — PAPER TRADING
# =============================================================================

def criar_conteudo_paper():
    """Cria o conteúdo visual do módulo de paper trading."""
    caminho_paper = os.path.join(DIRETORIO_RESULTS, "paper_trades.json")
    df = carregar_dados_btc()
    estado = atualizar_paper_trading(df)

    capital_inicial = estado.get("capital_inicial", 1000.0)
    capital_atual = estado.get("capital_atual", 1000.0)
    pnl = capital_atual - capital_inicial
    retorno_pct = (pnl / capital_inicial) * 100
    posicao = estado.get("posicao_aberta")
    trades = estado.get("trades", [])

    cor_pnl = COR_VERDE if pnl >= 0 else COR_VERMELHO
    sinal_pnl = "+" if pnl >= 0 else ""

    # Cards de resumo
    cards_resumo = dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.P("Capital Inicial", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
                html.H4(f"${capital_inicial:,.2f}", style={"color": COR_TEXTO, "fontFamily": "monospace"}),
            ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"}),
            width=3,
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.P("Capital Atual", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
                html.H4(f"${capital_atual:,.2f}", style={"color": cor_pnl, "fontFamily": "monospace"}),
            ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {cor_pnl}33", "borderRadius": "8px"}),
            width=3,
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.P("P&L Acumulado", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
                html.H4(f"{sinal_pnl}${pnl:,.2f}", style={"color": cor_pnl, "fontFamily": "monospace"}),
            ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {cor_pnl}33", "borderRadius": "8px"}),
            width=3,
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.P("Retorno %", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
                html.H4(f"{sinal_pnl}{retorno_pct:.2f}%", style={"color": cor_pnl, "fontFamily": "monospace"}),
            ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {cor_pnl}33", "borderRadius": "8px"}),
            width=3,
        ),
    ], className="mb-4")

    # Indicador de posição aberta
    if posicao:
        entrada = posicao.get("entrada", 0)
        stop = posicao.get("stop", 0)
        tp = posicao.get("tp", 0)
        rsi = posicao.get("rsi", 0)
        ts = posicao.get("timestamp", "")

        card_posicao = dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.Span("● POSIÇÃO ABERTA", style={"color": COR_LARANJA, "fontWeight": "bold", "fontSize": "14px", "letterSpacing": "2px"}),
                    html.Span(" — Long BTC/USDT 4h", style={"color": COR_CINZA, "fontSize": "13px"}),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Entrada", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "marginBottom": "2px"}),
                        html.H5(f"${entrada:,.2f}", style={"color": COR_AZUL, "fontFamily": "monospace"}),
                    ], width=3),
                    dbc.Col([
                        html.P("Stop Loss", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "marginBottom": "2px"}),
                        html.H5(f"${stop:,.2f}", style={"color": COR_VERMELHO, "fontFamily": "monospace"}),
                        html.P(f"({((stop - entrada) / entrada * 100):.2f}%)", style={"color": COR_VERMELHO, "fontSize": "11px", "marginTop": "-6px"}),
                    ], width=3),
                    dbc.Col([
                        html.P("Take Profit", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "marginBottom": "2px"}),
                        html.H5(f"${tp:,.2f}", style={"color": COR_VERDE, "fontFamily": "monospace"}),
                        html.P(f"(+{((tp - entrada) / entrada * 100):.2f}%)", style={"color": COR_VERDE, "fontSize": "11px", "marginTop": "-6px"}),
                    ], width=3),
                    dbc.Col([
                        html.P("RSI(14)", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "marginBottom": "2px"}),
                        html.H5(f"{rsi:.1f}", style={"color": COR_LARANJA, "fontFamily": "monospace"}),
                        html.P(f"Entrada: {ts[:16]}", style={"color": COR_CINZA, "fontSize": "10px", "marginTop": "-6px"}),
                    ], width=3),
                ]),
            ]),
            style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_LARANJA}55", "borderRadius": "8px", "marginBottom": "20px"},
        )
    else:
        card_posicao = dbc.Card(
            dbc.CardBody([
                html.Span("○ SEM POSIÇÃO ABERTA", style={"color": COR_CINZA, "fontWeight": "bold", "fontSize": "13px", "letterSpacing": "2px"}),
                html.Span(" — Aguardando sinal de compra (EMA 8/21 + RSI 40-65)", style={"color": COR_CINZA, "fontSize": "12px"}),
            ]),
            style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px", "marginBottom": "20px"},
        )

    # Tabela de trades paper
    if trades:
        colunas_paper = [
            {"name": "Entrada", "id": "entrada_ts"},
            {"name": "Saída", "id": "saida_ts"},
            {"name": "Preço Entrada", "id": "preco_entrada"},
            {"name": "Resultado (USDT)", "id": "resultado_usdt"},
            {"name": "Retorno %", "id": "retorno_pct"},
            {"name": "Motivo", "id": "motivo"},
        ]
        dados_tabela = [
            {
                "entrada_ts": t.get("entrada_ts", "")[:16],
                "saida_ts": t.get("saida_ts", "")[:16],
                "preco_entrada": f"${t.get('preco_entrada', 0):,.2f}",
                "resultado_usdt": f"${t.get('resultado_usdt', 0):+.2f}",
                "retorno_pct": f"{t.get('retorno_pct', 0):+.2f}%",
                "motivo": t.get("motivo", ""),
            }
            for t in reversed(trades[-20:])
        ]

        tabela_paper = dash_table.DataTable(
            columns=colunas_paper,
            data=dados_tabela,
            style_table={"overflowX": "auto", "borderRadius": "8px"},
            style_header={"backgroundColor": "#1c2128", "color": COR_TEXTO, "fontWeight": "bold", "border": f"1px solid {COR_BORDA}", "fontFamily": "monospace", "fontSize": "12px"},
            style_cell={"backgroundColor": COR_CARD, "color": COR_TEXTO, "border": f"1px solid {COR_BORDA}", "fontFamily": "monospace", "fontSize": "12px", "padding": "8px 12px"},
            style_data_conditional=[
                {"if": {"filter_query": '{resultado_usdt} contains "+"'}, "color": COR_VERDE},
                {"if": {"filter_query": '{resultado_usdt} contains "-"'}, "color": COR_VERMELHO},
            ],
        )
    else:
        tabela_paper = html.P("Nenhum trade paper registrado ainda. A lógica verifica sinais a cada 30 minutos.", style={"color": COR_CINZA, "fontStyle": "italic"})

    return html.Div([cards_resumo, card_posicao, tabela_paper])


# =============================================================================
# LAYOUT DO APP
# =============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="Safe Trading Dashboard",
    suppress_callback_exceptions=True,
)

# =============================================================================
# AUTENTICAÇÃO BÁSICA — protege o dashboard com usuário/senha
# Configurado via variáveis de ambiente DASHBOARD_USER e DASHBOARD_PASSWORD
# =============================================================================

DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "andre")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "safetrading123")

server = app.server  # Expõe o Flask server do Dash

@server.route("/health")
def health_check():
    """Rota pública para healthcheck do Railway — sem autenticação."""
    return "ok", 200


@server.before_request
def verificar_auth():
    """Exige autenticação HTTP Basic para acessar qualquer rota."""
    if request.path == "/health":
        return  # healthcheck passa sem auth
    auth = request.authorization
    if not auth or auth.username != DASHBOARD_USER or auth.password != DASHBOARD_PASSWORD:
        return Response(
            "Acesso restrito ao Safe Trading Dashboard",
            401,
            {"WWW-Authenticate": 'Basic realm="Safe Trading"'}
        )

ESTILO_TAB = {
    "backgroundColor": COR_CARD,
    "color": COR_CINZA,
    "border": f"1px solid {COR_BORDA}",
    "fontFamily": "monospace",
    "fontSize": "13px",
    "padding": "8px 20px",
}
ESTILO_TAB_SELECIONADA = {
    "backgroundColor": "#1c2128",
    "color": COR_TEXTO,
    "border": f"1px solid {COR_AZUL}",
    "borderBottom": "none",
    "fontFamily": "monospace",
    "fontSize": "13px",
    "fontWeight": "bold",
    "padding": "8px 20px",
}

app.layout = html.Div(
    style={"backgroundColor": COR_FUNDO, "minHeight": "100vh", "fontFamily": "monospace"},
    children=[
        # Header
        html.Div(
            style={"backgroundColor": "#0d1117", "borderBottom": f"1px solid {COR_BORDA}", "padding": "16px 32px"},
            children=[
                dbc.Row([
                    dbc.Col([
                        html.H2(
                            "Safe Trading 🤖",
                            style={"color": COR_TEXTO, "fontFamily": "monospace", "fontWeight": "bold", "marginBottom": "4px"},
                        ),
                        html.Span(
                            "Projeto em Construção",
                            style={"color": COR_CINZA, "fontSize": "13px", "letterSpacing": "1px"},
                        ),
                    ], width="auto"),
                    dbc.Col([
                        html.Div([
                            dbc.Badge("F3.3 — Otimização Concluída ✅", color="success", className="me-2", style={"fontFamily": "monospace", "fontSize": "12px"}),
                            dbc.Badge("F4 — ML em Planejamento 🔶", color="warning", style={"fontFamily": "monospace", "fontSize": "12px"}),
                        ], style={"display": "flex", "alignItems": "center", "height": "100%"}),
                    ], className="d-flex align-items-center justify-content-end"),
                ], className="align-items-center"),
            ],
        ),

        # Preço BTC ao vivo
        html.Div(
            id="barra-preco-btc",
            style={
                "backgroundColor": "#1c2128",
                "borderBottom": f"1px solid {COR_BORDA}",
                "padding": "8px 32px",
                "display": "flex",
                "alignItems": "center",
                "gap": "24px",
            },
        ),

        # Intervalo para atualização automática
        dcc.Interval(id="intervalo-preco", interval=30_000, n_intervals=0),
        dcc.Interval(id="intervalo-paper", interval=30 * 60 * 1000, n_intervals=0),  # 30 min

        # Conteúdo principal com abas
        html.Div(
            style={"padding": "24px 32px"},
            children=[
                dcc.Tabs(
                    id="abas",
                    value="timeline",
                    style={"marginBottom": "20px"},
                    children=[
                        dcc.Tab(label="📅 Timeline do Projeto", value="timeline", style=ESTILO_TAB, selected_style=ESTILO_TAB_SELECIONADA),
                        dcc.Tab(label="📊 Histórico de Backtests", value="backtests", style=ESTILO_TAB, selected_style=ESTILO_TAB_SELECIONADA),
                        dcc.Tab(label="📈 BTC ao Vivo + Sinais", value="btc_live", style=ESTILO_TAB, selected_style=ESTILO_TAB_SELECIONADA),
                        dcc.Tab(label="🤖 Paper Trading", value="paper", style=ESTILO_TAB, selected_style=ESTILO_TAB_SELECIONADA),
                        dcc.Tab(label="⚡ Freqtrade Live", value="freqtrade", style=ESTILO_TAB, selected_style=ESTILO_TAB_SELECIONADA),
                    ],
                ),
                html.Div(id="conteudo-aba"),
            ],
        ),

        # Footer
        html.Div(
            style={"borderTop": f"1px solid {COR_BORDA}", "padding": "12px 32px", "marginTop": "40px"},
            children=[
                html.P(
                    "Safe Trading Dashboard v1.0 — Dados reais Binance | Estratégia: EMA 8/21 + RSI(14) + Volume | BTC/USDT 4h",
                    style={"color": COR_CINZA, "fontSize": "11px", "marginBottom": "0", "textAlign": "center"},
                ),
            ],
        ),
    ],
)


# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    Output("barra-preco-btc", "children"),
    Input("intervalo-preco", "n_intervals"),
)
def atualizar_barra_preco(_):
    """Atualiza a barra de preço BTC a cada 30 segundos."""
    preco = buscar_preco_btc()
    agora = datetime.now().strftime("%H:%M:%S")

    if preco:
        return [
            html.Span("BTC/USDT", style={"color": COR_CINZA, "fontSize": "12px", "textTransform": "uppercase"}),
            html.Span(f"${preco:,.2f}", style={"color": COR_TEXTO, "fontWeight": "bold", "fontSize": "18px", "fontFamily": "monospace"}),
            html.Span(f"Atualizado: {agora}", style={"color": COR_CINZA, "fontSize": "11px", "marginLeft": "auto"}),
        ]
    return [
        html.Span("BTC/USDT", style={"color": COR_CINZA, "fontSize": "12px"}),
        html.Span("Preço não disponível (sem conexão)", style={"color": COR_CINZA, "fontSize": "13px"}),
    ]


@app.callback(
    Output("conteudo-aba", "children"),
    Input("abas", "value"),
    Input("intervalo-preco", "n_intervals"),
    Input("intervalo-paper", "n_intervals"),
)
def renderizar_aba(aba, n_preco, n_paper):
    """Renderiza o conteúdo da aba selecionada."""

    if aba == "timeline":
        fig_timeline = criar_grafico_timeline()
        painel_milestones = []
        for ms in MILESTONES:
            cor = COR_STATUS[ms["status"]]
            simbolo = "✅" if ms["status"] == "concluido" else ("🔶" if ms["status"] == "andamento" else "🔲")
            painel_milestones.append(
                dbc.Card(
                    dbc.CardBody([
                        html.Div([
                            html.Span(f"{ms['fase']}", style={"color": cor, "fontWeight": "bold", "fontSize": "12px", "fontFamily": "monospace", "marginRight": "8px"}),
                            html.Span(f"{simbolo} {ms['nome']}", style={"color": COR_TEXTO, "fontWeight": "bold", "fontSize": "14px"}),
                        ], className="mb-2"),
                        html.Pre(ms["detalhe"], style={"color": COR_CINZA, "fontSize": "12px", "whiteSpace": "pre-wrap", "marginBottom": "0", "lineHeight": "1.6"}),
                    ]),
                    style={"backgroundColor": COR_CARD, "border": f"1px solid {cor}33", "borderRadius": "8px", "marginBottom": "12px"},
                )
            )

        return html.Div([
            dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_timeline, config={"displayModeBar": False})),
                     style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px", "marginBottom": "20px"}),
            html.H5("Detalhes dos Milestones", style={"color": COR_TEXTO, "marginBottom": "16px"}),
            html.Div(painel_milestones),
        ])

    elif aba == "backtests":
        fig_sharpe, fig_pf, tabela_dados = criar_graficos_backtests()
        cards = criar_cards_destaque()

        colunas = [{"name": k, "id": k} for k in (tabela_dados[0].keys() if tabela_dados else [])]
        tabela = dash_table.DataTable(
            columns=colunas,
            data=tabela_dados,
            style_table={"overflowX": "auto", "borderRadius": "8px"},
            style_header={"backgroundColor": "#1c2128", "color": COR_TEXTO, "fontWeight": "bold", "border": f"1px solid {COR_BORDA}", "fontFamily": "monospace", "fontSize": "12px"},
            style_cell={"backgroundColor": COR_CARD, "color": COR_TEXTO, "border": f"1px solid {COR_BORDA}", "fontFamily": "monospace", "fontSize": "12px", "padding": "10px 14px"},
            style_data_conditional=[
                {"if": {"row_index": 0}, "borderLeft": f"3px solid {COR_VERDE}"},
            ],
        ) if tabela_dados else html.P("Dados não disponíveis", style={"color": COR_CINZA})

        return html.Div([
            cards,
            dbc.Row([
                dbc.Col(
                    dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_sharpe, config={"displayModeBar": False})),
                             style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"}),
                    width=6,
                ),
                dbc.Col(
                    dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_pf, config={"displayModeBar": False})),
                             style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"}),
                    width=6,
                ),
            ], className="mb-4"),
            html.H5("Tabela Comparativa Completa", style={"color": COR_TEXTO, "marginBottom": "12px"}),
            dbc.Card(dbc.CardBody(tabela),
                     style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"}),
        ])

    elif aba == "btc_live":
        preco = buscar_preco_btc()
        fig_btc = criar_grafico_btc(preco)

        banner_preco = html.Div(
            style={"marginBottom": "16px", "display": "flex", "gap": "24px", "alignItems": "center"},
            children=[
                html.Div([
                    html.Span("Preço Atual BTC/USDT  ", style={"color": COR_CINZA, "fontSize": "12px"}),
                    html.Span(
                        f"${preco:,.2f}" if preco else "N/A",
                        style={"color": COR_TEXTO, "fontWeight": "bold", "fontSize": "24px", "fontFamily": "monospace"},
                    ),
                ]),
                html.Div([
                    html.Span("Estratégia: ", style={"color": COR_CINZA, "fontSize": "12px"}),
                    html.Span("EMA 8/21 + RSI(14) + Volume | BTC/USDT 4h", style={"color": COR_AZUL, "fontSize": "12px", "fontFamily": "monospace"}),
                ]),
                html.Div([
                    html.Span("▲ Sinal Compra  ", style={"color": COR_VERDE, "fontSize": "12px"}),
                    html.Span("▼ Sinal Venda", style={"color": COR_VERMELHO, "fontSize": "12px"}),
                ]),
            ],
        )

        return html.Div([
            banner_preco,
            dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_btc, config={"displayModeBar": True, "displaylogo": False})),
                     style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"}),
        ])

    elif aba == "paper":
        conteudo = criar_conteudo_paper()
        return html.Div([
            html.H5("Paper Trading Simulado", style={"color": COR_TEXTO, "marginBottom": "4px"}),
            html.P(
                "Capital virtual de $1.000 | Estratégia: EMA 8/21 + RSI(40-65) | Stop 1.5×ATR | TP 3×ATR | Atualiza a cada 30 min",
                style={"color": COR_CINZA, "fontSize": "12px", "marginBottom": "20px"},
            ),
            conteudo,
        ])

    elif aba == "freqtrade":
        return criar_conteudo_freqtrade()

    return html.Div()


def criar_conteudo_freqtrade():
    """
    Cria o conteúdo da aba Freqtrade Live.
    Consome a API REST do Freqtrade (dry-run) rodando localmente ou no Railway.
    Exibe: status do bot, trades abertos, P&L e capital atual.
    Degrada graciosamente se o Freqtrade estiver offline.
    """
    dados = buscar_freqtrade_status()

    # --- Freqtrade offline: exibe mensagem amigável ---
    if not dados:
        return html.Div([
            html.H5("Freqtrade Live", style={"color": COR_TEXTO, "marginBottom": "8px"}),
            dbc.Alert(
                [
                    html.Strong("Freqtrade offline "),
                    html.Span("— o bot não está respondendo na porta configurada."),
                    html.Hr(),
                    html.P([
                        "Para iniciar localmente: ",
                        html.Code("cd freqtrade && docker-compose up -d", style={"backgroundColor": "#21262d", "padding": "2px 6px", "borderRadius": "4px"}),
                    ], className="mb-1"),
                    html.P([
                        "No Railway: configure a variável ",
                        html.Code("FREQTRADE_URL", style={"backgroundColor": "#21262d", "padding": "2px 6px", "borderRadius": "4px"}),
                        " com a URL do serviço Freqtrade.",
                    ], className="mb-0"),
                ],
                color="secondary",
                style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "color": COR_TEXTO, "fontFamily": "monospace", "fontSize": "13px"},
            ),
        ])

    # --- Freqtrade online: extrai dados ---
    config = dados.get("config", {})
    profit = dados.get("profit", {})
    balance = dados.get("balance", {})
    trades_abertos = dados.get("trades_abertos", [])

    estrategia = config.get("strategy", "—")
    dry_run = config.get("dry_run", True)
    modo_label = "DRY RUN (paper)" if dry_run else "LIVE (capital real)"
    modo_cor = COR_LARANJA if dry_run else COR_VERMELHO

    # P&L
    profit_total = profit.get("profit_all_coin", 0.0)
    profit_dia = profit.get("profit_factor", 0.0)
    total_trades = profit.get("trade_count", 0)
    wins = profit.get("winning_trades", 0)
    losses = profit.get("losing_trades", 0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

    # Capital
    capital_total = balance.get("total", 0.0)
    capital_livre = balance.get("free", 0.0)
    moeda = balance.get("symbol", "USDT")

    cor_profit = COR_VERDE if profit_total >= 0 else COR_VERMELHO
    sinal = "+" if profit_total >= 0 else ""

    # Cards de resumo
    cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Modo", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
            html.H5(modo_label, style={"color": modo_cor, "fontFamily": "monospace", "fontSize": "13px"}),
        ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {modo_cor}33", "borderRadius": "8px"}), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Estratégia", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
            html.H5(estrategia, style={"color": COR_AZUL, "fontFamily": "monospace", "fontSize": "13px"}),
        ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_AZUL}33", "borderRadius": "8px"}), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.P(f"Capital ({moeda})", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
            html.H5(f"{capital_total:.2f}", style={"color": COR_TEXTO, "fontFamily": "monospace"}),
            html.P(f"Livre: {capital_livre:.2f}", style={"color": COR_CINZA, "fontSize": "11px", "marginTop": "-4px"}),
        ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"}), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("P&L Total", style={"color": COR_TEXTO_SECUNDARIO, "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "1px", "marginBottom": "4px"}),
            html.H5(f"{sinal}{profit_total:.4f} {moeda}", style={"color": cor_profit, "fontFamily": "monospace", "fontSize": "13px"}),
            html.P(f"{total_trades} trades | Win: {win_rate:.1f}%", style={"color": COR_CINZA, "fontSize": "11px", "marginTop": "-4px"}),
        ]), style={"backgroundColor": COR_CARD, "border": f"1px solid {cor_profit}33", "borderRadius": "8px"}), width=3),
    ], className="mb-4")

    # Trades abertos
    if trades_abertos:
        linhas_trades = []
        for t in trades_abertos:
            pnl = t.get("profit_pct", 0.0) * 100
            cor_t = COR_VERDE if pnl >= 0 else COR_VERMELHO
            linhas_trades.append({
                "Par": t.get("pair", "—"),
                "Entrada": f"${t.get('open_rate', 0):,.2f}",
                "Atual": f"${t.get('current_rate', 0):,.2f}",
                "P&L %": f"{'+' if pnl >= 0 else ''}{pnl:.2f}%",
                "Abertura": str(t.get("open_date", "—"))[:16],
            })

        tabela_trades = dash_table.DataTable(
            columns=[{"name": k, "id": k} for k in linhas_trades[0].keys()],
            data=linhas_trades,
            style_table={"overflowX": "auto", "borderRadius": "8px"},
            style_header={"backgroundColor": "#1c2128", "color": COR_TEXTO, "fontWeight": "bold", "border": f"1px solid {COR_BORDA}", "fontFamily": "monospace", "fontSize": "12px"},
            style_cell={"backgroundColor": COR_CARD, "color": COR_TEXTO, "border": f"1px solid {COR_BORDA}", "fontFamily": "monospace", "fontSize": "12px", "padding": "8px 12px"},
            style_data_conditional=[
                {"if": {"filter_query": '{P&L %} contains "+"'}, "color": COR_VERDE},
                {"if": {"filter_query": '{P&L %} contains "-"'}, "color": COR_VERMELHO},
            ],
        )
        secao_trades = html.Div([
            html.H6(f"Trades Abertos ({len(trades_abertos)})", style={"color": COR_TEXTO, "marginBottom": "12px"}),
            tabela_trades,
        ])
    else:
        secao_trades = dbc.Card(
            dbc.CardBody(html.P("Nenhum trade aberto no momento.", style={"color": COR_CINZA, "fontStyle": "italic", "marginBottom": "0"})),
            style={"backgroundColor": COR_CARD, "border": f"1px solid {COR_BORDA}", "borderRadius": "8px"},
        )

    return html.Div([
        html.H5("Freqtrade Live", style={"color": COR_TEXTO, "marginBottom": "4px"}),
        html.P(
            "Conexão via API REST do Freqtrade | Dry-run (paper trading) | Atualiza com a página",
            style={"color": COR_CINZA, "fontSize": "12px", "marginBottom": "20px"},
        ),
        dbc.Alert(
            "Bot online — dry-run ativo",
            color="success",
            style={"backgroundColor": "rgba(0,255,136,0.1)", "border": f"1px solid {COR_VERDE}55",
                   "color": COR_VERDE, "fontFamily": "monospace", "fontSize": "12px", "padding": "8px 16px"},
        ),
        cards,
        secao_trades,
    ])


# =============================================================================
# ENTRY POINT
# =============================================================================

def buscar_velas_binance(symbol="BTCUSDT", intervalo="4h", limite=200):
    """Busca as últimas velas da Binance via API pública."""
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": intervalo, "limit": limite},
            timeout=10,
        )
        dados = resp.json()
        if not isinstance(dados, list):
            return pd.DataFrame()
        df = pd.DataFrame(dados, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"[Scheduler] Erro ao buscar velas Binance: {e}")
        return pd.DataFrame()


def job_atualizar_sinais():
    """
    Job executado pelo scheduler a cada 4 horas.
    Busca as últimas velas da Binance, recalcula indicadores,
    verifica sinais e atualiza o estado do paper trading.
    """
    print(f"[Scheduler] Job iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Busca dados atualizados da Binance
    df_live = buscar_velas_binance()

    if df_live.empty:
        print("[Scheduler] Sem dados da Binance — abortando job")
        return

    # 2. Tenta mesclar com dados históricos locais (se existir)
    df_historico = carregar_dados_btc()
    if not df_historico.empty:
        df_combinado = pd.concat([df_historico, df_live]).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    else:
        df_combinado = df_live

    # 3. Atualiza paper trading com dados combinados
    estado = atualizar_paper_trading(df_combinado)

    # 4. Sincroniza com Supabase (se configurado)
    try:
        from supabase_client import salvar_posicao_aberta, salvar_paper_trade, listar_paper_trades

        # Sincroniza posição aberta
        posicao = estado.get("posicao_aberta")
        salvar_posicao_aberta(posicao)

        # Sincroniza novos trades (os que estão no JSON mas não no Supabase)
        trades_locais = estado.get("trades", [])
        trades_remote = listar_paper_trades()
        ts_remote = {t.get("entrada_timestamp", "") for t in trades_remote}

        for trade in trades_locais:
            ts = trade.get("entrada_ts", trade.get("entrada_timestamp", ""))
            if ts not in ts_remote:
                trade_fmt = {
                    "entrada_timestamp": trade.get("entrada_ts", ""),
                    "saida_timestamp": trade.get("saida_ts", ""),
                    "preco_entrada": trade.get("preco_entrada"),
                    "preco_saida": trade.get("preco_saida"),
                    "stop_loss": trade.get("stop"),
                    "take_profit": trade.get("tp"),
                    "pnl_usdt": trade.get("resultado_usdt"),
                    "retorno_pct": trade.get("retorno_pct"),
                    "resultado": trade.get("motivo", ""),
                }
                salvar_paper_trade(trade_fmt)

    except ImportError:
        pass  # supabase_client não instalado — OK em dev local
    except Exception as e:
        print(f"[Scheduler] Erro ao sincronizar Supabase: {e}")

    capital = estado.get("capital_atual", 1000.0)
    n_trades = len(estado.get("trades", []))
    posicao_str = "ABERTA" if estado.get("posicao_aberta") else "sem posição"
    print(f"[Scheduler] Job concluído | Capital: ${capital:.2f} | Trades: {n_trades} | Posição: {posicao_str}")


# =============================================================================
# SCHEDULER — roda job_atualizar_sinais a cada 4 horas em background
# =============================================================================

_scheduler = BackgroundScheduler(daemon=True)
_scheduler.add_job(job_atualizar_sinais, "interval", hours=4, id="sinais_4h",
                   next_run_time=None)  # não roda imediatamente no startup
_scheduler.start()
print("[Scheduler] Iniciado — primeiro job em 4 horas")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Porta dinâmica: Railway injeta PORT automaticamente
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    print("\n" + "=" * 60)
    print("  Safe Trading Dashboard")
    if port == 8050:
        print(f"  http://127.0.0.1:{port}")
        print(f"  Usuario: {DASHBOARD_USER} | Senha: {DASHBOARD_PASSWORD}")
    else:
        print(f"  Rodando na porta {port} (produção)")
    print("=" * 60 + "\n")

    # host="0.0.0.0" necessário para Railway (aceita conexões externas)
    app.run(host="0.0.0.0", port=port, debug=debug)
