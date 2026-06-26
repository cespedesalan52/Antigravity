"""Tests de estadísticas y categorías."""


def test_stats_cuenta_correctamente(client, biblio_headers, estudiante_headers, usuarios):
    # Estado inicial
    s0 = client.get("/stats/", headers=biblio_headers).json()

    # Crear libro con 2 ejemplares y prestar 1
    libro = client.post("/libros/", headers=biblio_headers,
                        json={"titulo": "T", "autor": "A", "isbn": "ST-1", "cantidad_ejemplares": 2}).json()
    client.post("/prestamos/", headers=biblio_headers,
                json={"usuario_id": usuarios["estudiante"].id, "libro_id": libro["id"]})

    s1 = client.get("/stats/", headers=biblio_headers).json()
    assert s1["total_libros"] == s0["total_libros"] + 1
    assert s1["total_ejemplares"] == s0["total_ejemplares"] + 2
    assert s1["prestamos_activos"] == s0["prestamos_activos"] + 1


def test_stats_requiere_sesion(client):
    assert client.get("/stats/").status_code == 401


def test_categoria_crear_y_listar(client, biblio_headers):
    r = client.post("/categorias/", headers=biblio_headers, json={"nombre": "Historia"})
    assert r.status_code == 201
    nombres = [c["nombre"] for c in client.get("/categorias/").json()]
    assert "Historia" in nombres


def test_categoria_duplicada_falla(client, biblio_headers):
    client.post("/categorias/", headers=biblio_headers, json={"nombre": "Arte"})
    assert client.post("/categorias/", headers=biblio_headers, json={"nombre": "Arte"}).status_code == 400


def test_categoria_crear_requiere_staff(client, estudiante_headers):
    assert client.post("/categorias/", headers=estudiante_headers, json={"nombre": "X"}).status_code == 403
