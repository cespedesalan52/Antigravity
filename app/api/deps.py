"""
Dependencias de la API: autenticación y autorización.

Provee las dependencias de FastAPI para:
- `get_current_user`: identifica al usuario a partir del token Bearer.
- `require_roles`: restringe un endpoint a determinados roles.
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decodificar_token
from app.crud.usuario import obtener_usuario_por_id
from app.models.enums import RolUsuario
from app.models.usuario import Usuario


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Obtiene el usuario autenticado a partir del header Authorization.

    Espera un header con el formato `Authorization: Bearer <token>`.

    Raises:
        HTTPException 401: Si falta el token, es inválido o expiró, o si el
                           usuario referenciado ya no existe.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Inicia sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = obtener_usuario_por_id(db, usuario_id=payload.get("sub"))
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario de la sesión ya no existe.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def require_roles(*roles_permitidos: RolUsuario):
    """
    Crea una dependencia que exige que el usuario tenga uno de los roles dados.

    Uso:
        @router.delete(..., dependencies=[Depends(require_roles(RolUsuario.ADMINISTRADOR))])

    Raises:
        HTTPException 403: Si el usuario autenticado no tiene un rol permitido.
    """

    def verificar_rol(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return usuario

    return verificar_rol
