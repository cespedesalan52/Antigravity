"""
CRUD: Prestamo.

Operaciones de base de datos para la gestión de préstamos.
Las operaciones de "alto nivel" (validaciones, sanciones) están
en app/services/prestamo_service.py. Este módulo se enfoca
exclusivamente en la interacción directa con la BD.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import EstadoPrestamo, EstadoUsuario
from app.models.prestamo import Prestamo
from app.models.sancion import Sancion
from app.models.usuario import Usuario

# Un préstamo se considera "en curso" (el ejemplar sigue afuera) mientras
# esté ACTIVO o VENCIDO. Solo deja de estarlo cuando pasa a DEVUELTO.
ESTADOS_EN_CURSO = (EstadoPrestamo.ACTIVO, EstadoPrestamo.VENCIDO)


def marcar_prestamos_vencidos(db: Session) -> int:
    """
    Marca como VENCIDO los préstamos ACTIVO cuya fecha de vencimiento ya pasó.

    Se invoca de forma perezosa al listar préstamos (no hay un scheduler),
    de modo que el estado refleje la realidad cada vez que se consulta.

    Returns:
        Cantidad de préstamos que cambiaron a VENCIDO.
    """
    stmt = select(Prestamo).where(
        Prestamo.estado == EstadoPrestamo.ACTIVO,
        Prestamo.fecha_vencimiento < date.today(),
    )
    vencidos = list(db.execute(stmt).scalars().all())
    for prestamo in vencidos:
        prestamo.estado = EstadoPrestamo.VENCIDO
    if vencidos:
        db.commit()
    return len(vencidos)


def listar_prestamos(
    db: Session,
    estado_filtro: str | None = None,
    usuario_id: int | None = None,
) -> list[Prestamo]:
    """
    Lista préstamos con filtros opcionales.

    Args:
        db: Sesión activa de SQLAlchemy.
        estado_filtro: "activos" (ACTIVO+VENCIDO), "vencidos", "devueltos",
                       o None para todos.
        usuario_id: Si se indica, solo los préstamos de ese usuario.

    Returns:
        Lista de préstamos ordenados por fecha de vencimiento.
    """
    stmt = select(Prestamo)
    if usuario_id is not None:
        stmt = stmt.where(Prestamo.usuario_id == usuario_id)

    if estado_filtro == "activos":
        stmt = stmt.where(Prestamo.estado.in_(ESTADOS_EN_CURSO))
    elif estado_filtro == "vencidos":
        stmt = stmt.where(Prestamo.estado == EstadoPrestamo.VENCIDO)
    elif estado_filtro == "devueltos":
        stmt = stmt.where(Prestamo.estado == EstadoPrestamo.DEVUELTO)

    stmt = stmt.order_by(Prestamo.fecha_vencimiento)
    return list(db.execute(stmt).scalars().all())


def contar_prestamos_activos(db: Session, usuario_id: int) -> int:
    """Cuenta los préstamos en curso (ACTIVO o VENCIDO) de un usuario."""
    stmt = (
        select(func.count())
        .select_from(Prestamo)
        .where(
            Prestamo.usuario_id == usuario_id,
            Prestamo.estado.in_(ESTADOS_EN_CURSO),
        )
    )
    return db.execute(stmt).scalar() or 0


def obtener_prestamo_por_id(db: Session, prestamo_id: int) -> Prestamo | None:
    """
    Busca un préstamo por su ID.

    Args:
        db: Sesión activa de SQLAlchemy.
        prestamo_id: ID del préstamo a buscar.

    Returns:
        La instancia del Prestamo si existe, o None.
    """
    return db.get(Prestamo, prestamo_id)


def obtener_prestamos_activos_usuario(db: Session, usuario_id: int) -> list[Prestamo]:
    """
    Obtiene todos los préstamos activos de un usuario.

    Args:
        db: Sesión activa de SQLAlchemy.
        usuario_id: ID del usuario.

    Returns:
        Lista de préstamos en curso (ACTIVO o VENCIDO) del usuario.
    """
    stmt = select(Prestamo).where(
        Prestamo.usuario_id == usuario_id,
        Prestamo.estado.in_(ESTADOS_EN_CURSO),
    )
    return list(db.execute(stmt).scalars().all())


def tiene_sanciones_vigentes(db: Session, usuario_id: int) -> bool:
    """
    Verifica si un usuario tiene sanciones vigentes (sin fecha_fin
    o con fecha_fin futura).

    Se usa como validación antes de permitir un nuevo préstamo.

    Args:
        db: Sesión activa de SQLAlchemy.
        usuario_id: ID del usuario a verificar.

    Returns:
        True si el usuario tiene al menos una sanción vigente.
    """
    from datetime import date

    stmt = select(Sancion).where(
        Sancion.usuario_id == usuario_id,
        # Sanción vigente: sin fecha_fin o con fecha_fin >= hoy
        (Sancion.fecha_fin.is_(None)) | (Sancion.fecha_fin >= date.today()),
    )
    result = db.execute(stmt).first()
    
    tiene_vigentes = result is not None
    
    # Autoreactivación si no tiene sanciones vigentes
    if not tiene_vigentes:
        usuario = db.get(Usuario, usuario_id)
        if usuario and usuario.estado == EstadoUsuario.SANCIONADO:
            usuario.estado = EstadoUsuario.ACTIVO
            db.commit()
            
    return tiene_vigentes
