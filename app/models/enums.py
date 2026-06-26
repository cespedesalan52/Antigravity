"""
Enumeraciones del dominio de biblioteca.

Define los tipos enumerados que se usan como columnas en los modelos ORM.
SQLAlchemy mapea estos enums de Python a tipos ENUM nativos de PostgreSQL,
garantizando integridad referencial a nivel de base de datos.
"""

import enum


class RolUsuario(str, enum.Enum):
    """Roles posibles para un usuario del sistema."""

    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    BIBLIOTECARIO = "BIBLIOTECARIO"
    ADMINISTRADOR = "ADMINISTRADOR"


class EstadoUsuario(str, enum.Enum):
    """Estados del ciclo de vida de un usuario."""

    ACTIVO = "ACTIVO"
    SANCIONADO = "SANCIONADO"
    INACTIVO = "INACTIVO"


class EstadoEjemplar(str, enum.Enum):
    """Estados posibles de un ejemplar físico de un libro."""

    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    MANTENIMIENTO = "MANTENIMIENTO"
    PERDIDO = "PERDIDO"


class EstadoPrestamo(str, enum.Enum):
    """Estados del ciclo de vida de un préstamo."""

    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    VENCIDO = "VENCIDO"


class EstadoReserva(str, enum.Enum):
    """Estados posibles de una reserva de libro."""

    PENDIENTE = "PENDIENTE"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"
    EXPIRADA = "EXPIRADA"


class TipoSancion(str, enum.Enum):
    """Tipos de sanción que se pueden aplicar a un usuario."""

    MORA = "MORA"        # Devolución tardía
    DANIO = "DANIO"      # Daño al ejemplar
    PERDIDA = "PERDIDA"  # Pérdida del ejemplar
