"""Tests de sanciones: generación por mora, listado y pago."""

from datetime import date, timedelta


def _generar_sancion(client, biblio_headers, usuario_id):
    """Crea un préstamo y lo devuelve tarde para generar una sanción."""
    libro_id = client.post("/libros/", headers=biblio_headers,
                           json={"titulo": "S", "autor": "A", "isbn": "S-1", "cantidad_ejemplares": 1}).json()["id"]
    p = client.post("/prestamos/", headers=biblio_headers,
                    json={"usuario_id": usuario_id, "libro_id": libro_id}).json()
    tarde = (date.fromisoformat(p["fecha_vencimiento"]) + timedelta(days=4)).isoformat()
    client.post(f"/prestamos/{p['id']}/devolucion", headers=biblio_headers, json={"fecha_devolucion": tarde})


def test_listar_y_pagar_sancion(client, biblio_headers, usuarios, db_session):
    from app.models.enums import EstadoUsuario
    from app.models.usuario import Usuario

    est_id = usuarios["estudiante"].id
    _generar_sancion(client, biblio_headers, est_id)

    sanciones = client.get("/sanciones/", headers=biblio_headers).json()
    assert len(sanciones) == 1
    assert sanciones[0]["vigente"] is True

    # El usuario quedó sancionado
    db_session.expire_all()
    assert db_session.get(Usuario, est_id).estado == EstadoUsuario.SANCIONADO

    # Pagar la sanción -> se reactiva
    sid = sanciones[0]["id"]
    r = client.post(f"/sanciones/{sid}/pagar", headers=biblio_headers)
    assert r.status_code == 200
    assert r.json()["vigente"] is False

    db_session.expire_all()
    assert db_session.get(Usuario, est_id).estado == EstadoUsuario.ACTIVO


def test_pagar_sancion_ya_saldada_falla(client, biblio_headers, usuarios):
    _generar_sancion(client, biblio_headers, usuarios["estudiante"].id)
    sid = client.get("/sanciones/", headers=biblio_headers).json()[0]["id"]
    assert client.post(f"/sanciones/{sid}/pagar", headers=biblio_headers).status_code == 200
    assert client.post(f"/sanciones/{sid}/pagar", headers=biblio_headers).status_code == 400


def test_sanciones_requiere_staff(client, estudiante_headers):
    assert client.get("/sanciones/", headers=estudiante_headers).status_code == 403
