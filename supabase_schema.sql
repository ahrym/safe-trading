-- =============================================================================
-- Safe Trading — Schema SQL para Supabase
-- Execute este SQL no painel do Supabase: SQL Editor > New Query
-- =============================================================================

-- Tabela de paper trades (histórico de trades simulados)
create table if not exists paper_trades (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default now(),
  entrada_timestamp text,
  saida_timestamp text,
  preco_entrada numeric,
  preco_saida numeric,
  stop_loss numeric,
  take_profit numeric,
  pnl_usdt numeric,
  retorno_pct numeric,
  resultado text
);

-- Tabela de posição aberta (estado atual do paper trading)
-- Usa id=1 fixo pois só existe uma posição por vez
create table if not exists posicao_aberta (
  id int primary key default 1,
  updated_at timestamp with time zone default now(),
  ativa boolean default false,
  preco_entrada numeric,
  stop_loss numeric,
  take_profit numeric,
  quantidade numeric,
  entrada_timestamp text,
  capital_atual numeric default 1000.0,
  capital_inicial numeric default 1000.0
);

-- Insere linha inicial da posição (sem posição aberta)
insert into posicao_aberta (id, ativa, capital_atual, capital_inicial)
values (1, false, 1000.0, 1000.0)
on conflict (id) do nothing;
