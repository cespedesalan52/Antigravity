"""
Schemas Pydantic: Usuario.

Define los modelos de entrada (Create) y salida (Response)
para la gestión de usuarios del sistema.
"""

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import EstadoUsuario, RolUsuario


# ── Schemas de Entrada ──────────────────────────────────────────

class UsuarioCreate(BaseModel):
    """
    Datos requeridos para registrar un nuevo usuario.

    - El campo `email` se valida automáticamente gracias a EmailStr.
    - `rol` es opcional y por defecto será ESTUDIANTE.
    """

    dni: str
    nombre: str
    apellido: str
    email: EmailStr
    contrasena: str  # Contraseña en texto plano; se hashea en el CRUD
    rol: RolUsuario = RolUsuario.ESTUDIANTE


# ── Schemas de Salida ───────────────────────────────────────────

class UsuarioResponse(BaseModel):
    """
    Representación pública de un usuario.

    Nota: NO incluye contrasena_hash por seguridad.
    """

    id: int
    dni: str
    nombre: str
    apellido: str
    email: str
    rol: RolUsuario
    estado: EstadoUsuario

    model_config = ConfigDict(from_attributes=True)
