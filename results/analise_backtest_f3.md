# Análise do Backtest — F3.3
## Estratégia: EMA 8/21 + RSI(14) + Volume | BTC/USDT 4H

**Data da análise:** 26/06/2026  
**Analista:** Agente Analista — Safe Trading  
**Arquivo de origem:** `results/backtest_ema_resultado.json`

---

## 1. Resumo Executivo

**Veredicto: REPROVADO PARA WALK-FORWARD — pendente de dados suficientes.**

As métricas individuais são excelentes (Sharpe 2.32, Drawdown 0.89%, Profit Factor 4.12), mas o backtest gerou apenas **6 trades em 5,5 meses** — um volume estatisticamente insuficiente para qualquer conclusão robusta. Esses resultados positivos podem ser ruído puro. O período coberto (jan–jun 2026) é menos da metade do mínimo recomendado pela própria documentação da estratégia (12 meses), e não inclui nenhum ciclo de bear market.

---

## 2. Métricas vs. Critérios de Aprovação

| Métrica | Critério Mínimo | Resultado | Status |
|---|---|---|---|
| Sharpe Ratio | > 1.0 | **2.32** | APROVADO |
| Max Drawdown | < 20% | **0.89%** | APROVADO |
| Profit Factor | > 1.5 | **4.12** | APROVADO |
| Win Rate | Informativo | **66.67% (4/6)** | INFORMATIVO |
| Total de trades | > 30 (doc. estratégia) | **6** | REPROVADO |
| Período de backtest | > 12 meses (doc. estratégia) | **~5.5 meses** | REPROVADO |

**Métricas adicionais do backtest:**

| Métrica | Valor |
|---|---|
| Capital inicial | US$ 1.000,00 |
| Capital final | US$ 1.027,10 |
| Retorno total | +2.71% |
| Média de ganho por trade | +4.42% |
| Média de perda por trade | -2.11% |
| R:R médio realizado | ~2.1:1 |
| Duração média do trade | 16 candles (≈ 64 horas) |

---

## 3. Alertas e Riscos

### Alerta Crítico — Amostra Estatisticamente Inválida

Com **6 trades** em 5,5 meses, qualquer métrica calculada (Sharpe, Profit Factor, Win Rate) carece de significância estatística. A documentação da própria estratégia define o mínimo de **30 trades** para validação — estamos em 20% desse mínimo. Uma sequência de 4 vitórias com 2 derrotas pode ocorrer por acaso mesmo em uma estratégia com expectativa negativa (probabilidade de ~16% assumindo win rate real de 50%).

### Alerta Crítico — Período Incompleto

O backtest cobre apenas **janeiro a junho de 2026**, um período predominantemente de alta (BTC variando de ~$64k a ~$80k nos trades registrados). Não há exposição a:
- Bear market ou queda prolongada
- Alta volatilidade com reversões rápidas
- Mercado lateral com múltiplos falsos cruzamentos de EMA

A estratégia pode estar superestimada por operar em condição favorável.

### Alerta Moderado — Frequência de Sinais Muito Baixa

6 trades em 5,5 meses equivale a **aproximadamente 1 trade por mês**. Isso tem duas implicações:
1. **Operacionalmente:** o capital fica ocioso 99%+ do tempo, com retorno de capital de 2.71% em quase 6 meses — inferior à renda fixa.
2. **Estrategicamente:** os filtros RSI + Volume estão talvez restritivos demais, descartando oportunidades válidas.

### Alerta Leve — Métricas Infladas por Amostra Pequena

O Profit Factor de 4.12 e o Sharpe de 2.32 são números extraordinariamente bons — tão bons que são suspeitos com apenas 6 observações. Estratégias com dezenas ou centenas de trades raramente sustentam Profit Factor acima de 3.0. Com 6 trades, esses valores têm intervalos de confiança extremamente amplos.

### Ponto Positivo — Gestão de Risco Funcionando

A estrutura de risco está operando corretamente: risco por trade de 1%, stop loss dinâmico por ATR, take profit em 3x ATR. O R:R realizado médio de ~2.1:1 está em linha com o alvo de 2:1 definido na estratégia. As perdas foram contidas (-4.96 e -3.71 USDT) e os ganhos foram maiores (+5.99 a +11.81 USDT). Isso é o comportamento esperado.

---

## 4. Recomendação: Próximo Passo

**Não avançar para walk-forward ainda.** Executar as ações abaixo em ordem:

### Ação Prioritária — Ampliar o Período do Backtest

Rodar o backtest no período recomendado pela estratégia: **2022-01-01 a 2026-06-01** (4 anos e meio). Isso deve gerar volume de trades suficiente para validação estatística (>30 trades esperados) e incluirá o bear market de 2022, que é o teste real de qualquer estratégia trend-following em BTC.

O script de backtest já existe no projeto. É necessário apenas ajustar as datas de início e re-executar.

### Ação Secundária — Avaliar Relaxamento dos Filtros (somente após mais dados)

Se mesmo com período estendido o volume de trades for abaixo de 20 por ano, avaliar:
- Ampliar faixa do RSI de 40–65 para 35–70
- Testar sem o filtro de volume (apenas EMA + RSI)
- Comparar resultados

### Decisão de Walk-Forward

O walk-forward deve ser autorizado apenas após:
1. Backtest com período >= 12 meses aprovado
2. Mínimo de 30 trades no período testado
3. Métricas (Sharpe > 1.0, Drawdown < 20%, Profit Factor > 1.5) sustentadas com essa amostra maior

---

## 5. Conclusão para o Orquestrador

Os critérios formais de aprovação (Sharpe, Drawdown, Profit Factor) foram **tecnicamente atingidos**, mas o contexto estatístico invalida qualquer conclusão. Com 6 trades em 5 meses, os números são bonitos mas não dizem nada confiável sobre a estratégia.

**Recomendação ao André:** autorizar a ampliação do período do backtest para 2022–2026 e reavaliar. O código já está funcionando — é apenas uma questão de mudar as datas e rodar novamente. Nenhuma mudança na estratégia é necessária agora.

---

*Relatório gerado em 26/06/2026 pelo Agente Analista — Projeto Safe Trading F3.3*
