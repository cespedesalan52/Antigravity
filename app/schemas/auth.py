"""
Schemas Pydantic: Autenticación.

Modelos de entrada y salida para el inicio de sesión.
"""

from pydantic import BaseModel, EmailStr

from app.models.enums import RolUsuario
from app.schemas.usuario import UsuarioResponse


class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""

    email: EmailStr
    password: str


class RegistroRequest(BaseModel):
    """
    Datos para el auto-registro público de un usuario.

    Solo se permiten los roles ESTUDIANTE y DOCENTE; el endpoint rechaza
    cualquier intento de auto-registrarse como personal (bibliotecario o
    administrador).
    """

    nombre: str
    apellido: str
    dni: str
    email: EmailStr
    password: str
    rol: RolUsuario = RolUsuario.ESTUDIANTE


class TokenResponse(BaseModel):
    """
    Respuesta del login: el token de acceso y los datos del usuario.

    El cliente debe enviar el `access_token` en el header
    `Authorization: Bearer <token>` en las peticiones protegidas.
    """

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse
