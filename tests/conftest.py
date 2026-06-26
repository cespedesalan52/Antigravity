"""
Configuración de pytest: base de datos de pruebas aislada y cliente HTTP.

Se usa una base SQLite temporal en archivo (no la PostgreSQL real), con las
tablas creadas a partir de los modelos. La dependencia `get_db` se sustituye
para que la API use esta base durante los tests.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registra todos los modelos en el metadata)
from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.crud.usuario import crear_usuario
from app.main import app
from app.models.enums import RolUsuario
from app.schemas.usuario import UsuarioCreate


@pytest.fixture(autouse=True)
def desactivar_rate_limit():
    """Desactiva el rate limiting por defecto en los tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture()
def db_engine():
    """Crea un engine SQLite temporal con las tablas del proyecto."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _activar_fk(dbapi_con, _record):
        # SQLite no aplica claves foráneas por defecto
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    os.unlink(path)


@pytest.fixture()
def SessionLocal(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session(SessionLocal):
    """Sesión directa a la BD de prueba (para sembrar datos o verificar)."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(SessionLocal):
    """Cliente de la API con `get_db` apuntando a la base de prueba."""

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Sin context manager para no disparar el lifespan (que tocaría PostgreSQL).
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Helpers / fixtures de usuarios ──────────────────────────────

_USUARIOS = {
    "admin": ("11111111", "Ana", "Admin", "admin@test.edu", "admin1234", RolUsuario.ADMINISTRADOR),
    "biblio": ("22222222", "Bibi", "Otecaria", "biblio@test.edu", "biblio1234", RolUsuario.BIBLIOTECARIO),
    "docente": ("33333333", "Dora", "Docente", "docente@test.edu", "docente1234", RolUsuario.DOCENTE),
    "estudiante": ("44444444", "Esteban", "Alumno", "estu@test.edu", "estud1234", RolUsuario.ESTUDIANTE),
}


@pytest.fixture()
def usuarios(db_session):
    """Crea un usuario de cada rol y devuelve un dict con sus instancias."""
    creados = {}
    for clave, (dni, nombre, apellido, email, pwd, rol) in _USUARIOS.items():
        creados[clave] = crear_usuario(
            db_session,
            UsuarioCreate(dni=dni, nombre=nombre, apellido=apellido, email=email, contrasena=pwd, rol=rol),
        )
    return creados


def login(client, email, password):
    """Devuelve los headers de autorización para un usuario."""
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def biblio_headers(client, usuarios):
    return login(client, "biblio@test.edu", "biblio1234")


@pytest.fixture()
def estudiante_headers(client, usuarios):
    return login(client, "estu@test.edu", "estud1234")
