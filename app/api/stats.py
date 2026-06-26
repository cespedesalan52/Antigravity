"""
Router API: Estadísticas.

Métricas globales de la biblioteca para el panel de control. Disponible
para cualquier usuario autenticado.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud.prestamo import marcar_prestamos_vencidos
from app.models.ejemplar import Ejemplar
from app.models.enums import EstadoEjemplar, EstadoPrestamo, EstadoReserva
from app.models.libro import Libro
from app.models.prestamo import Prestamo
from app.models.reserva import Reserva
from app.models.sancion import Sancion
from app.models.usuario import Usuario  # noqa: F401  (registro del modelo)
from app.schemas.stats import StatsResponse

router = APIRouter()


def _contar(db: Session, modelo, *condiciones) -> int:
    stmt = select(func.count()).select_from(modelo)
    for cond in condiciones:
        stmt = stmt.where(cond)
    return db.execute(stmt).scalar() or 0


@router.get(
    "/",
    response_model=StatsResponse,
    summary="Métricas globales de la biblioteca",
    dependencies=[Depends(get_current_user)],
)
def estadisticas(db: Session = Depends(get_db)):
    """Devuelve los contadores globales del sistema para el dashboard."""
    # Asegura que los préstamos vencidos estén marcados antes de contarlos.
    marcar_prestamos_vencidos(db)

    return {
        "total_libros": _contar(db, Libro),
        "total_ejemplares": _contar(db, Ejemplar),
        "ejemplares_disponibles": _contar(db, Ejemplar, Ejemplar.estado == EstadoEjemplar.DISPONIBLE),
        "ejemplares_prestados": _contar(db, Ejemplar, Ejemplar.estado == EstadoEjemplar.PRESTADO),
        "prestamos_activos": _contar(
            db, Prestamo, Prestamo.estado.in_((EstadoPrestamo.ACTIVO, EstadoPrestamo.VENCIDO))
        ),
        "prestamos_vencidos": _contar(db, Prestamo, Prestamo.estado == EstadoPrestamo.VENCIDO),
        "sanciones_vigentes": _contar(
            db, Sancion, (Sancion.fecha_fin.is_(None)) | (Sancion.fecha_fin >= date.today())
        ),
        "reservas_pendientes": _contar(db, Reserva, Reserva.estado == EstadoReserva.PENDIENTE),
    }
