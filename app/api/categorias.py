"""
Router API: Categorías.

Listado público (para poblar selectores) y creación restringida a personal.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.crud.categoria import crear_categoria, listar_categorias, obtener_categoria_por_nombre
from app.models.enums import RolUsuario
from app.schemas.categoria import CategoriaCreate, CategoriaResponse

router = APIRouter()


@router.get(
    "/",
    response_model=list[CategoriaResponse],
    summary="Listar categorías",
)
def listar(db: Session = Depends(get_db)):
    """Lista todas las categorías (se usa para poblar los selectores del catálogo)."""
    return listar_categorias(db)


@router.post(
    "/",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva categoría (solo personal autorizado)",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def crear(datos: CategoriaCreate, db: Session = Depends(get_db)):
    """Crea una categoría nueva. El nombre debe ser único."""
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de la categoría no puede estar vacío.",
        )
    if obtener_categoria_por_nombre(db, nombre):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una categoría llamada '{nombre}'.",
        )
    return crear_categoria(db, CategoriaCreate(nombre=nombre))
