"""
Modelo ORM: Sancion.

Registra las sanciones aplicadas a un usuario como consecuencia
de una devolución tardía, daño o pérdida de un ejemplar.
Cada sanción está vinculada a un préstamo específico.
"""

from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TipoSancion


class Sancion(Base):
    __tablename__ = "sanciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Claves foráneas
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    prestamo_id: Mapped[int] = mapped_column(
        ForeignKey("prestamos.id"),
        nullable=False,
        unique=True,  # Un préstamo genera máximo una sanción
    )

    tipo: Mapped[TipoSancion] = mapped_column(
        Enum(TipoSancion, name="tipo_sancion", create_constraint=True),
        nullable=False,
    )

    # Monto monetario de la sanción (precision 10, 2 decimales)
    monto: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=0.00,
    )

    # Período de vigencia de la sanción
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Relaciones ──────────────────────────────────────────────
    usuario: Mapped["Usuario"] = relationship(  # noqa: F821
        back_populates="sanciones",
        lazy="selectin",
    )
    prestamo: Mapped["Prestamo"] = relationship(  # noqa: F821
        back_populates="sancion",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Sancion(id={self.id}, usuario_id={self.usuario_id}, "
            f"tipo={self.tipo.value}, monto={self.monto})>"
        )
