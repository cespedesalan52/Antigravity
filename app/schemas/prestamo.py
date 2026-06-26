"""
Schemas Pydantic: Prestamo.

Define los modelos de entrada y salida para las operaciones
de préstamo y devolución de ejemplares.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import EstadoPrestamo


# ── Schemas de Entrada ──────────────────────────────────────────

class PrestamoCreate(BaseModel):
    """
    Datos para registrar un nuevo préstamo.

    Solo se necesita el usuario y el libro. La lógica de negocio
    se encarga de buscar un ejemplar disponible, calcular la fecha
    de vencimiento y validar el estado del usuario.
    """

    usuario_id: int
    libro_id: int


class DevolucionCreate(BaseModel):
    """
    Datos opcionales para registrar una devolución.

    La fecha de devolución real se puede omitir; en ese caso
    se usa la fecha actual del servidor.
    """

    fecha_devolucion: date | None = None


# ── Schemas de Salida ───────────────────────────────────────────

class PrestamoResponse(BaseModel):
    """Representación de un préstamo en las respuestas de la API."""

    id: int
    usuario_id: int
    ejemplar_id: int
    fecha_inicio: date
    fecha_vencimiento: date
    fecha_devolucion_real: date | None = None
    estado: EstadoPrestamo

    model_config = ConfigDict(from_attributes=True)


class PrestamoDetalle(BaseModel):
    """
    Representación enriquecida de un préstamo para los listados del panel.

    Incluye datos del usuario y del libro (resueltos por relaciones) y
    campos calculados sobre el vencimiento, para no obligar al frontend a
    hacer múltiples consultas.
    """

    id: int
    usuario_id: int
    usuario_nombre: str
    usuario_dni: str
    libro_id: int
    libro_titulo: str
    ejemplar_id: int
    fecha_inicio: date
    fecha_vencimiento: date
    fecha_devolucion_real: date | None = None
    estado: EstadoPrestamo
    vencido: bool
    dias_vencido: int


class SancionResponse(BaseModel):
    """
    Representación de una sanción generada automáticamente
    al detectar una devolución tardía.
    """

    id: int
    usuario_id: int
    prestamo_id: int
    tipo: str
    monto: float
    fecha_inicio: date
    fecha_fin: date | None = None

    model_config = ConfigDict(from_attributes=True)


class DevolucionResponse(BaseModel):
    """
    Respuesta al registrar una devolución.

    Incluye el préstamo actualizado y, opcionalmente, la sanción
    generada si la devolución fue tardía.
    """

    prestamo: PrestamoResponse
    sancion: SancionResponse | None = None
    mensaje: str
