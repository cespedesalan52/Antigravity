"""
Paquete de modelos ORM.

Importa y expone todos los modelos y enums para que:
1. SQLAlchemy detecte todas las tablas al llamar Base.metadata.create_all().
2. Otros módulos puedan importar de forma limpia:
   from app.models import Usuario, Libro, Prestamo, ...
"""

# Enumeraciones
from app.models.enums import (
    EstadoEjemplar,
    EstadoPrestamo,
    EstadoReserva,
    EstadoUsuario,
    RolUsuario,
    TipoSancion,
)

# Modelos ORM
from app.models.categoria import Categoria
from app.models.ejemplar import Ejemplar
from app.models.libro import Libro
from app.models.prestamo import Prestamo
from app.models.reserva import Reserva
from app.models.sancion import Sancion
from app.models.usuario import Usuario

# Exponer todos los símbolos públicos
__all__ = [
    # Enums
    "RolUsuario",
    "EstadoUsuario",
    "EstadoEjemplar",
    "EstadoPrestamo",
    "EstadoReserva",
    "TipoSancion",
    # Modelos
    "Categoria",
    "Usuario",
    "Libro",
    "Ejemplar",
    "Prestamo",
    "Reserva",
    "Sancion",
]
