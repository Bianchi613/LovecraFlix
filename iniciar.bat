@echo off
chcp 65001 >nul
echo.
echo  ██╗      ██████╗ ██╗   ██╗███████╗ ██████╗██████╗  █████╗ ███████╗██╗     ██╗██╗  ██╗
echo  ██║     ██╔═══██╗██║   ██║██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║     ██║╚██╗██╔╝
echo  ██║     ██║   ██║╚██╗ ██╔╝█████╗  ██║     ██████╔╝███████║█████╗  ██║     ██║ ╚███╔╝
echo  ██║     ██║   ██║ ╚████╔╝ ██╔══╝  ██║     ██╔══██╗██╔══██║██╔══╝  ██║     ██║ ██╔██╗
echo  ███████╗╚██████╔╝  ╚██╔╝  ███████╗╚██████╗██║  ██║██║  ██║██║     ███████╗██║██╔╝ ██╗
echo  ╚══════╝ ╚═════╝    ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝
echo.

cd /d "%~dp0backend"

REM -- Verifica se o setup já foi feito (config.json existe na raiz)
if not exist "%~dp0config.json" (
    echo  Parece que e a primeira vez que voce executa o LovecraFlix!
    echo  Vamos fazer a configuracao inicial...
    echo.
    python setup.py
    if errorlevel 1 (
        echo.
        echo  ERRO no setup. Verifique se o Python esta instalado.
        pause
        exit /b 1
    )
    echo.
)

echo  Iniciando servidor...
echo  Acesse: http://localhost:8000
echo.
python app.py
pause
