@echo off
REM ============================================================
REM  Conocimiento Abierto - Arranque rapido para compartir
REM  Abre dos ventanas: el backend (uvicorn) y el tunel (cloudflared).
REM  Se ubica solo en la carpeta del proyecto (%~dp0), no importa
REM  desde donde lo ejecutes.
REM ============================================================

cd /d "%~dp0"

echo Iniciando el backend (uvicorn) en el puerto 8000...
start "Conocimiento Abierto - Backend (uvicorn)" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload"

echo Esperando unos segundos a que levante el backend...
timeout /t 5 /nobreak >nul

echo Iniciando el tunel de Cloudflare...
start "Conocimiento Abierto - Tunel (cloudflared)" cmd /k "cloudflared.exe tunnel --url http://localhost:8000"

echo.
echo ============================================================
echo  Listo. Se abrieron dos ventanas:
echo   1) Backend (uvicorn)   -> dejala abierta
echo   2) Tunel (cloudflared) -> ahi aparece la URL para compartir
echo.
echo  Busca en la ventana del tunel la linea:
echo    https://algo-aleatorio.trycloudflare.com
echo  Ese es el link que les pasas a tus companeros.
echo ============================================================
echo.
pause
