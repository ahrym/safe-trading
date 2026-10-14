#!/usr/bin/env python3
"""Mede velocidade (tokens/s) de cada modelo via gateway.

Serve pra decidir a GPU do PC futuro: rode o mesmo benchmark num pod de
16, 24 e 32 GB e compare.

uso: python3 scripts/benchmark.py qwen3-14b gpt-oss-20b qwen3-30b
     (sem argumentos: testa todos os modelos que o gateway lista)
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

PROMPT = "Explique em 3 parágrafos como funciona um motor a combustão."


def carregar_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for linha in env.read_text().splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def chamar(url, chave, caminho, corpo=None):
    req = urllib.request.Request(
        url + caminho,
        data=json.dumps(corpo).encode() if corpo else None,
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def medir(url, chave, modelo):
    corpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 400,
        "disable_fallbacks": True,  # senão mede o modelo reserva no lugar do pedido
    }
    t0 = time.time()
    chamar(url, chave, "/v1/chat/completions", {**corpo, "max_tokens": 1})  # aquecimento: carrega na VRAM
    carga = time.time() - t0
    t0 = time.time()
    resp = chamar(url, chave, "/v1/chat/completions", corpo)
    dur = time.time() - t0
    tokens = resp["usage"]["completion_tokens"]
    return carga, tokens, dur


def main():
    carregar_env()
    url = os.environ.get("GATEWAY_URL", "http://localhost:4000")
    chave = os.environ["LITELLM_MASTER_KEY"]
    modelos = sys.argv[1:]
    if not modelos:
        apelidos = {"geral", "codigo", "visao", "rapido", "teste"}
        modelos = [m["id"] for m in chamar(url, chave, "/v1/models")["data"] if m["id"] not in apelidos]

    print(f"{'modelo':<22}{'carga (s)':>10}{'tokens':>8}{'tempo (s)':>11}{'tok/s':>8}")
    for m in modelos:
        try:
            carga, tokens, dur = medir(url, chave, m)
            print(f"{m:<22}{carga:>10.1f}{tokens:>8}{dur:>11.1f}{tokens / dur:>8.1f}")
        except Exception as e:  # modelo não baixado no perfil atual, timeout etc.
            print(f"{m:<22}  erro: {e}")


if __name__ == "__main__":
    main()
