# =============================================================================
# Safe Trading Dashboard — Dockerfile
# Imagem base Python 3.11 slim para manter o container leve
# =============================================================================

FROM python:3.11-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências primeiro (otimiza cache de camadas)
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto
COPY . .

# Cria diretórios necessários para o app
RUN mkdir -p /app/results /app/data

# Railway injeta PORT automaticamente — expõe a porta configurada
EXPOSE 8050

# Comando de inicialização
CMD ["python", "dashboard.py"]
