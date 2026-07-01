"""
fetch_data.py — Script de busca de dados históricos da Binance
Projeto: Safe Trading
Descrição: Conecta na Binance (sem precisar de API key) e baixa 500 candles
           de BTC/USDT no timeframe de 4 horas, salvando em CSV.
"""

# ─────────────────────────────────────────────
# Importações das bibliotecas necessárias
# ─────────────────────────────────────────────
import ccxt                          # Biblioteca para conectar em exchanges de cripto
import pandas as pd                  # Biblioteca para manipular dados em tabelas (DataFrames)
import os                            # Biblioteca para trabalhar com pastas e arquivos
import sys                           # Biblioteca para controlar saída do programa
from datetime import datetime        # Para trabalhar com datas e horários


# ─────────────────────────────────────────────
# Configurações do script
# ─────────────────────────────────────────────
PAR_TRADING = "BTC/USDT"            # Par de moedas que vamos buscar (Bitcoin vs Dólar Tether)
TIMEFRAME = "4h"                     # Timeframe dos candles: 4 horas
QUANTIDADE_CANDLES = 500             # Quantos candles históricos queremos baixar

# Caminho da pasta onde os dados serão salvos
PASTA_DADOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # Sobe um nível (sai de /scripts)
    "data"                                                         # Entra na pasta /data
)

# Nome do arquivo CSV de saída
ARQUIVO_CSV = os.path.join(PASTA_DADOS, "btc_usdt_4h.csv")       # Caminho completo do arquivo


def criar_pasta_dados():
    """Cria a pasta /data se ela não existir ainda."""
    if not os.path.exists(PASTA_DADOS):                           # Verifica se a pasta existe
        os.makedirs(PASTA_DADOS)                                   # Cria a pasta (e subpastas se necessário)
        print(f"Pasta criada: {PASTA_DADOS}")                      # Avisa que criou a pasta


def conectar_binance():
    """
    Conecta na Binance sem precisar de API key.
    Retorna o objeto exchange pronto para uso.
    """
    print("Conectando na Binance...")                              # Avisa que está conectando

    try:
        # Cria uma instância da Binance usando a biblioteca ccxt
        # enableRateLimit=True faz o script respeitar os limites de requisição da Binance
        exchange = ccxt.binance({
            "enableRateLimit": True,                               # Ativa controle de velocidade automático
        })

        # Carrega os mercados disponíveis na exchange (lista de todos os pares de moedas)
        exchange.load_markets()

        print("Conexão estabelecida com sucesso!")                 # Confirma que conectou
        return exchange                                            # Retorna o objeto exchange para uso

    except ccxt.NetworkError as e:
        # Erro de rede: sem internet ou Binance fora do ar
        print(f"\nErro de conexão com a internet: {e}")
        print("Verifique sua conexão e tente novamente.")
        sys.exit(1)                                               # Encerra o programa com código de erro

    except ccxt.ExchangeError as e:
        # Erro da própria exchange (ex: manutenção)
        print(f"\nErro na Binance: {e}")
        print("A Binance pode estar em manutenção. Tente novamente em alguns minutos.")
        sys.exit(1)

    except Exception as e:
        # Qualquer outro erro inesperado
        print(f"\nErro inesperado ao conectar: {e}")
        sys.exit(1)


def buscar_candles(exchange):
    """
    Busca os candles históricos de BTC/USDT na Binance.
    Retorna uma lista de candles no formato OHLCV.
    """
    print(f"Buscando {QUANTIDADE_CANDLES} candles de {PAR_TRADING} ({TIMEFRAME})...")

    try:
        # fetch_ohlcv = busca dados de Open, High, Low, Close, Volume
        # Cada candle é uma lista: [timestamp, abertura, máxima, mínima, fechamento, volume]
        candles = exchange.fetch_ohlcv(
            symbol=PAR_TRADING,                                    # Par de moedas (BTC/USDT)
            timeframe=TIMEFRAME,                                   # Intervalo de tempo (4h)
            limit=QUANTIDADE_CANDLES                               # Quantidade de candles a buscar
        )

        # Valida se recebemos dados de verdade
        if not candles or len(candles) == 0:
            print("Nenhum dado recebido da Binance. Tente novamente.")
            sys.exit(1)

        print(f"Dados recebidos! Total de candles: {len(candles)}")  # Confirma quantos candles vieram
        return candles                                             # Retorna os dados brutos

    except ccxt.BadSymbol:
        # Par de moedas não existe na exchange
        print(f"Par '{PAR_TRADING}' não encontrado na Binance.")
        sys.exit(1)

    except ccxt.NetworkError as e:
        # Perda de conexão durante a busca
        print(f"Erro de rede ao buscar dados: {e}")
        print("Verifique sua internet e tente novamente.")
        sys.exit(1)

    except Exception as e:
        # Qualquer outro erro
        print(f"Erro ao buscar candles: {e}")
        sys.exit(1)


def converter_para_dataframe(candles):
    """
    Converte a lista bruta de candles em um DataFrame pandas organizado.
    Cada linha = 1 candle com: timestamp, open, high, low, close, volume.
    """
    print("Convertendo dados para DataFrame...")

    # Cria o DataFrame com os dados brutos
    # Cada candle da Binance vem como: [timestamp_ms, open, high, low, close, volume]
    df = pd.DataFrame(
        candles,                                                   # Lista de candles recebida
        columns=["timestamp", "open", "high", "low", "close", "volume"]  # Nomes das colunas
    )

    # Converte o timestamp de milissegundos para data/hora legível
    # A Binance retorna o tempo em millisegundos (ex: 1699999999000)
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],                                           # Coluna a converter
        unit="ms"                                                  # Unidade: milissegundos
    )

    # Define o timestamp como índice do DataFrame (facilita análise por tempo)
    df.set_index("timestamp", inplace=True)

    # Garante que os valores numéricos estão no formato float (número com decimal)
    df["open"] = df["open"].astype(float)                         # Preço de abertura
    df["high"] = df["high"].astype(float)                         # Preço máximo
    df["low"] = df["low"].astype(float)                           # Preço mínimo
    df["close"] = df["close"].astype(float)                       # Preço de fechamento
    df["volume"] = df["volume"].astype(float)                     # Volume negociado

    # Ordena por data (mais antigo primeiro, mais recente por último)
    df.sort_index(inplace=True)

    print(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas.")
    return df                                                      # Retorna o DataFrame pronto


def validar_dados(df):
    """
    Valida a qualidade dos dados recebidos.
    Verifica se há dados nulos, valores negativos, etc.
    """
    print("Validando qualidade dos dados...")

    # Verifica se há células vazias (nulas) no DataFrame
    nulos = df.isnull().sum().sum()                               # Conta total de valores nulos
    if nulos > 0:
        print(f"Aviso: Encontrados {nulos} valores nulos nos dados.")
    else:
        print("Sem valores nulos — dados completos!")

    # Verifica se os preços fazem sentido (positivos e coerentes)
    preco_invalido = (df["close"] <= 0).sum()                     # Conta fechamentos negativos ou zero
    if preco_invalido > 0:
        print(f"Aviso: {preco_invalido} candles com preço de fechamento inválido.")
    else:
        print("Preços validados — todos positivos!")

    # Verifica se high >= low em todos os candles (condição obrigatória)
    candles_invalidos = (df["high"] < df["low"]).sum()            # High menor que low seria impossível
    if candles_invalidos > 0:
        print(f"Aviso: {candles_invalidos} candles com high < low (dado corrompido).")
    else:
        print("Candles validados — estrutura OHLC coerente!")


def salvar_csv(df):
    """
    Salva o DataFrame em arquivo CSV na pasta /data.
    """
    print(f"Salvando dados em CSV...")

    try:
        # Salva o DataFrame como arquivo CSV
        # index=True mantém a coluna de timestamp no arquivo
        df.to_csv(ARQUIVO_CSV, index=True)
        print(f"Arquivo salvo: {ARQUIVO_CSV}")                    # Confirma o caminho do arquivo salvo

    except PermissionError:
        # Arquivo pode estar aberto em outro programa (ex: Excel)
        print(f"Erro: Sem permissão para salvar em {ARQUIVO_CSV}")
        print("Feche o arquivo se ele estiver aberto em outro programa.")
        sys.exit(1)

    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")
        sys.exit(1)


def exibir_resumo(df):
    """
    Exibe um resumo dos dados baixados no terminal.
    """
    print("\n" + "="*60)
    print("RESUMO DOS DADOS BAIXADOS")
    print("="*60)

    # Mostra o período coberto pelos dados
    print(f"Período: {df.index[0]} até {df.index[-1]}")          # Primeiro e último candle
    print(f"Total de candles: {len(df)}")                         # Quantidade total
    print(f"Timeframe: {TIMEFRAME}")                              # Intervalo de cada candle

    # Mostra as últimas 5 linhas (candles mais recentes)
    print("\n--- Últimas 5 linhas (candles mais recentes) ---")
    print(df.tail(5).to_string())                                 # .tail(5) pega as últimas 5 linhas

    # Mostra estatísticas básicas dos preços de fechamento
    print("\n--- Estatísticas do preço de fechamento (close) ---")
    stats = df["close"].describe()                                 # Calcula: count, mean, std, min, max, etc.
    print(f"Mínimo:  $ {stats['min']:>12,.2f}")                   # Preço mais baixo no período
    print(f"Máximo:  $ {stats['max']:>12,.2f}")                   # Preço mais alto no período
    print(f"Média:   $ {stats['mean']:>12,.2f}")                  # Preço médio
    print(f"Atual:   $ {df['close'].iloc[-1]:>12,.2f}")           # Preço do último candle fechado
    print("="*60)


# ─────────────────────────────────────────────
# Função principal — orquestra tudo
# ─────────────────────────────────────────────
def main():
    """Executa o fluxo completo de busca e salvamento de dados."""

    print("\n" + "="*60)
    print("SAFE TRADING — Busca de Dados Históricos")
    print(f"Par: {PAR_TRADING} | Timeframe: {TIMEFRAME} | Candles: {QUANTIDADE_CANDLES}")
    print("="*60 + "\n")

    # Passo 1: Garante que a pasta /data existe
    criar_pasta_dados()

    # Passo 2: Conecta na Binance
    exchange = conectar_binance()

    # Passo 3: Busca os candles históricos
    candles = buscar_candles(exchange)

    # Passo 4: Converte para DataFrame pandas
    df = converter_para_dataframe(candles)

    # Passo 5: Valida a qualidade dos dados
    validar_dados(df)

    # Passo 6: Salva em CSV
    salvar_csv(df)

    # Passo 7: Exibe resumo no terminal
    exibir_resumo(df)

    print("\nConcluído! Agora rode: python scripts/visualizar_dados.py")


# Ponto de entrada do script
# Este bloco só executa quando o script é rodado diretamente (não quando importado)
if __name__ == "__main__":
    main()
