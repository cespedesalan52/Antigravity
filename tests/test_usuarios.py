"""
Tests del router de usuarios: búsqueda incremental por DNI y por nombre.
"""


def test_buscar_por_prefijo_dni(client, biblio_headers, usuarios):
    """'4' devuelve solo el usuario cuyo DNI empieza con 4 (44444444)."""
    resp = client.get("/usuarios/?dni=4", headers=biblio_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["dni"] == "44444444"


def test_buscar_por_prefijo_dni_varios(client, biblio_headers, usuarios):
    """El prefijo coincide solo al inicio, no en cualquier posición."""
    resp = client.get("/usuarios/?dni=1", headers=biblio_headers)
    assert resp.status_code == 200
    dnis = {u["dni"] for u in resp.json()}
    assert dnis == {"11111111"}


def test_buscar_por_nombre_parcial_e_insensible(client, biblio_headers, usuarios):
    """El nombre coincide de forma parcial y sin distinguir mayúsculas."""
    resp = client.get("/usuarios/?nombre=est", headers=biblio_headers)
    assert resp.status_code == 200
    nombres = {u["nombre"] for u in resp.json()}
    # 'Esteban' (nombre) — coincidencia case-insensitive por prefijo
    assert "Esteban" in nombres


def test_buscar_por_apellido(client, biblio_headers, usuarios):
    """La búsqueda por nombre también mira el apellido."""
    resp = client.get("/usuarios/?nombre=Alumno", headers=biblio_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["apellido"] == "Alumno"


def test_buscar_combinado_dni_y_nombre(client, biblio_headers, usuarios):
    """Los filtros de DNI y nombre se combinan con AND."""
    resp = client.get("/usuarios/?dni=4&nombre=Esteban", headers=biblio_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # DNI 4... pero un nombre que no coincide → sin resultados
    resp = client.get("/usuarios/?dni=4&nombre=Ana", headers=biblio_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_buscar_sin_coincidencias(client, biblio_headers, usuarios):
    resp = client.get("/usuarios/?dni=99", headers=biblio_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_buscar_requiere_personal(client, estudiante_headers, usuarios):
    """Un estudiante no puede listar usuarios (datos personales)."""
    resp = client.get("/usuarios/?dni=4", headers=estudiante_headers)
    assert resp.status_code == 403


def test_buscar_sin_sesion_rechazado(client, usuarios):
    resp = client.get("/usuarios/?dni=4")
    assert resp.status_code in (401, 403)
