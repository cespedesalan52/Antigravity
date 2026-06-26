"""
CRUD: Usuario.

Operaciones de base de datos para la gestión de usuarios.
"""

import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate

# Hashing de contraseñas con Argon2id (recomendación de OWASP): salado,
# resistente a GPU/ASIC y con parámetros de coste integrados en el hash.
# El PasswordHasher usa parámetros por defecto seguros y maneja la sal interna.
_password_hasher = PasswordHasher()


def _hash_password(password: str) -> str:
    """Genera un hash Argon2id de la contraseña (con sal aleatoria interna)."""
    return _password_hasher.hash(password)


def verificar_password(password: str, hash_almacenado: str) -> bool:
    """
    Verifica una contraseña contra el hash almacenado.

    Soporta el formato Argon2id y el legacy (SHA-256 sin sal) para no romper
    las cuentas creadas antes de este cambio.
    """
    if hash_almacenado.startswith("$argon2"):
        try:
            return _password_hasher.verify(hash_almacenado, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    # Formato legacy: SHA-256 sin sal (comparación en tiempo constante)
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(hash_almacenado, legacy)


def necesita_rehash(hash_almacenado: str) -> bool:
    """
    Indica si conviene re-hashear: hashes legacy o Argon2 con parámetros
    desactualizados respecto a la configuración actual.
    """
    if not hash_almacenado.startswith("$argon2"):
        return True
    try:
        return _password_hasher.check_needs_rehash(hash_almacenado)
    except InvalidHashError:
        return True


def crear_usuario(db: Session, datos: UsuarioCreate) -> Usuario:
    """
    Crea un nuevo usuario en la base de datos.

    Pasos:
    1. Hashea la contraseña en texto plano.
    2. Crea la instancia del modelo ORM.
    3. Persiste en la BD y refresca el objeto para obtener el ID generado.

    Args:
        db: Sesión activa de SQLAlchemy.
        datos: Schema Pydantic con los datos del nuevo usuario.

    Returns:
        La instancia del Usuario recién creado.
    """
    usuario = Usuario(
        dni=datos.dni,
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        contrasena_hash=_hash_password(datos.contrasena),
        rol=datos.rol,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar_usuario(db: Session, email: str, password: str) -> Usuario | None:
    """
    Verifica las credenciales de un usuario.

    Compara el hash de la contraseña recibida con el almacenado.

    Args:
        db: Sesión activa de SQLAlchemy.
        email: Email del usuario que intenta iniciar sesión.
        password: Contraseña en texto plano a verificar.

    Returns:
        La instancia del Usuario si las credenciales son correctas, o None.
    """
    usuario = obtener_usuario_por_email(db, email=email)
    if not usuario:
        return None
    if not verificar_password(password, usuario.contrasena_hash):
        return None

    # Migración transparente: si la cuenta tenía un hash legacy (SHA-256),
    # se re-hashea con PBKDF2 al primer login exitoso.
    if necesita_rehash(usuario.contrasena_hash):
        usuario.contrasena_hash = _hash_password(password)
        db.commit()

    return usuario


def obtener_usuario_por_email(db: Session, email: str) -> Usuario | None:
    """
    Busca un usuario por su dirección de email.

    Args:
        db: Sesión activa de SQLAlchemy.
        email: Dirección de email a buscar.

    Returns:
        La instancia del Usuario si existe, o None si no se encontró.
    """
    stmt = select(Usuario).where(Usuario.email == email)
    return db.execute(stmt).scalar_one_or_none()


def obtener_usuario_por_id(db: Session, usuario_id: int) -> Usuario | None:
    """
    Busca un usuario por su ID.

    Args:
        db: Sesión activa de SQLAlchemy.
        usuario_id: ID del usuario a buscar.

    Returns:
        La instancia del Usuario si existe, o None si no se encontró.
    """
    return db.get(Usuario, usuario_id)


def obtener_usuario_por_dni(db: Session, dni: str) -> Usuario | None:
    """
    Busca un usuario por su DNI.

    Args:
        db: Sesión activa de SQLAlchemy.
        dni: Documento Nacional de Identidad del usuario.

    Returns:
        La instancia del Usuario si existe, o None si no se encontró.
    """
    stmt = select(Usuario).where(Usuario.dni == dni)
    return db.execute(stmt).scalar_one_or_none()


def buscar_usuarios(
    db: Session,
    dni: str | None = None,
    nombre: str | None = None,
    limit: int = 20,
) -> list[Usuario]:
    """
    Busca usuarios por prefijo de DNI y/o por nombre o apellido.

    A diferencia de `obtener_usuario_por_dni` (coincidencia exacta), esta
    función está pensada para la búsqueda incremental del panel bibliotecario:

    - `dni`: coincidencia por PREFIJO (ej. "45" devuelve los DNI que empiezan
      con 45).
    - `nombre`: coincidencia PARCIAL case-insensitive contra el nombre y el
      apellido (ej. "Alan" devuelve a todos los que se llamen así).

    Ambos filtros son combinables (se aplican con AND). Si no se pasa ningún
    filtro, devuelve los primeros `limit` usuarios. Los resultados se ordenan
    por apellido y nombre para una lectura predecible.

    Args:
        db: Sesión activa de SQLAlchemy.
        dni: Prefijo del DNI a buscar.
        nombre: Texto a buscar dentro del nombre o el apellido.
        limit: Cantidad máxima de resultados a devolver.

    Returns:
        Lista de usuarios que coinciden con los criterios.
    """
    stmt = select(Usuario)

    if dni:
        stmt = stmt.where(Usuario.dni.ilike(f"{dni}%"))

    if nombre:
        patron = f"%{nombre}%"
        stmt = stmt.where(
            or_(
                Usuario.nombre.ilike(patron),
                Usuario.apellido.ilike(patron),
            )
        )

    stmt = stmt.order_by(Usuario.apellido, Usuario.nombre).limit(limit)
    return list(db.execute(stmt).scalars().all())
