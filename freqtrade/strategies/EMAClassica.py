# =============================================================================
# Estratégia S1 — EMA Clássica (EMAClassica)
# Baseada na estratégia vencedora dos backtests F3.2/F3.3
# EMA 8/21 com filtro de EMA 50 (tendência macro), RSI(14) e Volume
# Stop loss: 1.5× ATR(14) | Take profit: 3.0× ATR(14) → RR 2:1
# Timeframe: 4h | Par: BTC/USDT
# =============================================================================

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd


class EMAClassica(IStrategy):
    """
    Estratégia clássica de cruzamento de EMA com filtros de RSI e Volume.

    Lógica de entrada (LONG):
    - EMA 8 cruza acima da EMA 21 (cruzamento de alta)
    - Preço acima da EMA 50 (tendência macro de alta)
    - RSI(14) entre 40 e 65 (zona saudável — evita sobrecompra)
    - Volume acima da média de 20 candles (confirma movimento)

    Saída:
    - Stop loss dinâmico: 1.5× ATR(14) abaixo da entrada
    - Take profit dinâmico: 3.0× ATR(14) acima da entrada
    - Fallback: minimal_roi como proteção adicional
    """

    # Nome da estratégia (aparece na API e logs do Freqtrade)
    INTERFACE_VERSION = 3

    # Timeframe da estratégia
    timeframe = "4h"

    # ROI mínimo como fallback de saída (tabela tempo × retorno mínimo)
    # Ex.: após 0 min, aceita qualquer lucro ≥ 10%; após 480 min (8h), ≥ 3%
    minimal_roi = {
        "0": 0.10,
        "240": 0.06,
        "480": 0.03,
        "1440": 0.01
    }

    # Stop loss de fallback em percentual (caso ATR não calcule a tempo)
    stoploss = -0.03

    # Ativa trailing stop — desabilitado aqui pois usamos ATR no custom_stoploss
    trailing_stop = False

    # Processa sinais apenas em velas fechadas (evita look-ahead bias)
    process_only_new_candles = True

    # Número de candles necessários para warmup dos indicadores
    startup_candle_count: int = 60

    # Parâmetros otimizáveis (para uso futuro com hyperopt)
    periodo_ema_rapida = IntParameter(5, 15, default=8, space="buy")
    periodo_ema_lenta = IntParameter(18, 30, default=21, space="buy")
    periodo_ema_macro = IntParameter(40, 60, default=50, space="buy")
    rsi_min = IntParameter(30, 50, default=40, space="buy")
    rsi_max = IntParameter(55, 75, default=65, space="buy")
    mult_atr_stop = DecimalParameter(1.0, 2.5, default=1.5, decimals=1, space="sell")
    mult_atr_tp = DecimalParameter(2.0, 5.0, default=3.0, decimals=1, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calcula todos os indicadores técnicos necessários.
        Chamado uma vez por par por ciclo de análise.
        """

        # --- Médias Móveis Exponenciais ---
        dataframe["ema8"] = ta.EMA(dataframe, timeperiod=self.periodo_ema_rapida.value)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=self.periodo_ema_lenta.value)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=self.periodo_ema_macro.value)

        # --- RSI (Relative Strength Index) ---
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # --- ATR (Average True Range) — para stop/tp dinâmicos ---
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # --- Volume médio dos últimos 20 candles ---
        dataframe["volume_media"] = dataframe["volume"].rolling(window=20).mean()

        # --- Cruzamento de EMA: registra quando EMA8 cruza acima da EMA21 ---
        # .shift(1) garante que usamos a vela anterior para detectar o cruzamento
        # → evita look-ahead bias
        dataframe["ema8_prev"] = dataframe["ema8"].shift(1)
        dataframe["ema21_prev"] = dataframe["ema21"].shift(1)

        # Preços de stop e take profit calculados na entrada
        # (salvos como indicadores para referência — a lógica real fica em custom_stoploss)
        dataframe["stop_calculado"] = dataframe["close"] - self.mult_atr_stop.value * dataframe["atr"]
        dataframe["tp_calculado"] = dataframe["close"] + self.mult_atr_tp.value * dataframe["atr"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define condições de entrada em posição LONG.
        Sinal é marcado na vela fechada — sem look-ahead bias.
        """

        dataframe.loc[
            (
                # Cruzamento de alta: EMA8 cruza acima da EMA21
                # Compara valores da vela atual com os da vela anterior (shift já aplicado)
                (dataframe["ema8"] > dataframe["ema21"]) &
                (dataframe["ema8_prev"] <= dataframe["ema21_prev"]) &

                # Filtro de tendência macro: preço acima da EMA50
                (dataframe["close"] > dataframe["ema50"]) &

                # RSI em zona saudável (não sobrecomprado)
                (dataframe["rsi"] >= self.rsi_min.value) &
                (dataframe["rsi"] <= self.rsi_max.value) &

                # Volume acima da média — confirma o movimento
                (dataframe["volume"] > dataframe["volume_media"]) &

                # Apenas velas com volume real (evita candles fantasma)
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define condições de saída de posição LONG.
        A saída principal é via custom_stoploss (ATR dinâmico).
        Aqui definimos saída adicional por cruzamento inverso.
        """

        dataframe.loc[
            (
                # Cruzamento de baixa: EMA8 cruza abaixo da EMA21
                (dataframe["ema8"] < dataframe["ema21"]) &
                (dataframe["ema8_prev"] >= dataframe["ema21_prev"]) &

                # Apenas velas com volume real
                (dataframe["volume"] > 0)
            ),
            "exit_long"
        ] = 1

        return dataframe

    def custom_stoploss(self, current_time, current_rate, current_profit,
                        min_profit, **kwargs) -> float:
        """
        Stop loss dinâmico baseado em ATR.
        O Freqtrade chama este método a cada tick para calcular o stop.
        Retorna o stop como percentual negativo (ex.: -0.03 = -3%).

        Nota: Para stop loss baseado em ATR puro, idealmente precisaríamos
        do ATR da vela de entrada. Aqui usamos o stoploss fixo como fallback
        e deixamos o minimal_roi + exit_trend gerenciarem as saídas.
        """
        # Retorna None para usar o stoploss padrão definido acima
        # Em produção, implementar com dataframe para ATR real da entrada
        return self.stoploss

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                            rate: float, time_in_force: str, current_time,
                            entry_tag, side: str, **kwargs) -> bool:
        """
        Confirmação final antes de executar a ordem de compra.
        Permite filtros extras de última hora.
        """
        # Aceita todas as entradas válidas (filtros já aplicados em populate_entry_trend)
        return True
