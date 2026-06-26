"""
Schemas Pydantic: Estadísticas del panel de control.
"""

from pydantic import BaseModel


class StatsResponse(BaseModel):
    """Métricas globales de la biblioteca para el dashboard."""

    total_libros: int
    total_ejemplares: int
    ejemplares_disponibles: int
    ejemplares_prestados: int
    prestamos_activos: int
    prestamos_vencidos: int
    sanciones_vigentes: int
    reservas_pendientes: int
