"""
CRUD: Libro y Ejemplar.

Operaciones de base de datos para la gestión de libros y sus
ejemplares (copias físicas).
"""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ejemplar import Ejemplar
from app.models.enums import EstadoEjemplar, EstadoPrestamo, EstadoReserva
from app.models.libro import Libro
from app.schemas.libro import LibroCreate, LibroUpdate


def listar_libros(
    db: Session,
    busqueda: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Libro]:
    """
    Lista los libros del catálogo con filtrado opcional por título o autor.

    Ejecuta una búsqueda case-insensitive con ILIKE. Soporta paginación
    mediante skip y limit.

    Args:
        db: Sesión activa de SQLAlchemy.
        busqueda: Término de búsqueda para filtrar por título o autor.
        skip: Número de registros a omitir (offset).
        limit: Cantidad máxima de registros a devolver.

    Returns:
        Lista de libros que coinciden con los criterios de búsqueda.
    """
    stmt = select(Libro)

    if busqueda:
        patron = f"%{busqueda}%"
        stmt = stmt.where(
            or_(
                Libro.titulo.ilike(patron),
                Libro.autor.ilike(patron),
            )
        )

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def contar_libros(db: Session, busqueda: str | None = None) -> int:
    """
    Cuenta cuántos libros coinciden con el filtro de búsqueda.

    Se usa junto con `listar_libros` para devolver el total al paginar.
    """
    stmt = select(func.count()).select_from(Libro)
    if busqueda:
        patron = f"%{busqueda}%"
        stmt = stmt.where(
            or_(
                Libro.titulo.ilike(patron),
                Libro.autor.ilike(patron),
            )
        )
    return db.execute(stmt).scalar() or 0


def crear_libro(db: Session, datos: LibroCreate) -> Libro:
    """
    Crea un nuevo libro y genera automáticamente sus ejemplares.

    Pasos:
    1. Crea la ficha bibliográfica del libro.
    2. Persiste para obtener el libro.id.
    3. Llama a `agregar_ejemplares()` para crear las copias físicas
       en estado DISPONIBLE.

    Args:
        db: Sesión activa de SQLAlchemy.
        datos: Schema con los datos del libro y la cantidad de ejemplares.

    Returns:
        La instancia del Libro con sus ejemplares ya cargados.
    """
    libro = Libro(
        titulo=datos.titulo,
        autor=datos.autor,
        editorial=datos.editorial,
        anio=datos.anio,
        isbn=datos.isbn,
        categoria_id=datos.categoria_id,
    )
    db.add(libro)
    db.flush()  # Genera el libro.id sin cerrar la transacción

    # Generar los ejemplares solicitados
    agregar_ejemplares(db, libro.id, datos.cantidad_ejemplares)

    db.commit()
    db.refresh(libro)
    return libro


def agregar_ejemplares(db: Session, libro_id: int, cantidad: int) -> list[Ejemplar]:
    """
    Genera 'n' ejemplares en estado DISPONIBLE para un libro existente.

    Cada ejemplar representa una copia física del libro que puede
    ser prestada de forma independiente.

    Args:
        db: Sesión activa de SQLAlchemy.
        libro_id: ID del libro al que pertenecen los ejemplares.
        cantidad: Número de ejemplares a crear.

    Returns:
        Lista de los ejemplares recién creados.
    """
    ejemplares = []
    for _ in range(cantidad):
        ejemplar = Ejemplar(
            libro_id=libro_id,
            estado=EstadoEjemplar.DISPONIBLE,
        )
        db.add(ejemplar)
        ejemplares.append(ejemplar)

    return ejemplares


def obtener_libro_por_id(db: Session, libro_id: int) -> Libro | None:
    """
    Busca un libro por su ID.

    Args:
        db: Sesión activa de SQLAlchemy.
        libro_id: ID del libro a buscar.

    Returns:
        La instancia del Libro si existe, o None.
    """
    return db.get(Libro, libro_id)


def obtener_libro_por_isbn(db: Session, isbn: str) -> Libro | None:
    """
    Busca un libro por su ISBN.

    Se usa para validar la unicidad del ISBN al editar un libro,
    evitando un error de integridad a nivel de base de datos.

    Args:
        db: Sesión activa de SQLAlchemy.
        isbn: ISBN a buscar.

    Returns:
        La instancia del Libro si existe, o None.
    """
    stmt = select(Libro).where(Libro.isbn == isbn)
    return db.execute(stmt).scalar_one_or_none()


def actualizar_libro(db: Session, libro: Libro, datos: LibroUpdate) -> Libro:
    """
    Actualiza los datos de un libro y, si corresponde, ajusta su cantidad
    de ejemplares (copias físicas).

    Realiza una actualización PARCIAL: solo se modifican los campos que
    vienen en `datos` (los no enviados quedan intactos).

    Si `cantidad_ejemplares` viene en `datos`, se interpreta como el TOTAL
    deseado de copias y se delega en `_ajustar_ejemplares()`, que aplica
    las reglas de negocio (no negativo, no eliminar copias prestadas).

    Args:
        db: Sesión activa de SQLAlchemy.
        libro: Instancia del Libro a actualizar (ya cargada).
        datos: Schema con los campos a modificar.

    Returns:
        La instancia del Libro actualizada.

    Raises:
        ValueError: Si se intenta reducir los ejemplares por debajo de lo
                    que las reglas de negocio permiten. La capa API traduce
                    este error a una respuesta HTTP 400.
    """
    cambios = datos.model_dump(exclude_unset=True)
    nueva_cantidad = cambios.pop("cantidad_ejemplares", None)

    # Actualizar los campos bibliográficos enviados
    for campo, valor in cambios.items():
        setattr(libro, campo, valor)

    # Ajustar las copias físicas solo si se pidió un nuevo total
    if nueva_cantidad is not None:
        _ajustar_ejemplares(db, libro, nueva_cantidad)

    db.commit()
    db.refresh(libro)
    return libro


def _ajustar_ejemplares(db: Session, libro: Libro, nueva_cantidad: int) -> None:
    """
    Lleva la cantidad de ejemplares de un libro al total deseado, creando
    o eliminando copias según corresponda.

    Reglas del mundo real aplicadas:
    - Si el nuevo total es MAYOR → se crean ejemplares DISPONIBLE.
    - Si el nuevo total es MENOR → se eliminan ejemplares, pero SOLO los que
      están DISPONIBLE y sin historial de préstamos. Nunca se eliminan copias
      prestadas, en mantenimiento, perdidas o con préstamos asociados (eso
      rompería la integridad referencial y la trazabilidad).
    - El total nunca puede quedar por debajo del mínimo físicamente posible
      (las copias no eliminables), y `cantidad_ejemplares` ya se valida >= 0
      en el schema.

    Args:
        db: Sesión activa de SQLAlchemy.
        libro: Libro cuyas copias se ajustan.
        nueva_cantidad: Total deseado de ejemplares.

    Raises:
        ValueError: Si el nuevo total exige eliminar más copias de las que
                    es posible quitar.
    """
    ejemplares = libro.ejemplares
    actual = len(ejemplares)

    if nueva_cantidad == actual:
        return

    if nueva_cantidad > actual:
        agregar_ejemplares(db, libro.id, nueva_cantidad - actual)
        return

    # ── Reducción: validar qué copias se pueden eliminar ───────────
    a_quitar = actual - nueva_cantidad
    # Solo es seguro eliminar copias DISPONIBLE y sin préstamos en su historial
    removibles = [
        e for e in ejemplares
        if e.estado == EstadoEjemplar.DISPONIBLE and not e.prestamos
    ]

    if a_quitar > len(removibles):
        minimo_posible = actual - len(removibles)
        no_removibles = actual - len(removibles)
        raise ValueError(
            f"No se puede reducir a {nueva_cantidad} ejemplar(es). "
            f"El mínimo posible para este libro es {minimo_posible}, porque "
            f"{no_removibles} copia(s) no se pueden eliminar (están en préstamo, "
            f"en otro estado, o tienen historial de préstamos)."
        )

    for ejemplar in removibles[:a_quitar]:
        db.delete(ejemplar)


def eliminar_libro(db: Session, libro: Libro) -> None:
    """
    Elimina un libro del catálogo junto con sus dependencias, de forma segura.

    Reglas de negocio (si alguna se incumple, NO se elimina nada):
    - No se puede eliminar si tiene préstamos ACTIVOS (algún ejemplar prestado).
    - No se puede eliminar si tiene reservas PENDIENTES.
    - No se puede eliminar si tiene sanciones VIGENTES asociadas a sus préstamos
      (representan una deuda activa que no debe borrarse silenciosamente).

    Si pasa todas las validaciones, elimina en cascada respetando las claves
    foráneas: sanciones → préstamos → reservas → ejemplares → libro.

    Args:
        db: Sesión activa de SQLAlchemy.
        libro: Instancia del Libro a eliminar (ya cargada).

    Raises:
        ValueError: Si el libro tiene obligaciones activas que impiden borrarlo.
                    La capa API traduce este error a una respuesta HTTP 409.
    """
    ejemplares = list(libro.ejemplares)
    prestamos = [p for ejemplar in ejemplares for p in ejemplar.prestamos]
    reservas = list(libro.reservas)

    # ── Regla 1: préstamos activos ─────────────────────────────────
    hay_prestamos_activos = any(
        e.estado == EstadoEjemplar.PRESTADO for e in ejemplares
    ) or any(p.estado == EstadoPrestamo.ACTIVO for p in prestamos)
    if hay_prestamos_activos:
        raise ValueError(
            f"No se puede eliminar '{libro.titulo}' porque tiene préstamos activos. "
            "Primero deben devolverse todos los ejemplares prestados."
        )

    # ── Regla 2: reservas pendientes ───────────────────────────────
    if any(r.estado == EstadoReserva.PENDIENTE for r in reservas):
        raise ValueError(
            f"No se puede eliminar '{libro.titulo}' porque tiene reservas pendientes."
        )

    # ── Regla 3: sanciones vigentes asociadas a sus préstamos ──────
    hoy = date.today()
    sanciones = [p.sancion for p in prestamos if p.sancion is not None]
    if any(s.fecha_fin is None or s.fecha_fin >= hoy for s in sanciones):
        raise ValueError(
            f"No se puede eliminar '{libro.titulo}' porque tiene sanciones vigentes "
            "asociadas a sus préstamos."
        )

    # ── Borrado en cascada (orden seguro según las FK) ─────────────
    for sancion in sanciones:
        db.delete(sancion)
    for prestamo in prestamos:
        db.delete(prestamo)
    for reserva in reservas:
        db.delete(reserva)
    for ejemplar in ejemplares:
        db.delete(ejemplar)
    db.delete(libro)
    db.commit()


def contar_ejemplares_disponibles(db: Session, libro_id: int) -> int:
    """
    Cuenta cuántos ejemplares de un libro están en estado DISPONIBLE.

    Ejecuta un COUNT directo en la BD, más eficiente que cargar
    todos los ejemplares en memoria.

    Args:
        db: Sesión activa de SQLAlchemy.
        libro_id: ID del libro a consultar.

    Returns:
        Número de ejemplares disponibles.
    """
    stmt = (
        select(func.count())
        .select_from(Ejemplar)
        .where(
            Ejemplar.libro_id == libro_id,
            Ejemplar.estado == EstadoEjemplar.DISPONIBLE,
        )
    )
    result = db.execute(stmt).scalar()
    return result or 0


def buscar_ejemplar_disponible(db: Session, libro_id: int) -> Ejemplar | None:
    """
    Busca el primer ejemplar DISPONIBLE de un libro.

    Se usa durante el registro de un préstamo para seleccionar
    qué copia física se va a prestar.

    Args:
        db: Sesión activa de SQLAlchemy.
        libro_id: ID del libro del que se busca un ejemplar libre.

    Returns:
        Un Ejemplar en estado DISPONIBLE, o None si no hay ninguno.
    """
    stmt = (
        select(Ejemplar)
        .where(
            Ejemplar.libro_id == libro_id,
            Ejemplar.estado == EstadoEjemplar.DISPONIBLE,
        )
        .with_for_update()
        .limit(1)
    )
    return db.execute(stmt).scalars().first()
