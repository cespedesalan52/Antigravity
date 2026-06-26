"""
Router API: Libros.

Endpoints para la gestión de libros y consulta de disponibilidad.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.enums import RolUsuario
from app.crud.libro import (
    actualizar_libro,
    contar_ejemplares_disponibles,
    contar_libros,
    crear_libro,
    eliminar_libro,
    listar_libros,
    obtener_libro_por_id,
    obtener_libro_por_isbn,
)
from app.schemas.libro import (
    DisponibilidadResponse,
    LibroCreate,
    LibroResponse,
    LibrosPagina,
    LibroUpdate,
)

router = APIRouter()


@router.get(
    "/",
    response_model=LibrosPagina,
    summary="Listar libros del catálogo (paginado)",
)
def listar_catalogo(
    busqueda: str | None = Query(None, description="Filtrar por título o autor"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(50, ge=1, le=100, description="Cantidad máxima de resultados"),
    db: Session = Depends(get_db),
):
    """
    Lista los libros del catálogo con filtrado y paginación.

    Permite buscar por título o autor (case-insensitive). Devuelve el `total`
    de coincidencias junto con los `items` de la página (según skip/limit),
    para que el frontend pueda mostrar contadores y controles de páginas.
    """
    items = listar_libros(db, busqueda=busqueda, skip=skip, limit=limit)
    total = contar_libros(db, busqueda=busqueda)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.post(
    "/",
    response_model=LibroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo libro",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def registrar_libro(datos: LibroCreate, db: Session = Depends(get_db)):
    """
    Registra un libro nuevo y genera sus ejemplares (copias físicas).

    Solo accesible para usuarios con rol BIBLIOTECARIO o ADMINISTRADOR.
    """
    return crear_libro(db, datos=datos)


@router.put(
    "/{libro_id}",
    response_model=LibroResponse,
    summary="Actualizar un libro existente",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def editar_libro(libro_id: int, datos: LibroUpdate, db: Session = Depends(get_db)):
    """
    Actualiza los datos de un libro y/o ajusta su cantidad de ejemplares.

    Solo accesible para usuarios con rol BIBLIOTECARIO o ADMINISTRADOR.

    - La actualización es parcial: solo se modifican los campos enviados.
    - Si se envía `cantidad_ejemplares`, se interpreta como el TOTAL deseado
      de copias; el sistema crea o elimina ejemplares aplicando las reglas de
      negocio (no negativo, no eliminar copias prestadas o con historial).
    """
    libro = obtener_libro_por_id(db, libro_id)
    if not libro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libro no encontrado.",
        )

    # Evitar colisión de ISBN con otro libro distinto
    if datos.isbn is not None and datos.isbn != libro.isbn:
        otro = obtener_libro_por_isbn(db, datos.isbn)
        if otro and otro.id != libro.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ISBN ya está registrado en otro libro.",
            )

    try:
        return actualizar_libro(db, libro, datos)
    except ValueError as exc:
        # Regla de negocio violada (p. ej. reducir ejemplares por debajo del mínimo)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "/{libro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un libro del catálogo",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def borrar_libro(libro_id: int, db: Session = Depends(get_db)):
    """
    Elimina un libro del catálogo de forma segura.

    Solo accesible para usuarios con rol BIBLIOTECARIO o ADMINISTRADOR.

    No se permite eliminar si el libro tiene préstamos activos, reservas
    pendientes o sanciones vigentes. En esos casos devuelve 409 con el motivo.
    Si está libre de obligaciones, elimina el libro y sus dependencias.
    """
    libro = obtener_libro_por_id(db, libro_id)
    if not libro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libro no encontrado.",
        )

    try:
        eliminar_libro(db, libro)
    except ValueError as exc:
        # El libro tiene obligaciones activas que impiden su eliminación
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get(
    "/{libro_id}/disponibilidad",
    response_model=DisponibilidadResponse,
    summary="Consultar disponibilidad de un libro",
)
def consultar_disponibilidad(libro_id: int, db: Session = Depends(get_db)):
    """
    Devuelve la cantidad de ejemplares disponibles para préstamo de un libro.
    """
    libro = obtener_libro_por_id(db, libro_id)
    if not libro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libro no encontrado.",
        )
    
    disponibles = contar_ejemplares_disponibles(db, libro_id)
    return {
        "libro_id": libro.id,
        "titulo": libro.titulo,
        "isbn": libro.isbn,
        "total_ejemplares": len(libro.ejemplares),
        "ejemplares_disponibles": disponibles,
    }
