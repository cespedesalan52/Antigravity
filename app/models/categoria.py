"""
Modelo ORM: Categoria.

Representa las categorías temáticas para clasificar los libros
(ej. Ciencia, Historia, Programación, etc.).
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # ── Relaciones ──────────────────────────────────────────────
    # Un Categoria tiene muchos Libros
    libros: Mapped[list["Libro"]] = relationship(  # noqa: F821
        back_populates="categoria",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Categoria(id={self.id}, nombre='{self.nombre}')>"
