"""
Schemas Pydantic: Categoria.

Define los modelos de entrada y salida para las categorías de libros.
"""

from pydantic import BaseModel, ConfigDict


# ── Schemas de Entrada ──────────────────────────────────────────

class CategoriaCreate(BaseModel):
    """Datos requeridos para crear una nueva categoría."""

    nombre: str


# ── Schemas de Salida ───────────────────────────────────────────

class CategoriaResponse(BaseModel):
    """Representación de una categoría en las respuestas de la API."""

    id: int
    nombre: str

    # Permite que Pydantic lea atributos de objetos ORM (SQLAlchemy)
    model_config = ConfigDict(from_attributes=True)
