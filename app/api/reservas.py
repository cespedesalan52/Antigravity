"""
Router API: Reservas.

Permite a un usuario reservar un libro sin ejemplares disponibles, consultar
sus reservas y cancelarlas. El personal puede ver y cancelar todas.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.crud.libro import contar_ejemplares_disponibles, obtener_libro_por_id
from app.crud.reserva import (
    cancelar_reserva,
    crear_reserva,
    listar_reservas,
    obtener_reserva_pendiente,
    obtener_reserva_por_id,
)
from app.crud.usuario import obtener_usuario_por_dni
from app.models.enums import EstadoReserva, RolUsuario
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.schemas.reserva import ReservaCreate, ReservaDetalle

router = APIRouter()

_solo_personal = require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR)


def _a_detalle(reserva: Reserva) -> dict:
    """Construye el detalle enriquecido de una reserva a partir del ORM."""
    return {
        "id": reserva.id,
        "usuario_id": reserva.usuario_id,
        "usuario_nombre": f"{reserva.usuario.nombre} {reserva.usuario.apellido}",
        "usuario_dni": reserva.usuario.dni,
        "libro_id": reserva.libro_id,
        "libro_titulo": reserva.libro.titulo,
        "fecha_reserva": reserva.fecha_reserva,
        "estado": reserva.estado,
    }


def _es_staff(usuario: Usuario) -> bool:
    return usuario.rol in (RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR)


@router.post(
    "/",
    response_model=ReservaDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar un libro sin ejemplares disponibles",
)
def reservar(
    datos: ReservaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Crea una reserva del libro para el usuario autenticado.

    Solo se permite reservar cuando el libro no tiene ejemplares disponibles
    (si los hay, conviene retirarlo en el mostrador). No se puede reservar
    dos veces el mismo libro mientras haya una reserva pendiente.
    """
    libro = obtener_libro_por_id(db, datos.libro_id)
    if not libro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libro no encontrado.",
        )

    if contar_ejemplares_disponibles(db, libro.id) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este libro tiene ejemplares disponibles; no hace falta reservarlo.",
        )

    if obtener_reserva_pendiente(db, usuario.id, libro.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tenés una reserva pendiente para este libro.",
        )

    reserva = crear_reserva(db, usuario_id=usuario.id, libro_id=libro.id)
    return _a_detalle(reserva)


@router.get(
    "/mias",
    response_model=list[ReservaDetalle],
    summary="Listar mis reservas",
)
def mis_reservas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista las reservas del usuario autenticado."""
    reservas = listar_reservas(db, usuario_id=usuario.id)
    return [_a_detalle(r) for r in reservas]


@router.get(
    "/",
    response_model=list[ReservaDetalle],
    summary="Listar todas las reservas (solo personal autorizado)",
    dependencies=[Depends(_solo_personal)],
)
def listar(
    dni: str | None = Query(None, description="Filtrar por DNI del usuario"),
    estado: EstadoReserva | None = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
):
    """Lista todas las reservas, con filtros opcionales por DNI y estado."""
    usuario_id = None
    if dni:
        u = obtener_usuario_por_dni(db, dni=dni)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró un usuario con DNI '{dni}'.",
            )
        usuario_id = u.id

    reservas = listar_reservas(db, usuario_id=usuario_id, estado=estado)
    return [_a_detalle(r) for r in reservas]


@router.post(
    "/{reserva_id}/cancelar",
    response_model=ReservaDetalle,
    summary="Cancelar una reserva",
)
def cancelar(
    reserva_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Cancela una reserva pendiente. El usuario puede cancelar las propias;
    el personal autorizado puede cancelar cualquiera.
    """
    reserva = obtener_reserva_por_id(db, reserva_id)
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada.",
        )

    if reserva.usuario_id != usuario.id and not _es_staff(usuario):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés cancelar una reserva de otro usuario.",
        )

    if reserva.estado != EstadoReserva.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La reserva no está pendiente (estado: {reserva.estado.value}).",
        )

    reserva = cancelar_reserva(db, reserva)
    return _a_detalle(reserva)
