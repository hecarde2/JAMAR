@echo off
setlocal enabledelayedexpansion
title Asistente Jamar - Inicio rapido
cd /d "%~dp0"

echo ============================================================
echo  Asistente de IA Omnicanal - Muebles Jamar
echo  Inicio rapido con Docker
echo ============================================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker no esta instalado o no esta en el PATH.
  echo         Descarga Docker Desktop: https://docs.docker.com/get-docker/
  pause
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker Desktop no esta activo.
  echo         Abre Docker Desktop, espera a que inicie y vuelve a ejecutar este script.
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [INFO] Archivo .env creado a partir de .env.example
)

findstr /B /C:"TELEGRAM_BOT_TOKEN=" .env | findstr /R /C:"TELEGRAM_BOT_TOKEN=..*" >nul
if errorlevel 1 echo [AVISO] TELEGRAM_BOT_TOKEN vacio: el bot quedara activo sin conexion.
findstr /B /C:"GEMINI_API_KEY=" .env | findstr /R /C:"GEMINI_API_KEY=..*" >nul
if errorlevel 1 echo [AVISO] GEMINI_API_KEY vacio: el agente usara plantillas locales.
findstr /B /C:"SNOWFLAKE_ACCOUNT=" .env | findstr /R /C:"SNOWFLAKE_ACCOUNT=..*" >nul
if errorlevel 1 echo [AVISO] Snowflake sin configurar: se usara el catalogo de demostracion.

set "COMPOSE=docker compose"
docker compose version >nul 2>nul
if errorlevel 1 (
  where docker-compose >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Docker Compose no esta disponible.
    echo         Instala el plugin oficial de Docker Compose.
    pause
    exit /b 1
  )
  set "COMPOSE=docker-compose"
  echo [AVISO] Se usara docker-compose v1. Se recomienda Docker Compose v2.
)

echo.
echo [INFO] Compilando imagenes y levantando servicios...
%COMPOSE% up --build -d
if errorlevel 1 (
  echo [ERROR] No fue posible iniciar los servicios.
  echo         Revisa los logs con: %COMPOSE% logs backend
  pause
  exit /b 1
)

echo.
echo [INFO] Esperando backend...
timeout /t 8 /nobreak >nul

echo.
echo ============================================================
echo  Asistente Jamar en ejecucion
echo ============================================================
echo   Frontend / Widget : http://localhost:3000
echo   Widget embebible  : http://localhost:3000/?embed=1
echo   API y Swagger     : http://localhost:8000/docs
echo   Salud del backend : http://localhost:8000/api/health
echo   Telegram Mini App : configura PUBLIC_WEBAPP_URL con una URL publica
echo.
echo   Logs:    %COMPOSE% logs -f
echo   Detener: %COMPOSE% down
echo ============================================================
echo.
pause
