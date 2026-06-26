"""
Modelo ORM: Prestamo.

Registra cada transacción de préstamo de un ejemplar a un usuario.
Incluye fechas de inicio, vencimiento y devolución real para
calcular posibles sanciones por mora.
"""

from datetime import date

from sqlalchemy import Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoPrestamo


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Claves foráneas
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    ejemplar_id: Mapped[int] = mapped_column(
        ForeignKey("ejemplares.id"),
        nullable=False,
        index=True,
    )

    # Fechas del ciclo de vida del préstamo
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_devolucion_real: Mapped[date | None] = mapped_column(Date, nullable=True)

    estado: Mapped[EstadoPrestamo] = mapped_column(
        Enum(EstadoPrestamo, name="estado_prestamo", create_constraint=True),
        nullable=False,
        default=EstadoPrestamo.ACTIVO,
    )

    # ── Relaciones ──────────────────────────────────────────────
    usuario: Mapped["Usuario"] = relationship(  # noqa: F821
        back_populates="prestamos",
        lazy="selectin",
    )
    ejemplar: Mapped["Ejemplar"] = relationship(  # noqa: F821
        back_populates="prestamos",
        lazy="selectin",
    )
    sancion: Mapped["Sancion | None"] = relationship(  # noqa: F821
        back_populates="prestamo",
        uselist=False,  # Relación uno-a-uno: un préstamo genera máximo una sanción
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Prestamo(id={self.id}, usuario_id={self.usuario_id}, "
            f"ejemplar_id={self.ejemplar_id}, estado={self.estado.value})>"
        )
