"""Tests de préstamos y devoluciones: reglas de negocio y sanciones."""

from datetime import date, timedelta


def crear_libro(client, headers, isbn, cantidad=5):
    resp = client.post("/libros/", headers=headers,
                       json={"titulo": "T", "autor": "A", "isbn": isbn, "cantidad_ejemplares": cantidad})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def prestar(client, headers, usuario_id, libro_id):
    return client.post("/prestamos/", headers=headers, json={"usuario_id": usuario_id, "libro_id": libro_id})


def test_prestamo_ok(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, "P-OK")
    r = prestar(client, biblio_headers, usuarios["estudiante"].id, libro)
    assert r.status_code == 201
    assert r.json()["estado"] == "ACTIVO"


def test_duracion_por_rol(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, "P-DUR", cantidad=5)
    est = prestar(client, biblio_headers, usuarios["estudiante"].id, libro).json()
    doc = prestar(client, biblio_headers, usuarios["docente"].id, libro).json()

    def dias(p):
        return (date.fromisoformat(p["fecha_vencimiento"]) - date.fromisoformat(p["fecha_inicio"])).days

    assert dias(est) == 14
    assert dias(doc) == 30


def test_limite_de_prestamos_estudiante(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, "P-LIM", cantidad=5)
    est = usuarios["estudiante"].id
    assert prestar(client, biblio_headers, est, libro).status_code == 201
    assert prestar(client, biblio_headers, est, libro).status_code == 201
    assert prestar(client, biblio_headers, est, libro).status_code == 201
    # 4to supera el límite (3) de un estudiante
    r = prestar(client, biblio_headers, est, libro)
    assert r.status_code == 400
    assert "límite" in r.json()["detail"]


def test_devolucion_en_plazo_sin_sancion(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, "P-DEVOK")
    p = prestar(client, biblio_headers, usuarios["estudiante"].id, libro).json()
    r = client.post(f"/prestamos/{p['id']}/devolucion", headers=biblio_headers, json={})
    assert r.status_code == 200
    assert r.json()["sancion"] is None


def test_devolucion_tardia_genera_sancion(client, biblio_headers, usuarios):
    libro = crear_libro(client, biblio_headers, "P-TARDE")
    p = prestar(client, biblio_headers, usuarios["estudiante"].id, libro).json()
    # Devolver pasada la fecha de vencimiento
    tarde = (date.fromisoformat(p["fecha_vencimiento"]) + timedelta(days=5)).isoformat()
    r = client.post(f"/prestamos/{p['id']}/devolucion", headers=biblio_headers, json={"fecha_devolucion": tarde})
    assert r.status_code == 200
    assert r.json()["sancion"] is not None
    assert r.json()["sancion"]["monto"] > 0


def test_usuario_sancionado_no_puede_prestar(client, biblio_headers, usuarios, db_session):
    from app.models.enums import EstadoUsuario
    from app.models.usuario import Usuario

    u = db_session.get(Usuario, usuarios["estudiante"].id)
    u.estado = EstadoUsuario.SANCIONADO
    db_session.commit()

    libro = crear_libro(client, biblio_headers, "P-SANC")
    r = prestar(client, biblio_headers, usuarios["estudiante"].id, libro)
    assert r.status_code == 400


def test_marcar_vencidos(client, biblio_headers, usuarios, db_session):
    from app.models.prestamo import Prestamo

    libro = crear_libro(client, biblio_headers, "P-VENC")
    p = prestar(client, biblio_headers, usuarios["estudiante"].id, libro).json()
    # Backdatear el vencimiento al pasado
    pr = db_session.get(Prestamo, p["id"])
    pr.fecha_vencimiento = date.today() - timedelta(days=3)
    db_session.commit()

    vencidos = client.get("/prestamos/?estado=vencidos", headers=biblio_headers).json()
    assert any(x["id"] == p["id"] and x["vencido"] for x in vencidos)


def test_prestamos_requiere_staff(client, estudiante_headers, usuarios):
    r = prestar(client, estudiante_headers, usuarios["estudiante"].id, 1)
    assert r.status_code == 403
