"""
Schemas Pydantic: Ejemplar.

Define los modelos de salida para los ejemplares (copias físicas)
de un libro. No se necesita un schema de Create porque los ejemplares
se generan automáticamente al crear un libro.
"""

from pydantic import BaseModel, ConfigDict

from app.models.enums import EstadoEjemplar


# ── Schemas de Salida ───────────────────────────────────────────

class EjemplarResponse(BaseModel):
    """Representación de un ejemplar en las respuestas de la API."""

    id: int
    libro_id: int
    estado: EstadoEjemplar

    model_config = ConfigDict(from_attributes=True)
