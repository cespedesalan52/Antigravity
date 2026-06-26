"""
Schemas Pydantic: Sancion.

Modelos de salida para los listados de sanciones del panel.
"""

from datetime import date

from pydantic import BaseModel


class SancionDetalle(BaseModel):
    """Representación enriquecida de una sanción para el panel de personal."""

    id: int
    usuario_id: int
    usuario_nombre: str
    usuario_dni: str
    prestamo_id: int
    tipo: str
    monto: float
    fecha_inicio: date
    fecha_fin: date | None = None
    vigente: bool
