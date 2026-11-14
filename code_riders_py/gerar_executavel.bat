@echo off
REM ============================================================
REM  Gera o PedalHub.exe (roda em qualquer Windows, sem Python)
REM  Basta dar dois cliques neste arquivo.
REM  So o computador que GERA o .exe precisa ter Python.
REM ============================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao encontrado.
    echo Instale pelo site python.org marcando "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo.
echo === 1/2 Instalando o PyInstaller ===
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto erro

echo.
echo === 2/2 Gerando o executavel (leva 1 ou 2 minutos) ===
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name PedalHub --icon pedalhub.ico --add-data "pedalhub.ico;." app_gui.py
if errorlevel 1 goto erro

echo.
echo ============================================================
echo  Pronto! O executavel esta em:  dist\PedalHub.exe
echo  Pode copiar so esse arquivo para qualquer computador.
echo ============================================================
explorer dist
pause
exit /b 0

:erro
echo.
echo [ERRO] Algo deu errado. Veja as mensagens acima.
pause
exit /b 1
