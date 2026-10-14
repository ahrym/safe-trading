# Imagem do pod de GPU (RunPod ou PC local com NVIDIA).
# Ollama escuta só em 127.0.0.1; o Caddy expõe a porta 8080 exigindo
# "Authorization: Bearer $POD_TOKEN" — o Ollama sozinho não tem autenticação.

ARG OLLAMA_VERSION=latest

FROM caddy:2.8.4 AS caddy

FROM ollama/ollama:${OLLAMA_VERSION}

COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY perfis/ /opt/quartel/perfis/
COPY start.sh /opt/quartel/start.sh
RUN chmod +x /opt/quartel/start.sh

# Comportamento parecido com um PC de 1 GPU: um modelo carregado por vez,
# KV cache quantizado pra caber mais contexto na VRAM.
ENV OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_KEEP_ALIVE=30m \
    OLLAMA_FLASH_ATTENTION=1 \
    OLLAMA_KV_CACHE_TYPE=q8_0 \
    OLLAMA_CONTEXT_LENGTH=16384 \
    PORTA=8080 \
    PERFIL=24gb

EXPOSE 8080

ENTRYPOINT ["/opt/quartel/start.sh"]
