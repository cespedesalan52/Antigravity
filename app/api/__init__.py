from fastapi import APIRouter

from app.api.auth import router as router_auth
from app.api.categorias import router as router_categorias
from app.api.libros import router as router_libros
from app.api.prestamos import router as router_prestamos
from app.api.reservas import router as router_reservas
from app.api.sanciones import router as router_sanciones
from app.api.stats import router as router_stats
from app.api.usuarios import router as router_usuarios

api_router = APIRouter()

api_router.include_router(router_auth, prefix="/auth", tags=["Autenticación"])
api_router.include_router(router_usuarios, prefix="/usuarios", tags=["Usuarios"])
api_router.include_router(router_libros, prefix="/libros", tags=["Libros"])
api_router.include_router(router_categorias, prefix="/categorias", tags=["Categorías"])
api_router.include_router(router_prestamos, prefix="/prestamos", tags=["Préstamos y Devoluciones"])
api_router.include_router(router_reservas, prefix="/reservas", tags=["Reservas"])
api_router.include_router(router_sanciones, prefix="/sanciones", tags=["Sanciones"])
api_router.include_router(router_stats, prefix="/stats", tags=["Estadísticas"])
