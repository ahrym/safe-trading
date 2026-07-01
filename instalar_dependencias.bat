@echo off
echo ============================================
echo  Safe Trading - Instalando dependencias
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando Python...
python --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale em python.org
    pause
    exit /b 1
)

echo.
echo [2/3] Instalando bibliotecas...
python -m pip install --upgrade pip
python -m pip install ccxt pandas matplotlib mplfinance numpy python-dotenv

echo.
echo [3/3] Verificando instalacao...
python -c "import ccxt; import pandas; import matplotlib; import mplfinance; import numpy; print('Tudo instalado com sucesso!')"

echo.
echo ============================================
echo  Rodando o backtest...
echo ============================================
echo.
python scripts/backtest.py

echo.
pause
