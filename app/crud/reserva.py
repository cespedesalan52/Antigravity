"""
CRUD: Reserva.

Operaciones de base de datos para la gestión de reservas de libros.
Una reserva representa que un usuario quiere un libro que ahora mismo no
tiene ejemplares disponibles.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EstadoReserva
from app.models.reserva import Reserva


def obtener_reserva_por_id(db: Session, reserva_id: int) -> Reserva | None:
    """Busca una reserva por su ID."""
    return db.get(Reserva, reserva_id)


def obtener_reserva_pendiente(db: Session, usuario_id: int, libro_id: int) -> Reserva | None:
    """Devuelve la reserva PENDIENTE de un usuario para un libro, si existe."""
    stmt = select(Reserva).where(
        Reserva.usuario_id == usuario_id,
        Reserva.libro_id == libro_id,
        Reserva.estado == EstadoReserva.PENDIENTE,
    )
    return db.execute(stmt).scalar_one_or_none()


def reservas_pendientes_libro(db: Session, libro_id: int) -> list[Reserva]:
    """Lista las reservas PENDIENTES de un libro, de la más antigua a la más nueva."""
    stmt = (
        select(Reserva)
        .where(
            Reserva.libro_id == libro_id,
            Reserva.estado == EstadoReserva.PENDIENTE,
        )
        .order_by(Reserva.fecha_reserva)
    )
    return list(db.execute(stmt).scalars().all())


def listar_reservas(
    db: Session,
    usuario_id: int | None = None,
    estado: EstadoReserva | None = None,
) -> list[Reserva]:
    """Lista reservas con filtros opcionales, de la más reciente a la más antigua."""
    stmt = select(Reserva)
    if usuario_id is not None:
        stmt = stmt.where(Reserva.usuario_id == usuario_id)
    if estado is not None:
        stmt = stmt.where(Reserva.estado == estado)
    stmt = stmt.order_by(Reserva.fecha_reserva.desc())
    return list(db.execute(stmt).scalars().all())


def crear_reserva(db: Session, usuario_id: int, libro_id: int) -> Reserva:
    """Crea una reserva PENDIENTE para un usuario y un libro."""
    reserva = Reserva(
        usuario_id=usuario_id,
        libro_id=libro_id,
        estado=EstadoReserva.PENDIENTE,
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return reserva


def cancelar_reserva(db: Session, reserva: Reserva) -> Reserva:
    """Marca una reserva como CANCELADA."""
    reserva.estado = EstadoReserva.CANCELADA
    db.commit()
    db.refresh(reserva)
    return reserva


def completar_reserva_si_existe(db: Session, usuario_id: int, libro_id: int) -> bool:
    """
    Si el usuario tenía una reserva PENDIENTE para el libro, la marca como
    COMPLETADA (se usa al concretarse el préstamo de ese libro al usuario).

    No hace commit: se confía en el commit de la transacción que la invoca.

    Returns:
        True si se completó una reserva.
    """
    reserva = obtener_reserva_pendiente(db, usuario_id, libro_id)
    if reserva:
        reserva.estado = EstadoReserva.COMPLETADA
        return True
    return False
