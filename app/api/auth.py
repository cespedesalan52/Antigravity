"""
Router API: Autenticación.

Endpoint de inicio de sesión que valida credenciales y emite un token
de acceso firmado.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import crear_token_acceso
from app.crud.usuario import (
    autenticar_usuario,
    crear_usuario,
    obtener_usuario_por_dni,
    obtener_usuario_por_email,
)
from app.models.enums import RolUsuario
from app.schemas.auth import LoginRequest, RegistroRequest, TokenResponse
from app.schemas.usuario import UsuarioCreate

router = APIRouter()

# Roles que un usuario puede elegir al auto-registrarse.
# El personal (bibliotecario/administrador) NO puede crearse por esta vía.
ROLES_AUTOREGISTRO = {RolUsuario.ESTUDIANTE, RolUsuario.DOCENTE}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener un token de acceso",
)
@limiter.limit("10/minute")
def login(request: Request, datos: LoginRequest, db: Session = Depends(get_db)):
    """
    Valida las credenciales del usuario y devuelve un token de acceso.

    El token debe enviarse luego en el header `Authorization: Bearer <token>`
    para acceder a los endpoints protegidos.
    """
    usuario = autenticar_usuario(db, email=datos.email, password=datos.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )

    token = crear_token_acceso(usuario_id=usuario.id, rol=usuario.rol.value)
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}


@router.post(
    "/registro",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-registro de un nuevo usuario (estudiante o docente)",
)
@limiter.limit("5/minute")
def registro(request: Request, datos: RegistroRequest, db: Session = Depends(get_db)):
    """
    Permite que un estudiante o docente cree su propia cuenta e ingrese.

    No se puede usar para crear cuentas de personal (bibliotecario o
    administrador): esas debe crearlas un bibliotecario o administrador
    desde el panel de Usuarios.

    Al registrarse correctamente devuelve un token, de modo que el usuario
    queda autenticado de inmediato.
    """
    if datos.rol not in ROLES_AUTOREGISTRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Solo puedes registrarte como estudiante o docente. "
                "Las cuentas de personal las crea un bibliotecario o administrador."
            ),
        )

    if obtener_usuario_por_email(db, email=datos.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado.",
        )
    if obtener_usuario_por_dni(db, dni=datos.dni):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El DNI ya está registrado.",
        )

    usuario = crear_usuario(
        db,
        datos=UsuarioCreate(
            dni=datos.dni,
            nombre=datos.nombre,
            apellido=datos.apellido,
            email=datos.email,
            contrasena=datos.password,
            rol=datos.rol,
        ),
    )
    token = crear_token_acceso(usuario_id=usuario.id, rol=usuario.rol.value)
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}
