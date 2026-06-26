"""
Router API: Préstamos y Devoluciones.

Endpoints para la lógica de negocio de préstamos y devoluciones de ejemplares.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.crud.prestamo import listar_prestamos, marcar_prestamos_vencidos
from app.crud.usuario import obtener_usuario_por_dni
from app.models.enums import EstadoPrestamo, RolUsuario
from app.models.prestamo import Prestamo
from app.schemas.prestamo import (
    DevolucionCreate,
    DevolucionResponse,
    PrestamoCreate,
    PrestamoDetalle,
    PrestamoResponse,
)
from app.services.prestamo_service import registrar_devolucion, registrar_prestamo

router = APIRouter()

# Las operaciones de préstamo y devolución las realiza el personal de la
# biblioteca en el mostrador, por eso requieren rol BIBLIOTECARIO/ADMINISTRADOR.
_solo_personal = require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR)


def _a_detalle(prestamo: Prestamo) -> dict:
    """Construye el detalle enriquecido de un préstamo a partir del ORM."""
    vencido = prestamo.estado == EstadoPrestamo.VENCIDO
    dias_vencido = (date.today() - prestamo.fecha_vencimiento).days if vencido else 0
    return {
        "id": prestamo.id,
        "usuario_id": prestamo.usuario_id,
        "usuario_nombre": f"{prestamo.usuario.nombre} {prestamo.usuario.apellido}",
        "usuario_dni": prestamo.usuario.dni,
        "libro_id": prestamo.ejemplar.libro_id,
        "libro_titulo": prestamo.ejemplar.libro.titulo,
        "ejemplar_id": prestamo.ejemplar_id,
        "fecha_inicio": prestamo.fecha_inicio,
        "fecha_vencimiento": prestamo.fecha_vencimiento,
        "fecha_devolucion_real": prestamo.fecha_devolucion_real,
        "estado": prestamo.estado,
        "vencido": vencido,
        "dias_vencido": max(dias_vencido, 0),
    }


@router.get(
    "/",
    response_model=list[PrestamoDetalle],
    summary="Listar préstamos (con filtros)",
    dependencies=[Depends(_solo_personal)],
)
def listar(
    estado: str | None = Query(
        None, description="Filtro: 'activos', 'vencidos' o 'devueltos'"
    ),
    dni: str | None = Query(None, description="Filtrar por DNI del usuario"),
    db: Session = Depends(get_db),
):
    """
    Lista los préstamos del sistema, con filtros opcionales por estado y por DNI.

    Antes de listar, marca como VENCIDO los préstamos cuyo plazo ya expiró,
    de modo que el resultado refleje la situación real.
    """
    marcar_prestamos_vencidos(db)

    usuario_id = None
    if dni:
        usuario = obtener_usuario_por_dni(db, dni=dni)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró un usuario con DNI '{dni}'.",
            )
        usuario_id = usuario.id

    prestamos = listar_prestamos(db, estado_filtro=estado, usuario_id=usuario_id)
    return [_a_detalle(p) for p in prestamos]


@router.post(
    "/",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo préstamo",
    dependencies=[Depends(_solo_personal)],
)
def crear_prestamo(datos: PrestamoCreate, db: Session = Depends(get_db)):
    """
    Registra un préstamo de un libro para un usuario.
    
    Aplica todas las reglas de negocio (usuario activo, sin sanciones, ejemplar disponible).
    """
    return registrar_prestamo(db, usuario_id=datos.usuario_id, libro_id=datos.libro_id)


@router.post(
    "/{prestamo_id}/devolucion",
    response_model=DevolucionResponse,
    summary="Registrar la devolución de un ejemplar",
    dependencies=[Depends(_solo_personal)],
)
def realizar_devolucion(prestamo_id: int, datos: DevolucionCreate, db: Session = Depends(get_db)):
    """
    Registra la devolución de un préstamo.
    
    Calcula posibles sanciones si la devolución es tardía y cambia el estado del ejemplar a DISPONIBLE.
    """
    return registrar_devolucion(db, prestamo_id=prestamo_id, fecha_devolucion=datos.fecha_devolucion)
