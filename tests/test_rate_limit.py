"""Test del rate limiting en endpoints de autenticación."""

from app.core.limiter import limiter


def test_login_se_limita_por_exceso_de_intentos(client):
    """Tras varios intentos rápidos de login, el endpoint responde 429."""
    limiter.enabled = True
    limiter.reset()
    try:
        estados = []
        for _ in range(13):
            r = client.post("/auth/login", json={"email": "noexiste@test.edu", "password": "x"})
            estados.append(r.status_code)
    finally:
        limiter.reset()
        limiter.enabled = False

    # Los primeros intentos no están limitados; en algún momento aparece el 429.
    assert estados[0] != 429
    assert 429 in estados
