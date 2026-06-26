"""
Modelo ORM: Libro.

Representa la ficha bibliográfica de un libro. Un libro puede tener
múltiples ejemplares físicos (copias) disponibles para préstamo.
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Libro(Base):
    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    autor: Mapped[str] = mapped_column(String(200), nullable=False)
    editorial: Mapped[str] = mapped_column(String(150), nullable=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=True)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Clave foránea hacia Categoria
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id"),
        nullable=True,
    )

    # ── Relaciones ──────────────────────────────────────────────
    categoria: Mapped["Categoria"] = relationship(  # noqa: F821
        back_populates="libros",
        lazy="selectin",
    )
    ejemplares: Mapped[list["Ejemplar"]] = relationship(  # noqa: F821
        back_populates="libro",
        lazy="selectin",
    )
    reservas: Mapped[list["Reserva"]] = relationship(  # noqa: F821
        back_populates="libro",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Libro(id={self.id}, titulo='{self.titulo}', isbn='{self.isbn}')>"
