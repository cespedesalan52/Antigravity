"""
Router API: Usuarios.

Endpoints para la gestión de usuarios.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.crud.usuario import (
    buscar_usuarios,
    crear_usuario,
    obtener_usuario_por_dni,
    obtener_usuario_por_email,
)
from app.models.enums import RolUsuario
from app.schemas.usuario import UsuarioCreate, UsuarioResponse

router = APIRouter()


@router.get(
    "/buscar",
    response_model=UsuarioResponse,
    summary="Buscar usuario por DNI (solo personal autorizado)",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def buscar_usuario_por_dni(
    dni: str = Query(..., description="DNI del usuario a buscar"),
    db: Session = Depends(get_db),
):
    """
    Busca un usuario por su DNI. Solo para BIBLIOTECARIO o ADMINISTRADOR
    (expone datos personales, por eso no es público).

    Se utiliza desde el panel bibliotecario para verificar la identidad
    del usuario antes de registrar un préstamo.
    """
    usuario = obtener_usuario_por_dni(db, dni=dni)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró un usuario con DNI '{dni}'.",
        )
    return usuario


@router.get(
    "/",
    response_model=list[UsuarioResponse],
    summary="Buscar usuarios por prefijo de DNI o nombre (solo personal autorizado)",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def listar_usuarios(
    dni: str | None = Query(
        None, description="Prefijo del DNI a buscar (ej. '45' → DNI que empiezan con 45)"
    ),
    nombre: str | None = Query(
        None, description="Texto a buscar dentro del nombre o el apellido"
    ),
    limit: int = Query(20, ge=1, le=100, description="Máximo de resultados a devolver"),
    db: Session = Depends(get_db),
):
    """
    Lista usuarios para la búsqueda incremental del panel bibliotecario.

    Permite filtrar por prefijo de DNI y/o por coincidencia parcial de nombre
    o apellido (filtros combinables). Devuelve una lista —posiblemente vacía—
    ordenada por apellido y nombre. Solo para BIBLIOTECARIO o ADMINISTRADOR,
    ya que expone datos personales.
    """
    return buscar_usuarios(db, dni=dni, nombre=nombre, limit=limit)


@router.post(
    "/",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo usuario (solo personal autorizado)",
    dependencies=[Depends(require_roles(RolUsuario.BIBLIOTECARIO, RolUsuario.ADMINISTRADOR))],
)
def registrar_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en el sistema (de cualquier rol).

    Solo accesible para BIBLIOTECARIO o ADMINISTRADOR: es la única vía para
    crear cuentas de personal. Los estudiantes y docentes se auto-registran
    por `POST /auth/registro`.

    Verifica que el email y el DNI no estén en uso antes de crear el usuario.
    """
    usuario_email = obtener_usuario_por_email(db, email=datos.email)
    if usuario_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado.",
        )
        
    usuario_dni = obtener_usuario_por_dni(db, dni=datos.dni)
    if usuario_dni:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El DNI ya está registrado.",
        )
        
    return crear_usuario(db, datos=datos)
