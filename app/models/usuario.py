"""
Modelo ORM: Usuario.

Representa a los usuarios del sistema de biblioteca: estudiantes, docentes,
bibliotecarios y administradores.
"""

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoUsuario, RolUsuario


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dni: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Enum mapeado al tipo ENUM nativo de PostgreSQL
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(RolUsuario, name="rol_usuario", create_constraint=True),
        nullable=False,
        default=RolUsuario.ESTUDIANTE,
    )
    estado: Mapped[EstadoUsuario] = mapped_column(
        Enum(EstadoUsuario, name="estado_usuario", create_constraint=True),
        nullable=False,
        default=EstadoUsuario.ACTIVO,
    )

    # ── Relaciones ──────────────────────────────────────────────
    prestamos: Mapped[list["Prestamo"]] = relationship(  # noqa: F821
        back_populates="usuario",
        lazy="selectin",
    )
    reservas: Mapped[list["Reserva"]] = relationship(  # noqa: F821
        back_populates="usuario",
        lazy="selectin",
    )
    sanciones: Mapped[list["Sancion"]] = relationship(  # noqa: F821
        back_populates="usuario",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Usuario(id={self.id}, email='{self.email}', rol={self.rol.value})>"
