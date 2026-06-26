"""
CRUD: Sancion.

Operaciones de base de datos para listar y saldar sanciones.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EstadoUsuario
from app.models.sancion import Sancion
from app.models.usuario import Usuario


def es_vigente(sancion: Sancion) -> bool:
    """Una sanción está vigente si no tiene fecha_fin o esta es hoy o futura."""
    return sancion.fecha_fin is None or sancion.fecha_fin >= date.today()


def obtener_sancion(db: Session, sancion_id: int) -> Sancion | None:
    """Busca una sanción por su ID."""
    return db.get(Sancion, sancion_id)


def listar_sanciones(
    db: Session,
    usuario_id: int | None = None,
    solo_vigentes: bool = False,
) -> list[Sancion]:
    """
    Lista sanciones con filtros opcionales.

    Args:
        db: Sesión activa de SQLAlchemy.
        usuario_id: Si se indica, solo las sanciones de ese usuario.
        solo_vigentes: Si es True, excluye las ya saldadas/expiradas.

    Returns:
        Lista de sanciones, de la más reciente a la más antigua.
    """
    stmt = select(Sancion)
    if usuario_id is not None:
        stmt = stmt.where(Sancion.usuario_id == usuario_id)
    if solo_vigentes:
        stmt = stmt.where(
            (Sancion.fecha_fin.is_(None)) | (Sancion.fecha_fin >= date.today())
        )
    stmt = stmt.order_by(Sancion.fecha_inicio.desc())
    return list(db.execute(stmt).scalars().all())


def pagar_sancion(db: Session, sancion: Sancion) -> Sancion:
    """
    Salda una sanción: la da por terminada y reactiva al usuario si ya no
    le quedan sanciones vigentes.

    La sanción se cierra fijando su `fecha_fin` al día de ayer, de modo que
    deje de considerarse vigente (el modelo no tiene un campo de estado/pago
    propio en esta etapa).

    Args:
        db: Sesión activa de SQLAlchemy.
        sancion: La sanción a saldar (ya cargada).

    Returns:
        La sanción actualizada.
    """
    sancion.fecha_fin = date.today() - timedelta(days=1)
    db.flush()

    # Reactivar al usuario si no le quedan sanciones vigentes
    quedan_vigentes = listar_sanciones(db, usuario_id=sancion.usuario_id, solo_vigentes=True)
    if not quedan_vigentes:
        usuario = db.get(Usuario, sancion.usuario_id)
        if usuario and usuario.estado == EstadoUsuario.SANCIONADO:
            usuario.estado = EstadoUsuario.ACTIVO

    db.commit()
    db.refresh(sancion)
    return sancion
