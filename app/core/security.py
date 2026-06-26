"""
Seguridad: tokens de acceso firmados.

Implementa un token de acceso minimalista (similar a un JWT HS256) usando
solo la librería estándar de Python, para no agregar dependencias externas
—coherente con el resto del proyecto (ver el hash de contraseñas en
`app/crud/usuario.py`).

El token tiene el formato:  base64url(payload) "." base64url(firma_hmac)

La firma HMAC-SHA256 con `SECRET_KEY` garantiza que el cliente no pueda
alterar el payload (p. ej. cambiar su rol) sin invalidar el token.
"""

import base64
import hashlib
import hmac
import json
import time

from app.core.config import settings


def _b64url_encode(data: bytes) -> str:
    """Codifica en base64url sin relleno (padding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(texto: str) -> bytes:
    """Decodifica base64url reponiendo el relleno necesario."""
    relleno = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + relleno)


def _firmar(payload_codificado: str) -> str:
    """Calcula la firma HMAC-SHA256 del payload codificado."""
    firma = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_codificado.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(firma)


def crear_token_acceso(usuario_id: int, rol: str) -> str:
    """
    Genera un token de acceso firmado para un usuario.

    Args:
        usuario_id: ID del usuario autenticado (va en el claim `sub`).
        rol: Rol del usuario (va en el claim `rol`).

    Returns:
        El token de acceso como cadena.
    """
    expira_en = int(time.time()) + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = {"sub": usuario_id, "rol": rol, "exp": expira_en}
    payload_codificado = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    return f"{payload_codificado}.{_firmar(payload_codificado)}"


def decodificar_token(token: str) -> dict | None:
    """
    Verifica la firma y la expiración de un token, y devuelve su payload.

    Args:
        token: El token de acceso recibido del cliente.

    Returns:
        El diccionario del payload si el token es válido y no expiró,
        o None si la firma es inválida, está malformado o expiró.
    """
    try:
        payload_codificado, firma_recibida = token.split(".")
    except (ValueError, AttributeError):
        return None

    # Comparación en tiempo constante para evitar ataques de temporización
    if not hmac.compare_digest(firma_recibida, _firmar(payload_codificado)):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_codificado))
    except (ValueError, json.JSONDecodeError):
        return None

    if payload.get("exp", 0) < int(time.time()):
        return None

    return payload
