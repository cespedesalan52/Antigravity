"""Tests del catálogo: creación, edición de ejemplares y borrado seguro."""


def crear_libro(client, headers, isbn="L-1", cantidad=2, titulo="Libro X"):
    resp = client.post(
        "/libros/",
        headers=headers,
        json={"titulo": titulo, "autor": "Autor", "isbn": isbn, "cantidad_ejemplares": cantidad},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def disponibles(client, libro_id):
    return client.get(f"/libros/{libro_id}/disponibilidad").json()["ejemplares_disponibles"]


def test_crear_libro_genera_ejemplares(client, biblio_headers):
    libro = crear_libro(client, biblio_headers, isbn="L-CREA", cantidad=3)
    assert len(libro["ejemplares"]) == 3
    assert disponibles(client, libro["id"]) == 3


def test_editar_aumenta_ejemplares(client, biblio_headers):
    libro = crear_libro(client, biblio_headers, isbn="L-UP", cantidad=2)
    resp = client.put(f"/libros/{libro['id']}", headers=biblio_headers, json={"cantidad_ejemplares": 5})
    assert resp.status_code == 200
    assert disponibles(client, libro["id"]) == 5


def test_editar_reduce_ejemplares(client, biblio_headers):
    libro = crear_libro(client, biblio_headers, isbn="L-DOWN", cantidad=5)
    resp = client.put(f"/libros/{libro['id']}", headers=biblio_headers, json={"cantidad_ejemplares": 2})
    assert resp.status_code == 200
    assert disponibles(client, libro["id"]) == 2


def test_no_reduce_por_debajo_de_los_prestados(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, isbn="L-LOAN", cantidad=2)
    # Prestar un ejemplar
    r = client.post("/prestamos/", headers=biblio_headers,
                    json={"usuario_id": usuarios["estudiante"].id, "libro_id": libro["id"]})
    assert r.status_code == 201
    # Intentar dejar 0: imposible, hay 1 prestado
    resp = client.put(f"/libros/{libro['id']}", headers=biblio_headers, json={"cantidad_ejemplares": 0})
    assert resp.status_code == 400


def test_eliminar_con_prestamo_activo_falla(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, isbn="L-DEL1", cantidad=1)
    client.post("/prestamos/", headers=biblio_headers,
                json={"usuario_id": usuarios["estudiante"].id, "libro_id": libro["id"]})
    resp = client.delete(f"/libros/{libro['id']}", headers=biblio_headers)
    assert resp.status_code == 409


def test_eliminar_libro_limpio(client, biblio_headers):
    libro = crear_libro(client, biblio_headers, isbn="L-DEL2", cantidad=1)
    resp = client.delete(f"/libros/{libro['id']}", headers=biblio_headers)
    assert resp.status_code == 204
    assert client.get(f"/libros/{libro['id']}/disponibilidad").status_code == 404


def test_crear_libro_requiere_staff(client, estudiante_headers):
    resp = client.post(
        "/libros/",
        headers=estudiante_headers,
        json={"titulo": "X", "autor": "Y", "isbn": "L-NO", "cantidad_ejemplares": 1},
    )
    assert resp.status_code == 403


def test_listar_libros_es_publico(client):
    resp = client.get("/libros/")
    assert resp.status_code == 200
    # La respuesta es una página: {total, skip, limit, items}
    data = resp.json()
    assert set(data.keys()) == {"total", "skip", "limit", "items"}


def test_paginacion_total_e_items(client, biblio_headers):
    for i in range(5):
        crear_libro(client, biblio_headers, isbn=f"PAG-{i}", titulo=f"Libro {i}")

    pag1 = client.get("/libros/?skip=0&limit=2").json()
    assert pag1["total"] == 5
    assert len(pag1["items"]) == 2

    pag3 = client.get("/libros/?skip=4&limit=2").json()
    assert pag3["total"] == 5
    assert len(pag3["items"]) == 1  # queda solo el último
