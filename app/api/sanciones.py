"""
Router API: Sanciones.

Endpoints para listar y saldar sanciones. Solo personal autorizado.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.crud.sancion import es_vigente, listar_sanciones, obtener_sancion, pagar_sancion
from app.crud.usuario import obtener_usuario_por_dni
from app.models.enums import RolUsuario
from app.models.sancion import Sancion
from app.schemas.sancion import SancionDetalle

router = APIRouter()

_solo_personal = require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR)


def _a_detalle(sancion: Sancion) -> dict:
    """Construye el detalle enriquecido de una sanción a partir del ORM."""
    return {
        "id": sancion.id,
        "usuario_id": sancion.usuario_id,
        "usuario_nombre": f"{sancion.usuario.nombre} {sancion.usuario.apellido}",
        "usuario_dni": sancion.usuario.dni,
        "prestamo_id": sancion.prestamo_id,
        "tipo": sancion.tipo.value,
        "monto": float(sancion.monto),
        "fecha_inicio": sancion.fecha_inicio,
        "fecha_fin": sancion.fecha_fin,
        "vigente": es_vigente(sancion),
    }


@router.get(
    "/",
    response_model=list[SancionDetalle],
    summary="Listar sanciones (con filtros)",
    dependencies=[Depends(_solo_personal)],
)
def listar(
    dni: str | None = Query(None, description="Filtrar por DNI del usuario"),
    solo_vigentes: bool = Query(False, description="Solo sanciones vigentes (sin saldar)"),
    db: Session = Depends(get_db),
):
    """Lista las sanciones del sistema, con filtros opcionales."""
    usuario_id = None
    if dni:
        usuario = obtener_usuario_por_dni(db, dni=dni)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró un usuario con DNI '{dni}'.",
            )
        usuario_id = usuario.id

    sanciones = listar_sanciones(db, usuario_id=usuario_id, solo_vigentes=solo_vigentes)
    return [_a_detalle(s) for s in sanciones]


@router.post(
    "/{sancion_id}/pagar",
    response_model=SancionDetalle,
    summary="Saldar (pagar) una sanción",
    dependencies=[Depends(_solo_personal)],
)
def pagar(sancion_id: int, db: Session = Depends(get_db)):
    """
    Salda una sanción vigente. Si el usuario no queda con otras sanciones
    vigentes, se reactiva automáticamente.
    """
    sancion = obtener_sancion(db, sancion_id)
    if not sancion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sanción no encontrada.",
        )
    if not es_vigente(sancion):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sanción ya está saldada.",
        )

    sancion = pagar_sancion(db, sancion)
    return _a_detalle(sancion)
