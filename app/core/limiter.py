"""
Rate limiting (límite de peticiones por IP).

Define la instancia de `Limiter` que se usa para proteger endpoints
sensibles (login, registro) contra fuerza bruta y spam.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# La clave por defecto es la IP de origen del cliente.
# (Detrás de un proxy/túnel conviene configurar X-Forwarded-For.)
limiter = Limiter(key_func=get_remote_address)
