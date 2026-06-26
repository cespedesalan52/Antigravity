"""
Modelo ORM: Reserva.

Permite a los usuarios reservar un libro cuando no hay ejemplares
disponibles. Al devolverse un ejemplar, se puede notificar al usuario
que tiene una reserva activa.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoReserva


class Reserva(Base):
    __tablename__ = "reservas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Claves foráneas
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )
    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id"),
        nullable=False,
        index=True,
    )

    fecha_reserva: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    estado: Mapped[EstadoReserva] = mapped_column(
        Enum(EstadoReserva, name="estado_reserva", create_constraint=True),
        nullable=False,
        default=EstadoReserva.PENDIENTE,
    )

    # ── Relaciones ──────────────────────────────────────────────
    usuario: Mapped["Usuario"] = relationship(  # noqa: F821
        back_populates="reservas",
        lazy="selectin",
    )
    libro: Mapped["Libro"] = relationship(  # noqa: F821
        back_populates="reservas",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Reserva(id={self.id}, usuario_id={self.usuario_id}, "
            f"libro_id={self.libro_id}, estado={self.estado.value})>"
        )
