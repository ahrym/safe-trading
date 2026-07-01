"""
visualizar_dados.py — Script de visualização de dados do BTC/USDT
Projeto: Safe Trading
Descrição: Lê o CSV gerado pelo fetch_data.py e plota um gráfico de candlestick
           com EMA 8, EMA 21 e RSI(14) em subplot separado.
Requer: executar fetch_data.py primeiro para gerar o CSV.
"""

# ─────────────────────────────────────────────
# Importações das bibliotecas necessárias
# ─────────────────────────────────────────────
import pandas as pd                        # Para ler e manipular o CSV
import numpy as np                         # Para cálculos numéricos
import matplotlib.pyplot as plt            # Para criar gráficos
import matplotlib.dates as mdates          # Para formatar datas nos eixos do gráfico
import matplotlib.patches as mpatches     # Para criar legendas customizadas
import mplfinance as mpf                   # Para gráficos de candlestick profissionais
import os                                  # Para trabalhar com caminhos de arquivos
import sys                                 # Para encerrar o programa em caso de erro


# ─────────────────────────────────────────────
# Configurações do script
# ─────────────────────────────────────────────
QUANTIDADE_CANDLES = 60                    # Quantos candles exibir no gráfico (últimos 60 = ~10 dias)

# Caminhos dos arquivos (calcula relativos à localização do script)
PASTA_DADOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # Sobe um nível (sai de /scripts)
    "data"                                                         # Entra na pasta /data
)

ARQUIVO_CSV = os.path.join(PASTA_DADOS, "btc_usdt_4h.csv")        # Arquivo de entrada (gerado pelo fetch_data)
ARQUIVO_GRAFICO = os.path.join(PASTA_DADOS, "btc_chart.png")      # Arquivo de saída (gráfico PNG)


def ler_dados():
    """
    Lê o arquivo CSV gerado pelo fetch_data.py.
    Retorna um DataFrame pandas com os dados históricos.
    """
    print("Lendo dados do CSV...")

    # Verifica se o arquivo CSV existe antes de tentar ler
    if not os.path.exists(ARQUIVO_CSV):
        print(f"\nArquivo não encontrado: {ARQUIVO_CSV}")
        print("Execute primeiro: python scripts/fetch_data.py")
        sys.exit(1)                                               # Encerra com mensagem clara de como resolver

    try:
        # Lê o CSV e define a coluna 'timestamp' como índice do tipo datetime
        df = pd.read_csv(
            ARQUIVO_CSV,                                          # Caminho do arquivo
            index_col="timestamp",                                # Usa a coluna timestamp como índice
            parse_dates=True                                      # Converte o índice para formato de data
        )

        print(f"Dados carregados: {len(df)} candles no total.")
        return df                                                 # Retorna o DataFrame pronto

    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        sys.exit(1)


def calcular_indicadores(df):
    """
    Calcula os indicadores técnicos necessários para o gráfico:
    - EMA 8: Média Móvel Exponencial de 8 períodos (curto prazo)
    - EMA 21: Média Móvel Exponencial de 21 períodos (médio prazo)
    - RSI 14: Índice de Força Relativa de 14 períodos (sobrecompra/sobrevenda)
    """
    print("Calculando indicadores técnicos...")

    # EMA (Exponential Moving Average) dá mais peso aos preços recentes
    # EMA 8 = tendência de curto prazo (linha mais rápida, reage rápido ao preço)
    df["ema8"] = df["close"].ewm(span=8, adjust=False).mean()

    # EMA 21 = tendência de médio prazo (linha mais lenta, mais estável)
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

    # RSI (Relative Strength Index) mede força do movimento
    # Valores acima de 70 = sobrecomprado (possível queda)
    # Valores abaixo de 30 = sobrevendido (possível alta)
    delta = df["close"].diff()
    ganho = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    perda = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = ganho / perda.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))

    print("EMA 8, EMA 21 e RSI(14) calculados com sucesso!")
    return df                                                     # Retorna DataFrame com as colunas novas


def preparar_dados_para_grafico(df):
    """
    Seleciona apenas os últimos N candles para exibir no gráfico.
    O mplfinance exige que o índice seja DatetimeIndex.
    """
    print(f"Preparando os últimos {QUANTIDADE_CANDLES} candles para o gráfico...")

    # Pega apenas os últimos N candles (mais recentes)
    df_grafico = df.tail(QUANTIDADE_CANDLES).copy()               # .copy() evita avisos de modificação

    # Garante que o índice é do tipo DatetimeIndex (necessário para mplfinance)
    df_grafico.index = pd.DatetimeIndex(df_grafico.index)

    print(f"Período do gráfico: {df_grafico.index[0]} até {df_grafico.index[-1]}")
    return df_grafico                                             # Retorna só os candles que serão plotados


def gerar_grafico(df_grafico):
    """
    Gera o gráfico de candlestick com EMA 8, EMA 21 e RSI(14).
    Salva como PNG na pasta /data.
    """
    print("Gerando gráfico...")

    # ── Configuração do estilo do gráfico ──────────────────────
    # Define o estilo visual: fundo escuro (profissional para trading)
    estilo = mpf.make_mpf_style(
        base_mpf_style="nightclouds",                             # Tema escuro
        gridstyle="--",                                           # Linhas de grade tracejadas
        gridcolor="#333333",                                      # Cor das grades
        facecolor="#1a1a2e",                                      # Cor do fundo
        edgecolor="#333333",                                      # Cor da borda
        figcolor="#0f0f23",                                       # Cor do fundo da figura
        marketcolors=mpf.make_marketcolors(
            up="#00ff88",                                         # Candle de alta: verde
            down="#ff4444",                                       # Candle de baixa: vermelho
            edge="inherit",                                       # Borda segue a cor do candle
            wick="inherit",                                       # Pavio segue a cor do candle
            volume="in",                                          # Volume integrado ao candle
        )
    )

    # ── Adiciona as linhas de EMA ao gráfico ───────────────────
    # ap = "additional plots" (plots adicionais sobre o gráfico de preço)
    ema8_plot = mpf.make_addplot(
        df_grafico["ema8"],                                       # Dados da EMA 8
        color="#FFD700",                                          # Cor amarela-dourada
        width=1.5,                                                # Espessura da linha
        label="EMA 8"                                             # Rótulo para a legenda
    )

    ema21_plot = mpf.make_addplot(
        df_grafico["ema21"],                                      # Dados da EMA 21
        color="#FF8C00",                                          # Cor laranja
        width=1.5,                                                # Espessura da linha
        label="EMA 21"                                            # Rótulo para a legenda
    )

    # ── Adiciona o RSI em subplot separado ─────────────────────
    rsi_plot = mpf.make_addplot(
        df_grafico["rsi14"],                                      # Dados do RSI
        panel=2,                                                  # Painel 2 = subplot abaixo do volume
        color="#00bfff",                                          # Cor azul ciano
        width=1.5,
        ylabel="RSI(14)",                                         # Rótulo do eixo Y
        label="RSI 14"
    )

    # Linha horizontal de sobrecompra (RSI = 70)
    rsi_70 = mpf.make_addplot(
        [70] * len(df_grafico),                                   # Lista com valor 70 para cada candle
        panel=2,                                                  # Mesmo painel do RSI
        color="#ff4444",                                          # Vermelho = zona de sobrecompra
        width=0.8,
        linestyle="--"                                            # Linha tracejada
    )

    # Linha horizontal de sobrevenda (RSI = 30)
    rsi_30 = mpf.make_addplot(
        [30] * len(df_grafico),                                   # Lista com valor 30 para cada candle
        panel=2,                                                  # Mesmo painel do RSI
        color="#00ff88",                                          # Verde = zona de sobrevenda
        width=0.8,
        linestyle="--"                                            # Linha tracejada
    )

    # ── Plota e salva o gráfico ─────────────────────────────────
    fig, axes = mpf.plot(
        df_grafico,                                               # DataFrame com os dados OHLCV
        type="candle",                                            # Tipo: candlestick
        style=estilo,                                             # Estilo visual definido acima
        title=f"\n  BTC/USDT — Gráfico 4H | Últimos {QUANTIDADE_CANDLES} Candles",
        ylabel="Preço (USDT)",                                    # Rótulo do eixo Y do preço
        volume=True,                                              # Mostra o volume de negociação
        volume_panel=1,                                           # Volume no painel 1 (abaixo do preço)
        addplot=[ema8_plot, ema21_plot, rsi_plot, rsi_70, rsi_30],  # Indicadores adicionais
        panel_ratios=(4, 1, 2),                                   # Proporção dos painéis: preço, volume, RSI
        figsize=(16, 10),                                         # Tamanho da figura em polegadas
        returnfig=True,                                           # Retorna a figura para customização
        warn_too_much_data=200                                    # Avisa se tiver mais de 200 candles
    )

    # ── Adiciona legenda manual ─────────────────────────────────
    # O mplfinance não adiciona legenda automaticamente para addplots
    legenda_ema8 = mpatches.Patch(color="#FFD700", label="EMA 8")   # Patch amarelo para EMA 8
    legenda_ema21 = mpatches.Patch(color="#FF8C00", label="EMA 21")  # Patch laranja para EMA 21
    legenda_rsi = mpatches.Patch(color="#00bfff", label="RSI(14)")   # Patch azul para RSI

    # Adiciona a legenda no primeiro painel (gráfico de preço)
    axes[0].legend(
        handles=[legenda_ema8, legenda_ema21, legenda_rsi],       # Itens da legenda
        loc="upper left",                                         # Posição: canto superior esquerdo
        facecolor="#1a1a2e",                                      # Fundo escuro
        edgecolor="#555555",                                      # Borda cinza
        labelcolor="white",                                       # Texto branco
        fontsize=10
    )

    # ── Salva o gráfico como PNG ────────────────────────────────
    try:
        fig.savefig(
            ARQUIVO_GRAFICO,                                      # Caminho do arquivo PNG
            dpi=150,                                              # Resolução (150 DPI = boa qualidade)
            bbox_inches="tight",                                  # Sem bordas em branco desnecessárias
            facecolor="#0f0f23"                                   # Mantém o fundo escuro ao salvar
        )
        print(f"Gráfico salvo em: {ARQUIVO_GRAFICO}")
        plt.close(fig)                                            # Fecha a figura para liberar memória

    except Exception as e:
        print(f"Erro ao salvar o gráfico: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────
# Função principal — orquestra tudo
# ─────────────────────────────────────────────
def main():
    """Executa o fluxo completo de leitura, cálculo e visualização."""

    print("\n" + "="*60)
    print("SAFE TRADING — Visualização de Dados")
    print(f"Arquivo: btc_usdt_4h.csv | Candles no gráfico: {QUANTIDADE_CANDLES}")
    print("="*60 + "\n")

    # Passo 1: Lê os dados do CSV
    df = ler_dados()

    # Passo 2: Calcula os indicadores técnicos (EMA 8, EMA 21, RSI 14)
    df = calcular_indicadores(df)

    # Passo 3: Seleciona os últimos N candles para o gráfico
    df_grafico = preparar_dados_para_grafico(df)

    # Passo 4: Gera e salva o gráfico
    gerar_grafico(df_grafico)

    print("\nConcluído!")
    print(f"Abra o arquivo para ver o gráfico: {ARQUIVO_GRAFICO}")


# Ponto de entrada do script
if __name__ == "__main__":
    main()
