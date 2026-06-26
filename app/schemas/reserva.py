"""
Schemas Pydantic: Reserva.

Modelos de entrada y salida para la gestión de reservas.
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import EstadoReserva


class ReservaCreate(BaseModel):
    """Datos para crear una reserva (el usuario surge del token de sesión)."""

    libro_id: int


class ReservaDetalle(BaseModel):
    """Representación enriquecida de una reserva para los listados."""

    id: int
    usuario_id: int
    usuario_nombre: str
    usuario_dni: str
    libro_id: int
    libro_titulo: str
    fecha_reserva: datetime
    estado: EstadoReserva
