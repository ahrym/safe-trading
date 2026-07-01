# Dockerfile para deploy do Freqtrade no Railway
# Baseado na imagem oficial estável do Freqtrade
FROM freqtradeorg/freqtrade:stable

# Cria diretórios necessários para dados, logs e resultados de backtest
RUN mkdir -p /freqtrade/user_data/data \
             /freqtrade/user_data/logs \
             /freqtrade/user_data/backtest_results \
             /freqtrade/user_data/strategies

# Copia configuração principal
COPY config.json /freqtrade/config.json

# Copia estratégias para o diretório padrão do Freqtrade
COPY strategies/ /freqtrade/user_data/strategies/

# Expõe a porta da API REST do Freqtrade
EXPOSE 8081

# Comando de inicialização: modo trade com a estratégia EMAClassica
CMD ["freqtrade", "trade", "--config", "/freqtrade/config.json", "--strategy", "EMAClassica"]
