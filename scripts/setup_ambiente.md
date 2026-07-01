# Setup do Ambiente Safe Trading

## Pré-requisitos

- Windows 10 ou Windows 11
- Python 3.11 ou superior
  - Download: https://www.python.org/downloads/
  - **IMPORTANTE:** Durante a instalação, marque a opção "Add Python to PATH"

---

## Passo 1: Verificar Python

Abra o **Prompt de Comando** (CMD) ou **PowerShell** e execute:

```cmd
python --version
```

Output esperado (versão 3.11 ou superior):
```
Python 3.11.x
```

Se aparecer um erro, o Python não está instalado ou não está no PATH. Reinstale marcando "Add Python to PATH".

---

## Passo 2: Criar ambiente virtual

Navegue até a pasta do projeto e crie o ambiente virtual:

```cmd
cd "C:\Users\user\Claude\Projects\safe trading"
python -m venv venv
```

Ative o ambiente virtual:

```cmd
venv\Scripts\activate
```

Output esperado (o prompt muda para):
```
(venv) C:\Users\user\Claude\Projects\safe trading>
```

> **Dica:** Você precisa ativar o ambiente virtual toda vez que abrir um novo terminal para trabalhar no projeto.

---

## Passo 3: Instalar dependências

Com o ambiente virtual ativado, instale todas as bibliotecas:

```cmd
pip install -r requirements.txt
```

A instalação pode demorar alguns minutos dependendo da sua conexão.

---

## Passo 4: Configurar variáveis de ambiente

Copie o arquivo de exemplo e edite com suas chaves (opcional para dados públicos):

```cmd
copy .env.example .env
```

> **Para começar**, você NÃO precisa de API key. O script de dados usa apenas endpoints públicos da Binance.

---

## Passo 5: Verificar instalação

Execute este comando para confirmar que tudo está funcionando:

```cmd
python -c "import ccxt; import pandas; import pandas_ta; import matplotlib; import mplfinance; print('Todas as bibliotecas instaladas com sucesso!')"
```

Output esperado:
```
Todas as bibliotecas instaladas com sucesso!
```

---

## Passo 6: Testar busca de dados

```cmd
python scripts/fetch_data.py
```

Output esperado:
```
Conectando na Binance...
Buscando 500 candles de BTC/USDT (4h)...
Dados recebidos! Total de candles: 500
Salvando dados em CSV...
Arquivo salvo: data/btc_usdt_4h.csv

--- Últimas 5 linhas ---
[tabela com dados]

--- Estatísticas básicas ---
[resumo estatístico]
```

---

## Passo 7: Gerar gráfico

```cmd
python scripts/visualizar_dados.py
```

Output esperado:
```
Lendo dados do CSV...
Calculando indicadores...
Gerando gráfico...
Gráfico salvo em: data/btc_chart.png
```

---

## Solução de problemas comuns

### Erro: `python` não é reconhecido
**Causa:** Python não está no PATH do Windows.
**Solução:** Reinstale o Python em https://python.org marcando **"Add Python to PATH"**. Ou tente `py` em vez de `python`.

### Erro: `venv\Scripts\activate` não funciona no PowerShell
**Causa:** Política de execução de scripts bloqueada.
**Solução:** Execute no PowerShell como administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Depois tente ativar novamente.

### Erro: `pip install` falha com SSL
**Causa:** Certificado SSL bloqueado por firewall corporativo.
**Solução:**
```cmd
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Erro: `pandas_ta` não importa após instalação
**Causa:** Conflito de versão com pandas 2.x.
**Solução:**
```cmd
pip install pandas-ta --upgrade
```

### Erro de conexão com a Binance
**Causa:** A Binance pode estar com restrições em algumas regiões.
**Solução:** O script tenta reconectar automaticamente. Se persistir, tente usar uma VPN.

### Erro: `No module named 'mplfinance'`
**Causa:** mplfinance não foi instalado.
**Solução:**
```cmd
pip install mplfinance
```

---

## Estrutura de pastas do projeto

```
safe trading/
├── .env                     # Suas chaves (nunca commite este arquivo!)
├── .env.example             # Modelo do .env
├── .gitignore               # Arquivos ignorados pelo git
├── requirements.txt         # Lista de dependências Python
├── scripts/
│   ├── setup_ambiente.md    # Este arquivo de instruções
│   ├── fetch_data.py        # Busca dados históricos da Binance
│   └── visualizar_dados.py  # Gera gráficos de candlestick
└── data/
    ├── btc_usdt_4h.csv      # Dados históricos (gerado pelo fetch_data.py)
    └── btc_chart.png        # Gráfico (gerado pelo visualizar_dados.py)
```
