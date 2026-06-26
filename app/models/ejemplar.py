"""
Modelo ORM: Ejemplar.

Representa una copia física de un libro. Cada libro puede tener
múltiples ejemplares, y cada ejemplar tiene su propio estado
(disponible, prestado, en mantenimiento, etc.).
"""

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoEjemplar


class Ejemplar(Base):
    __tablename__ = "ejemplares"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Clave foránea hacia Libro
    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id"),
        nullable=False,
        index=True,
    )

    estado: Mapped[EstadoEjemplar] = mapped_column(
        Enum(EstadoEjemplar, name="estado_ejemplar", create_constraint=True),
        nullable=False,
        default=EstadoEjemplar.DISPONIBLE,
    )

    # ── Relaciones ──────────────────────────────────────────────
    libro: Mapped["Libro"] = relationship(  # noqa: F821
        back_populates="ejemplares",
        lazy="selectin",
    )
    prestamos: Mapped[list["Prestamo"]] = relationship(  # noqa: F821
        back_populates="ejemplar",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Ejemplar(id={self.id}, libro_id={self.libro_id}, estado={self.estado.value})>"
