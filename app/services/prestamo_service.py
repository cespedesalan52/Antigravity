"""
Servicio de Préstamos y Devoluciones.

Contiene la lógica de negocio compleja que orquesta múltiples
operaciones CRUD y aplica las reglas del dominio de biblioteca:

- Validar que el usuario esté activo y sin sanciones.
- Buscar un ejemplar disponible del libro solicitado.
- Calcular fechas de vencimiento.
- Detectar devoluciones tardías y generar sanciones automáticas.
"""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.libro import buscar_ejemplar_disponible
from app.crud.prestamo import (
    ESTADOS_EN_CURSO,
    contar_prestamos_activos,
    obtener_prestamo_por_id,
    tiene_sanciones_vigentes,
)
from app.crud.reserva import completar_reserva_si_existe, reservas_pendientes_libro
from app.crud.usuario import obtener_usuario_por_id
from app.models.enums import (
    EstadoEjemplar,
    EstadoPrestamo,
    EstadoUsuario,
    RolUsuario,
    TipoSancion,
)
from app.models.prestamo import Prestamo
from app.models.sancion import Sancion

# Duración estándar de un préstamo en días (fallback)
DIAS_PRESTAMO = 14

# Duración del préstamo según el rol del usuario (los docentes obtienen plazos
# más largos que los estudiantes).
DIAS_PRESTAMO_POR_ROL = {
    RolUsuario.ESTUDIANTE: 14,
    RolUsuario.DOCENTE: 30,
    RolUsuario.BIBLIOTECARIO: 30,
    RolUsuario.ADMINISTRADOR: 30,
}

# Máximo de préstamos simultáneos según el rol.
LIMITE_PRESTAMOS_POR_ROL = {
    RolUsuario.ESTUDIANTE: 3,
    RolUsuario.DOCENTE: 5,
    RolUsuario.BIBLIOTECARIO: 10,
    RolUsuario.ADMINISTRADOR: 10,
}

# Monto de multa por día de retraso (en la moneda local)
MULTA_POR_DIA = 5.00


def registrar_prestamo(db: Session, usuario_id: int, libro_id: int) -> Prestamo:
    """
    Registra un nuevo préstamo de un libro a un usuario.

    Flujo de la lógica de negocio:
    ┌─────────────────────────────────────────────────────────────┐
    │  1. Verificar que el usuario existe                        │
    │  2. Verificar que el usuario está ACTIVO                   │
    │  3. Verificar que el usuario NO tiene sanciones vigentes   │
    │  4. Buscar un ejemplar DISPONIBLE del libro solicitado     │
    │  5. Cambiar el estado del ejemplar a PRESTADO              │
    │  6. Crear el registro de Préstamo con fecha de vencimiento │
    │  7. Confirmar la transacción                               │
    └─────────────────────────────────────────────────────────────┘

    Args:
        db: Sesión activa de SQLAlchemy.
        usuario_id: ID del usuario que solicita el préstamo.
        libro_id: ID del libro que desea prestar.

    Returns:
        La instancia del Préstamo recién creado.

    Raises:
        HTTPException: Si alguna validación falla (usuario no encontrado,
                       inactivo, sancionado, o sin ejemplares disponibles).
    """

    # ── Paso 1: Verificar existencia del usuario ───────────────
    usuario = obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado.",
        )

    # ── Paso 2: Verificar que el usuario esté ACTIVO ───────────
    if usuario.estado != EstadoUsuario.ACTIVO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El usuario '{usuario.nombre} {usuario.apellido}' no está activo. "
                f"Estado actual: {usuario.estado.value}."
            ),
        )

    # ── Paso 3: Verificar que no tenga sanciones vigentes ──────
    if tiene_sanciones_vigentes(db, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El usuario '{usuario.nombre} {usuario.apellido}' tiene sanciones "
                "vigentes y no puede realizar préstamos hasta que se resuelvan."
            ),
        )

    # ── Paso 4: Verificar el límite de préstamos simultáneos ───
    limite = LIMITE_PRESTAMOS_POR_ROL.get(usuario.rol, 3)
    activos = contar_prestamos_activos(db, usuario_id)
    if activos >= limite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El usuario '{usuario.nombre} {usuario.apellido}' ya alcanzó su "
                f"límite de {limite} préstamos simultáneos (tiene {activos} en curso)."
            ),
        )

    # ── Paso 5: Buscar ejemplar disponible ─────────────────────
    ejemplar = buscar_ejemplar_disponible(db, libro_id)
    if not ejemplar:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"No hay ejemplares disponibles para el libro con ID {libro_id}. "
                "Todos los ejemplares están prestados o en mantenimiento."
            ),
        )

    # ── Paso 6: Cambiar estado del ejemplar a PRESTADO ─────────
    ejemplar.estado = EstadoEjemplar.PRESTADO

    # ── Paso 7: Crear el registro de Préstamo ──────────────────
    # El plazo de devolución depende del rol del usuario.
    hoy = date.today()
    dias_plazo = DIAS_PRESTAMO_POR_ROL.get(usuario.rol, DIAS_PRESTAMO)
    prestamo = Prestamo(
        usuario_id=usuario_id,
        ejemplar_id=ejemplar.id,
        fecha_inicio=hoy,
        fecha_vencimiento=hoy + timedelta(days=dias_plazo),
        estado=EstadoPrestamo.ACTIVO,
    )
    db.add(prestamo)

    # Si el usuario tenía una reserva pendiente de este libro, se concreta.
    completar_reserva_si_existe(db, usuario_id, libro_id)

    # ── Paso 8: Confirmar transacción ──────────────────────────
    db.commit()
    db.refresh(prestamo)
    return prestamo


def registrar_devolucion(
    db: Session,
    prestamo_id: int,
    fecha_devolucion: date | None = None,
) -> dict:
    """
    Registra la devolución de un préstamo.

    Flujo de la lógica de negocio:
    ┌─────────────────────────────────────────────────────────────┐
    │  1. Verificar que el préstamo existe                       │
    │  2. Verificar que el préstamo está ACTIVO                  │
    │  3. Registrar la fecha de devolución real                  │
    │  4. Cambiar el estado del préstamo a DEVUELTO              │
    │  5. Cambiar el estado del ejemplar a DISPONIBLE            │
    │  6. Si la devolución es tardía → crear Sanción             │
    │  7. Confirmar la transacción                               │
    └─────────────────────────────────────────────────────────────┘

    Args:
        db: Sesión activa de SQLAlchemy.
        prestamo_id: ID del préstamo a devolver.
        fecha_devolucion: Fecha real de devolución. Si es None, se usa
                          la fecha actual del servidor.

    Returns:
        Diccionario con el préstamo actualizado, un mensaje descriptivo,
        y la sanción (si se generó).

    Raises:
        HTTPException: Si el préstamo no existe o ya fue devuelto.
    """

    # ── Paso 1: Verificar existencia del préstamo ──────────────
    prestamo = obtener_prestamo_por_id(db, prestamo_id)
    if not prestamo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Préstamo con ID {prestamo_id} no encontrado.",
        )

    # ── Paso 2: Verificar que el préstamo siga en curso ────────
    # Se aceptan préstamos ACTIVO o VENCIDO (ambos siguen sin devolverse).
    if prestamo.estado not in ESTADOS_EN_CURSO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El préstamo con ID {prestamo_id} ya fue procesado. "
                f"Estado actual: {prestamo.estado.value}."
            ),
        )

    # ── Paso 3: Registrar la fecha de devolución real ──────────
    fecha_real = fecha_devolucion or date.today()
    prestamo.fecha_devolucion_real = fecha_real

    # ── Paso 4: Cambiar estado del préstamo a DEVUELTO ─────────
    prestamo.estado = EstadoPrestamo.DEVUELTO

    # ── Paso 5: Cambiar estado del ejemplar a DISPONIBLE ───────
    prestamo.ejemplar.estado = EstadoEjemplar.DISPONIBLE

    # ── Paso 6: Verificar si la devolución es tardía ───────────
    sancion = None
    if fecha_real > prestamo.fecha_vencimiento:
        # Calcular los días de retraso y el monto de la multa
        dias_retraso = (fecha_real - prestamo.fecha_vencimiento).days
        monto_multa = round(dias_retraso * MULTA_POR_DIA, 2)

        # La sanción es proporcional: el doble de los días de retraso
        dias_sancion = dias_retraso * 2
        sancion = Sancion(
            usuario_id=prestamo.usuario_id,
            prestamo_id=prestamo.id,
            tipo=TipoSancion.MORA,
            monto=monto_multa,
            fecha_inicio=fecha_real,
            fecha_fin=fecha_real + timedelta(days=dias_sancion),
        )
        db.add(sancion)

        # Actualizar el estado del usuario a SANCIONADO
        prestamo.usuario.estado = EstadoUsuario.SANCIONADO

    # ── Paso 7: Confirmar transacción ──────────────────────────
    db.commit()
    db.refresh(prestamo)
    if sancion:
        db.refresh(sancion)

    # Construir respuesta descriptiva
    if sancion:
        mensaje = (
            f"Devolución registrada con RETRASO de {dias_retraso} día(s). "
            f"Se generó una sanción por mora de ${monto_multa:.2f}. "
            f"La sanción vence el {sancion.fecha_fin}."
        )
    else:
        mensaje = "Devolución registrada exitosamente dentro del plazo."

    # Avisar al personal si el libro devuelto tiene reservas pendientes,
    # para que pueda retenerlo para el próximo usuario en la lista.
    pendientes = reservas_pendientes_libro(db, prestamo.ejemplar.libro_id)
    if pendientes:
        mensaje += f" Atención: este libro tiene {len(pendientes)} reserva(s) pendiente(s)."

    return {
        "prestamo": prestamo,
        "sancion": sancion,
        "mensaje": mensaje,
    }
