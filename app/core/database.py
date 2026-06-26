"""
Módulo de conexión a la base de datos.

Configura el engine de SQLAlchemy, la fábrica de sesiones (SessionLocal),
la clase base declarativa (Base) y la inyección de dependencias (get_db)
para usar con FastAPI.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# ========================================
# Engine de SQLAlchemy
# ========================================
# pool_pre_ping=True verifica que la conexión esté viva antes de usarla,
# evitando errores por conexiones caídas en pools de larga duración.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Cambiar a True para depuración de SQL generado
)

# ========================================
# Fábrica de Sesiones
# ========================================
# autocommit=False: las transacciones deben ser confirmadas explícitamente.
# autoflush=False: evita que SQLAlchemy haga flush automático antes de queries,
# dando mayor control sobre cuándo se persisten los datos.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ========================================
# Clase Base Declarativa (SQLAlchemy 2.0)
# ========================================
class Base(DeclarativeBase):
    """
    Clase base para todos los modelos ORM del proyecto.

    Todos los modelos deben heredar de esta clase para ser detectados
    por SQLAlchemy y poder crear las tablas con Base.metadata.create_all().
    """

    pass


# ========================================
# Inyección de Dependencias para FastAPI
# ========================================
def get_db() -> Generator[Session, None, None]:
    """
    Generador que provee una sesión de base de datos.

    Se usa como dependencia en los endpoints de FastAPI:

        @router.post("/ejemplo")
        def crear_ejemplo(db: Session = Depends(get_db)):
            ...

    La sesión se cierra automáticamente al finalizar la solicitud HTTP,
    garantizando que no queden conexiones abiertas.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
