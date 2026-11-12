"""Punto de entrada de la API del Asistente Jamar.

Expone los endpoints REST consumidos por el widget web, la Mini App de Telegram
y el bot. La documentación interactiva está disponible en `/docs`.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes import advisor, chat, credit, customers, products, vision
from schemas import HealthResponse
from snowflake_client import get_snowflake_client

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("jamar.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Registra el modo de operación y cierra conexiones al apagar."""
    logger.info(
        "Asistente Jamar iniciado | datos=%s | IA=%s | telegram=%s",
        get_snowflake_client().mode,
        "habilitada" if settings.ai_enabled else "plantillas locales",
        "habilitado" if settings.telegram_enabled else "sin token",
    )
    yield
    get_snowflake_client().close()
    logger.info("Conexiones cerradas correctamente")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Asistente omnicanal de Muebles Jamar: asesoría de interiores, inventario "
        "en tiempo real, análisis visual de espacios y pre-aprobación CrediJamar."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials="*" not in settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(credit.router, prefix="/api")
app.include_router(advisor.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(vision.router, prefix="/api")
app.include_router(customers.router, prefix="/api")


@app.get("/", tags=["Sistema"], summary="Información del servicio")
def root() -> dict:
    """Identificación básica y enlaces útiles de la API."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operativo",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Sistema"], summary="Estado del servicio")
def health() -> HealthResponse:
    """Verifica el estado de datos e IA para monitoreo y healthchecks."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        snowflake_mode=get_snowflake_client().mode,
        ai_enabled=settings.ai_enabled,
        telegram_enabled=settings.telegram_enabled,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )
