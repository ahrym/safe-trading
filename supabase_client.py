# =============================================================================
# Safe Trading — Cliente Supabase com fallback para JSON local
# Se SUPABASE_URL e SUPABASE_KEY estiverem configurados, usa Supabase.
# Caso contrário, persiste dados em results/paper_trades.json (dev local).
# =============================================================================

import json
import os
from datetime import datetime, timezone

# Diretório base do projeto
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_RESULTS = os.path.join(DIRETORIO_BASE, "results")

# Caminhos dos arquivos JSON locais (fallback)
CAMINHO_PAPER_TRADES = os.path.join(DIRETORIO_RESULTS, "paper_trades.json")
CAMINHO_POSICAO = os.path.join(DIRETORIO_RESULTS, "posicao_aberta.json")

# Verifica se as credenciais do Supabase estão configuradas
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
USAR_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Inicializa cliente Supabase (apenas se configurado)
_supabase = None
if USAR_SUPABASE:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[Supabase] Conectado: {SUPABASE_URL[:40]}...")
    except Exception as e:
        print(f"[Supabase] Erro ao conectar: {e} — usando fallback JSON local")
        USAR_SUPABASE = False
else:
    print("[Supabase] Variáveis não configuradas — usando fallback JSON local")


# =============================================================================
# FUNÇÕES AUXILIARES LOCAIS
# =============================================================================

def _ler_json(caminho, fallback=None):
    """Lê arquivo JSON com fallback gracioso."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback if fallback is not None else {}


def _salvar_json(caminho, dados):
    """Salva dados em arquivo JSON."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False, default=str)


# =============================================================================
# FUNÇÕES PÚBLICAS — PAPER TRADES
# =============================================================================

def salvar_paper_trade(trade_dict: dict) -> bool:
    """
    Salva um trade paper finalizado.
    trade_dict deve conter: entrada_timestamp, saida_timestamp, preco_entrada,
    preco_saida, stop_loss, take_profit, pnl_usdt, retorno_pct, resultado
    """
    if USAR_SUPABASE and _supabase:
        try:
            _supabase.table("paper_trades").insert(trade_dict).execute()
            print(f"[Supabase] Trade salvo: {trade_dict.get('resultado', '?')}")
            return True
        except Exception as e:
            print(f"[Supabase] Erro ao salvar trade: {e} — usando JSON local")

    # Fallback local: adiciona ao arquivo JSON existente
    estado = _ler_json(
        CAMINHO_PAPER_TRADES,
        fallback={"capital_inicial": 1000.0, "capital_atual": 1000.0, "posicao_aberta": None, "trades": []}
    )
    estado.setdefault("trades", []).append(trade_dict)
    _salvar_json(CAMINHO_PAPER_TRADES, estado)
    return True


def listar_paper_trades() -> list:
    """
    Retorna lista de todos os trades paper registrados.
    """
    if USAR_SUPABASE and _supabase:
        try:
            resp = _supabase.table("paper_trades").select("*").order("created_at").execute()
            return resp.data or []
        except Exception as e:
            print(f"[Supabase] Erro ao listar trades: {e} — usando JSON local")

    # Fallback local
    estado = _ler_json(CAMINHO_PAPER_TRADES, fallback={"trades": []})
    return estado.get("trades", [])


# =============================================================================
# FUNÇÕES PÚBLICAS — POSIÇÃO ABERTA
# =============================================================================

def salvar_posicao_aberta(posicao: dict) -> bool:
    """
    Salva o estado da posição aberta (ou ausência de posição).
    posicao: dict com campos da posição, ou None para fechar posição.
    """
    if USAR_SUPABASE and _supabase:
        try:
            dados = {
                "id": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "ativa": posicao is not None and posicao.get("ativa", False),
                "preco_entrada": posicao.get("entrada") if posicao else None,
                "stop_loss": posicao.get("stop") if posicao else None,
                "take_profit": posicao.get("tp") if posicao else None,
                "entrada_timestamp": posicao.get("timestamp") if posicao else None,
                "capital_atual": posicao.get("capital_atual") if posicao else None,
            }
            _supabase.table("posicao_aberta").upsert(dados).execute()
            return True
        except Exception as e:
            print(f"[Supabase] Erro ao salvar posição: {e} — usando JSON local")

    # Fallback local
    _salvar_json(CAMINHO_POSICAO, posicao or {})
    return True


def ler_posicao_aberta() -> dict | None:
    """
    Lê o estado atual da posição aberta.
    Retorna dict com a posição ou None se não há posição aberta.
    """
    if USAR_SUPABASE and _supabase:
        try:
            resp = _supabase.table("posicao_aberta").select("*").eq("id", 1).execute()
            if resp.data:
                linha = resp.data[0]
                if linha.get("ativa"):
                    return {
                        "entrada": linha.get("preco_entrada"),
                        "stop": linha.get("stop_loss"),
                        "tp": linha.get("take_profit"),
                        "timestamp": linha.get("entrada_timestamp"),
                        "capital_atual": linha.get("capital_atual", 1000.0),
                    }
            return None
        except Exception as e:
            print(f"[Supabase] Erro ao ler posição: {e} — usando JSON local")

    # Fallback local
    dados = _ler_json(CAMINHO_POSICAO, fallback=None)
    return dados if dados else None


def ler_capital_atual() -> float:
    """Retorna o capital atual do paper trading."""
    if USAR_SUPABASE and _supabase:
        try:
            resp = _supabase.table("posicao_aberta").select("capital_atual, capital_inicial").eq("id", 1).execute()
            if resp.data:
                return float(resp.data[0].get("capital_atual", 1000.0))
        except Exception:
            pass

    # Fallback local
    estado = _ler_json(CAMINHO_PAPER_TRADES, fallback={"capital_atual": 1000.0})
    return float(estado.get("capital_atual", 1000.0))
