#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Inicio rápido del Asistente de IA Omnicanal - Muebles Jamar
# Compatible con Linux y macOS. Requiere Docker + Docker Compose v2.
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")"

GREEN="\033[0;32m"
GOLD="\033[0;33m"
RED="\033[0;31m"
DIM="\033[2m"
RESET="\033[0m"

info() { printf "${GREEN}[JAMAR]${RESET} %s\n" "$1"; }
warn() { printf "${GOLD}[AVISO]${RESET} %s\n" "$1"; }
error() { printf "${RED}[ERROR]${RESET} %s\n" "$1" >&2; }

env_value() {
  local key="$1"
  if [ -f .env ]; then
    grep -E "^${key}=" .env 2>/dev/null | tail -n 1 | cut -d '=' -f 2- | tr -d '\r' || true
  fi
}

# --- 1. Validar Docker -------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  error "Docker no está instalado. Descárgalo en https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  error "El daemon de Docker no está activo. Inicia Docker Desktop o el servicio docker."
  exit 1
fi

COMPOSE=()
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
  warn "Se usará docker-compose (v1). Se recomienda Docker Compose v2."
else
  error "Docker Compose no está disponible. Instala el plugin oficial de Compose."
  exit 1
fi

# --- 2. Preparar entorno -----------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  info "Archivo .env creado a partir de .env.example"
fi

chmod +x start.sh 2>/dev/null || true

FRONTEND_PORT="$(env_value FRONTEND_PORT)"; FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="$(env_value BACKEND_PORT)"; BACKEND_PORT="${BACKEND_PORT:-8000}"

if ! grep -Eq '^TELEGRAM_BOT_TOKEN=.+' .env 2>/dev/null; then
  warn "TELEGRAM_BOT_TOKEN vacío: el contenedor del bot quedará activo sin conexión."
fi
if ! grep -Eq '^GEMINI_API_KEY=.+' .env 2>/dev/null; then
  warn "GEMINI_API_KEY vacío: el agente usará plantillas locales (modo demostración)."
fi
if ! grep -Eq '^SNOWFLAKE_ACCOUNT=.+' .env 2>/dev/null; then
  warn "Snowflake sin configurar: se usará el catálogo de demostración."
fi

# --- 3. Compilar y arrancar --------------------------------------------------
info "Compilando imágenes y levantando servicios..."
"${COMPOSE[@]}" up --build -d

# --- 4. Esperar disponibilidad ----------------------------------------------
info "Esperando que el backend esté saludable..."
HEALTHY=0
for _ in $(seq 1 45); do
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
      HEALTHY=1
      break
    fi
  else
    if "${COMPOSE[@]}" ps --services --filter status=running 2>/dev/null | grep -q backend; then
      HEALTHY=1
      break
    fi
  fi
  sleep 2
done

if [ "$HEALTHY" -eq 1 ]; then
  info "Backend operativo."
else
  warn "El backend aún no responde. Revisa los logs con: ${COMPOSE[*]} logs -f backend"
fi

printf "\n${GREEN}============================================================${RESET}\n"
printf "${GREEN} Asistente Jamar en ejecución${RESET}\n"
printf "${GREEN}============================================================${RESET}\n"
printf "  Frontend / Widget : http://localhost:%s\n" "$FRONTEND_PORT"
printf "  Widget embebible : http://localhost:%s/?embed=1\n" "$FRONTEND_PORT"
printf "  API y Swagger     : http://localhost:%s/docs\n" "$BACKEND_PORT"
printf "  Salud del backend : http://localhost:%s/api/health\n" "$BACKEND_PORT"
printf "  Telegram Mini App : configura PUBLIC_WEBAPP_URL con una URL pública\n"
printf "\n${DIM}  Logs: %s logs -f\n  Detener: %s down\n${RESET}\n" "${COMPOSE[*]}" "${COMPOSE[*]}"
