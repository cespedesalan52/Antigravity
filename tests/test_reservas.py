"""Tests de reservas: creación, reglas, cancelación e integración con préstamos."""


def libro_sin_stock(client, biblio_headers, usuarios, isbn):
    """Crea un libro de 1 ejemplar y lo presta para dejarlo sin stock."""
    libro_id = client.post("/libros/", headers=biblio_headers,
                           json={"titulo": "R", "autor": "A", "isbn": isbn, "cantidad_ejemplares": 1}).json()["id"]
    client.post("/prestamos/", headers=biblio_headers,
                json={"usuario_id": usuarios["docente"].id, "libro_id": libro_id})
    return libro_id


def test_reservar_sin_stock_ok(client, biblio_headers, estudiante_headers, usuarios):
    libro_id = libro_sin_stock(client, biblio_headers, usuarios, "R-1")
    r = client.post("/reservas/", headers=estudiante_headers, json={"libro_id": libro_id})
    assert r.status_code == 201
    assert r.json()["estado"] == "PENDIENTE"


def test_reservar_con_stock_falla(client, biblio_headers, estudiante_headers):
    libro_id = client.post("/libros/", headers=biblio_headers,
                           json={"titulo": "R", "autor": "A", "isbn": "R-STOCK", "cantidad_ejemplares": 2}).json()["id"]
    r = client.post("/reservas/", headers=estudiante_headers, json={"libro_id": libro_id})
    assert r.status_code == 400


def test_reserva_duplicada_falla(client, biblio_headers, estudiante_headers, usuarios):
    libro_id = libro_sin_stock(client, biblio_headers, usuarios, "R-DUP")
    assert client.post("/reservas/", headers=estudiante_headers, json={"libro_id": libro_id}).status_code == 201
    assert client.post("/reservas/", headers=estudiante_headers, json={"libro_id": libro_id}).status_code == 400


def test_reservar_sin_token(client, biblio_headers, usuarios):
    libro_id = libro_sin_stock(client, biblio_headers, usuarios, "R-NOAUTH")
    assert client.post("/reservas/", json={"libro_id": libro_id}).status_code == 401


def test_mis_reservas_y_cancelar(client, biblio_headers, estudiante_headers, usuarios):
    libro_id = libro_sin_stock(client, biblio_headers, usuarios, "R-MIAS")
    reserva = client.post("/reservas/", headers=estudiante_headers, json={"libro_id": libro_id}).json()

    mias = client.get("/reservas/mias", headers=estudiante_headers).json()
    assert len(mias) == 1

    r = client.post(f"/reservas/{reserva['id']}/cancelar", headers=estudiante_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "CANCELADA"


def test_listar_reservas_requiere_staff(client, estudiante_headers):
    assert client.get("/reservas/", headers=estudiante_headers).status_code == 403


def test_prestar_completa_la_reserva(client, biblio_headers, estudiante_headers, usuarios, db_session):
    from app.models.prestamo import Prestamo

    # Libro de 1 ejemplar, prestado al docente -> sin stock
    libro_id = client.post("/libros/", headers=biblio_headers,
                           json={"titulo": "R", "autor": "A", "isbn": "R-FULL", "cantidad_ejemplares": 1}).json()["id"]
    pdoc = client.post("/prestamos/", headers=biblio_headers,
                       json={"usuario_id": usuarios["docente"].id, "libro_id": libro_id}).json()

    # Estudiante reserva
    client.post("/reservas/", headers=estudiante_headers, json={"libro_id": libro_id})

    # Devolver el del docente y prestarle al estudiante (el reservante)
    client.post(f"/prestamos/{pdoc['id']}/devolucion", headers=biblio_headers, json={})
    client.post("/prestamos/", headers=biblio_headers,
                json={"usuario_id": usuarios["estudiante"].id, "libro_id": libro_id})

    mias = client.get("/reservas/mias", headers=estudiante_headers).json()
    assert mias[0]["estado"] == "COMPLETADA"
