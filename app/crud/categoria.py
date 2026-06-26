"""
CRUD: Categoria.

Operaciones de base de datos para la gestión de categorías de libros.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.categoria import Categoria
from app.schemas.categoria import CategoriaCreate


def listar_categorias(db: Session) -> list[Categoria]:
    """Devuelve todas las categorías ordenadas por nombre."""
    stmt = select(Categoria).order_by(Categoria.nombre)
    return list(db.execute(stmt).scalars().all())


def obtener_categoria_por_nombre(db: Session, nombre: str) -> Categoria | None:
    """Busca una categoría por su nombre (para validar unicidad)."""
    stmt = select(Categoria).where(Categoria.nombre == nombre)
    return db.execute(stmt).scalar_one_or_none()


def crear_categoria(db: Session, datos: CategoriaCreate) -> Categoria:
    """Crea una nueva categoría."""
    categoria = Categoria(nombre=datos.nombre)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria
