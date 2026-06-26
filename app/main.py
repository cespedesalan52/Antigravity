"""
Conocimiento Abierto - Punto de entrada de la aplicación.

Configura la instancia de FastAPI, incluye los routers y
opcionalmente crea las tablas de la base de datos al iniciar.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.limiter import limiter

logger = logging.getLogger("uvicorn.error")

# Carpeta del frontend (raíz_del_proyecto/frontend)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Importar todos los modelos para que SQLAlchemy los registre
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Evento de ciclo de vida de la aplicación.

    Al iniciar:
    - Valida que la configuración de seguridad sea apta para el entorno.
    - Crea todas las tablas en la base de datos si no existen.
      En producción, esto se reemplazaría por migraciones de Alembic.
    """
    if settings.secret_key_insegura:
        aviso = (
            "SECRET_KEY usa el valor de relleno por defecto. Definí una clave "
            "propia y aleatoria en el .env (variable SECRET_KEY)."
        )
        if settings.es_produccion:
            # En producción no se permite arrancar con una clave conocida.
            raise RuntimeError(f"Configuración insegura: {aviso}")
        logger.warning("⚠️  %s", aviso)

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "API REST para el sistema de gestión de biblioteca "
        "'Conocimiento Abierto'. Permite gestionar usuarios, libros, "
        "ejemplares, préstamos, reservas y sanciones."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar CORS restringido a los orígenes permitidos (configurable por
# la variable de entorno ALLOWED_ORIGINS). El frontend se sirve desde la misma
# app, así que normalmente no se necesitan orígenes externos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ───────────────────────────────────────────────
# Limita endpoints sensibles (login/registro) contra fuerza bruta y spam.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _limite_excedido(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiados intentos. Esperá un momento e intentá de nuevo."},
    )


# Incluir los routers de la API
app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de verificación de estado del servicio."""
    return {
        "status": "ok",
        "proyecto": settings.PROJECT_NAME,
        "version": "1.0.0",
    }


# Servir el frontend (HTML/CSS/JS) desde la misma app.
# Debe montarse AL FINAL para que las rutas de la API tengan prioridad.
# html=True hace que "/" devuelva index.html automáticamente.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
