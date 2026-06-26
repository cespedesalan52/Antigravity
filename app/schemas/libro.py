"""
Schemas Pydantic: Libro.

Define los modelos de entrada y salida para los libros,
incluyendo la cantidad de ejemplares a generar al crear uno nuevo.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.categoria import CategoriaResponse
from app.schemas.ejemplar import EjemplarResponse


# ── Schemas de Entrada ──────────────────────────────────────────

class LibroCreate(BaseModel):
    """
    Datos para registrar un nuevo libro en el sistema.

    - `cantidad_ejemplares`: número de copias físicas a crear
      automáticamente en estado DISPONIBLE (por defecto 1).
    - `categoria_id`: FK opcional hacia la categoría.
    """

    titulo: str
    autor: str
    editorial: str | None = None
    anio: int | None = None
    isbn: str
    categoria_id: int | None = None
    cantidad_ejemplares: int = Field(default=1, ge=1)  # copias a crear; nunca menos de 1


class LibroUpdate(BaseModel):
    """
    Datos para actualizar un libro existente (actualización parcial).

    Todos los campos son opcionales: solo se modifican los que se envían
    (se usa `exclude_unset` en el CRUD para distinguir "no enviado" de "null").

    - `cantidad_ejemplares`: si se envía, representa el TOTAL deseado de
      copias físicas del libro (no un incremento). El sistema crea o elimina
      ejemplares para alcanzar ese total, respetando que no puede ser negativo
      ni eliminar copias prestadas. Mínimo 0.
    """

    titulo: str | None = None
    autor: str | None = None
    editorial: str | None = None
    anio: int | None = None
    isbn: str | None = None
    categoria_id: int | None = None
    cantidad_ejemplares: int | None = Field(default=None, ge=0)


# ── Schemas de Salida ───────────────────────────────────────────

class LibroResponse(BaseModel):
    """Representación de un libro en las respuestas de la API."""

    id: int
    titulo: str
    autor: str
    editorial: str | None = None
    anio: int | None = None
    isbn: str
    categoria_id: int | None = None
    categoria: CategoriaResponse | None = None
    ejemplares: list[EjemplarResponse] = []

    model_config = ConfigDict(from_attributes=True)


class LibrosPagina(BaseModel):
    """
    Página de resultados del catálogo.

    Incluye el total global (para que el frontend pueda mostrar contadores y
    controles de páginas) y los items de la página actual.
    """

    total: int
    skip: int
    limit: int
    items: list[LibroResponse]


class DisponibilidadResponse(BaseModel):
    """
    Respuesta para el endpoint de disponibilidad de un libro.

    Incluye la información básica del libro y el conteo de
    ejemplares disponibles para préstamo.
    """

    libro_id: int
    titulo: str
    isbn: str
    total_ejemplares: int
    ejemplares_disponibles: int
