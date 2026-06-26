"""Tests de autenticación, hashing de contraseñas y permisos básicos."""

import hashlib

from app.crud.usuario import _hash_password, necesita_rehash, verificar_password


# ── Hashing de contraseñas ──────────────────────────────────────

def test_hash_es_argon2_y_verifica():
    h = _hash_password("secreta123")
    assert h.startswith("$argon2")
    assert verificar_password("secreta123", h)
    assert not verificar_password("incorrecta", h)


def test_hash_legacy_sha256_se_verifica_y_necesita_rehash():
    legacy = hashlib.sha256(b"clave").hexdigest()
    assert verificar_password("clave", legacy)
    assert necesita_rehash(legacy)
    assert not necesita_rehash(_hash_password("clave"))


# ── Login ───────────────────────────────────────────────────────

def test_login_ok(client, usuarios):
    resp = client.post("/auth/login", json={"email": "biblio@test.edu", "password": "biblio1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["usuario"]["rol"] == "BIBLIOTECARIO"


def test_login_password_incorrecta(client, usuarios):
    resp = client.post("/auth/login", json={"email": "biblio@test.edu", "password": "mala"})
    assert resp.status_code == 401


def test_login_migra_hash_legacy(client, usuarios, db_session):
    """Una cuenta con hash SHA-256 se migra a Argon2 al iniciar sesión."""
    from app.models.usuario import Usuario

    u = db_session.query(Usuario).filter_by(email="estu@test.edu").first()
    u.contrasena_hash = hashlib.sha256(b"estud1234").hexdigest()
    db_session.commit()

    resp = client.post("/auth/login", json={"email": "estu@test.edu", "password": "estud1234"})
    assert resp.status_code == 200

    db_session.refresh(u)
    assert u.contrasena_hash.startswith("$argon2")


# ── Registro público ────────────────────────────────────────────

def test_registro_estudiante_ok(client):
    resp = client.post(
        "/auth/registro",
        json={
            "nombre": "Nuevo", "apellido": "Alumno", "dni": "90000001",
            "email": "nuevo@test.edu", "password": "clave12345", "rol": "ESTUDIANTE",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["usuario"]["rol"] == "ESTUDIANTE"


def test_registro_no_permite_staff(client):
    resp = client.post(
        "/auth/registro",
        json={
            "nombre": "Hacker", "apellido": "X", "dni": "90000002",
            "email": "hack@test.edu", "password": "clave12345", "rol": "BIBLIOTECARIO",
        },
    )
    assert resp.status_code == 403


# ── Permisos ────────────────────────────────────────────────────

def test_endpoint_protegido_sin_token(client):
    resp = client.post("/usuarios/", json={
        "dni": "1", "nombre": "a", "apellido": "b", "email": "x@x.com",
        "contrasena": "clave1234", "rol": "ESTUDIANTE",
    })
    assert resp.status_code == 401


def test_crear_usuario_requiere_staff(client, estudiante_headers):
    resp = client.post(
        "/usuarios/",
        headers=estudiante_headers,
        json={
            "dni": "55555555", "nombre": "a", "apellido": "b", "email": "y@x.com",
            "contrasena": "clave1234", "rol": "ESTUDIANTE",
        },
    )
    assert resp.status_code == 403
