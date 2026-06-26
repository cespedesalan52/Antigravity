/**
 * ═══════════════════════════════════════════════════════════════
 *  Conocimiento Abierto — API Client Module
 *  Centralized HTTP communication layer using Fetch API
 * ═══════════════════════════════════════════════════════════════
 */

// Vacío = mismo origen. El frontend y la API ahora se sirven juntos
// desde FastAPI, así que las peticiones van al mismo host que sirvió la web.
// Esto permite compartir la app por un túnel (Cloudflare/ngrok) sin cambiar nada.
const BASE_URL = "";

/**
 * Realiza una petición HTTP al backend de FastAPI.
 *
 * Maneja automáticamente:
 * - Serialización del body a JSON
 * - Headers de Content-Type
 * - Parseo de errores del backend (campo "detail")
 *
 * @param {string} endpoint - Ruta relativa (ej: "/libros/")
 * @param {object} options - Opciones de fetch (method, body, etc.)
 * @returns {Promise<any>} Los datos de la respuesta parseados como JSON
 * @throws {Error} Con el mensaje del backend si la respuesta no es OK
 */
async function fetchAPI(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`;

    const token = localStorage.getItem("token");
    const config = {
        headers: {
            "Content-Type": "application/json",
            // Adjunta el token de sesión si el usuario inició sesión
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...options.headers,
        },
        ...options,
    };

    // Serializar body si es un objeto
    if (config.body && typeof config.body === "object") {
        config.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, config);

    // Sesión expirada o token inválido: limpiar y volver al login.
    // Se excluyen los endpoints de /auth/ (login/registro) para no interferir
    // con el manejo de credenciales incorrectas en esas pantallas.
    if (response.status === 401 && !endpoint.startsWith("/auth/")) {
        localStorage.removeItem("token");
        localStorage.removeItem("usuario");
        if (!window.location.pathname.endsWith("login.html")) {
            window.location.href = "login.html";
        }
    }

    // Parsear el body de la respuesta.
    // Se lee como texto primero para soportar respuestas sin cuerpo
    // (p. ej. 204 No Content en un DELETE), que romperían response.json().
    let data = null;
    const raw = await response.text();
    if (raw) {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            try {
                data = JSON.parse(raw);
            } catch {
                data = raw;
            }
        } else {
            data = raw;
        }
    }

    // Si la respuesta no es exitosa, lanzar error con el detalle del backend
    if (!response.ok) {
        let errorMessage;
        if (data && data.detail) {
            if (typeof data.detail === "string") {
                errorMessage = data.detail;
            } else if (Array.isArray(data.detail)) {
                // Errores de validación de FastAPI: [{loc, msg, type}]
                errorMessage = data.detail.map((e) => e.msg || JSON.stringify(e)).join(", ");
            } else {
                errorMessage = JSON.stringify(data.detail);
            }
        } else if (typeof data === "string" && data) {
            errorMessage = data;
        } else {
            errorMessage = `Error ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
    }

    return data;
}

/* ── Autenticación / Sesión ──────────────────────────────────── */

/**
 * Inicia sesión: valida credenciales y guarda el token y el usuario.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>} El usuario autenticado
 */
async function loginRequest(email, password) {
    const data = await fetchAPI("/auth/login", {
        method: "POST",
        body: { email, password },
    });
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("usuario", JSON.stringify(data.usuario));
    return data.usuario;
}

/**
 * Auto-registro de un nuevo usuario (estudiante o docente) e inicio de sesión.
 * @param {object} datos - { nombre, apellido, dni, email, password, rol }
 * @returns {Promise<object>} El usuario creado (queda con sesión iniciada)
 */
async function registroRequest(datos) {
    const data = await fetchAPI("/auth/registro", {
        method: "POST",
        body: datos,
    });
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("usuario", JSON.stringify(data.usuario));
    return data.usuario;
}

/**
 * Cierra la sesión actual y redirige al login.
 */
function cerrarSesion() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    window.location.href = "login.html";
}

/**
 * Devuelve el usuario actualmente logueado, o null si no hay sesión.
 * @returns {object|null}
 */
function getUsuarioActual() {
    try {
        const raw = localStorage.getItem("usuario");
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

/**
 * Indica si el usuario logueado es personal autorizado (bibliotecario/admin).
 * @returns {boolean}
 */
function esStaff() {
    const usuario = getUsuarioActual();
    return !!usuario && (usuario.rol === "BIBLIOTECARIO" || usuario.rol === "ADMINISTRADOR");
}

/**
 * Guardia de página: exige sesión iniciada. Si no hay, redirige al login.
 * @returns {boolean} true si hay sesión; false si se está redirigiendo.
 */
function requireAuth() {
    if (!localStorage.getItem("token") || !getUsuarioActual()) {
        window.location.href = "login.html";
        return false;
    }
    return true;
}

/**
 * Guardia de página: exige sesión iniciada Y rol de personal autorizado.
 * Sin sesión → login; logueado pero sin permiso → dashboard.
 * @returns {boolean} true si es staff; false si se está redirigiendo.
 */
function requireStaff() {
    if (!requireAuth()) return false;
    if (!esStaff()) {
        window.location.href = "dashboard.html";
        return false;
    }
    return true;
}

/* ── Funciones de la API ─────────────────────────────────────── */

/**
 * Lista los libros del catálogo con búsqueda opcional.
 * @param {string|null} busqueda - Término de búsqueda (título o autor)
 * @returns {Promise<Array>} Lista de libros
 */
async function buscarLibros(busqueda = null, skip = 0, limit = 12) {
    const params = new URLSearchParams();
    if (busqueda) params.set("busqueda", busqueda);
    params.set("skip", skip);
    params.set("limit", limit);
    // Devuelve { total, skip, limit, items }
    return fetchAPI(`/libros/?${params.toString()}`);
}

/**
 * Consulta la disponibilidad de un libro específico.
 * @param {number} libroId - ID del libro
 * @returns {Promise<object>} Datos de disponibilidad
 */
async function consultarDisponibilidad(libroId) {
    return fetchAPI(`/libros/${libroId}/disponibilidad`);
}

/**
 * Busca un usuario por su DNI.
 * @param {string} dni - Documento Nacional de Identidad
 * @returns {Promise<object>} Datos del usuario
 */
async function buscarUsuarioPorDNI(dni) {
    return fetchAPI(`/usuarios/buscar?dni=${encodeURIComponent(dni)}`);
}

/**
 * Busca usuarios de forma incremental por prefijo de DNI y/o por nombre.
 * A diferencia de `buscarUsuarioPorDNI` (coincidencia exacta), devuelve una
 * lista de coincidencias para mostrar mientras se escribe.
 * @param {{dni?: string, nombre?: string}} filtros
 * @returns {Promise<Array>} Lista de usuarios coincidentes
 */
async function buscarUsuarios({ dni = null, nombre = null } = {}) {
    const params = new URLSearchParams();
    if (dni) params.set("dni", dni);
    if (nombre) params.set("nombre", nombre);
    const query = params.toString();
    return fetchAPI(`/usuarios/${query ? "?" + query : ""}`);
}

/**
 * Registra un nuevo préstamo.
 * @param {number} usuarioId - ID del usuario
 * @param {number} libroId - ID del libro
 * @returns {Promise<object>} Datos del préstamo creado
 */
async function registrarPrestamo(usuarioId, libroId) {
    return fetchAPI("/prestamos/", {
        method: "POST",
        body: { usuario_id: usuarioId, libro_id: libroId },
    });
}

/**
 * Registra la devolución de un préstamo.
 * @param {number} prestamoId - ID del préstamo
 * @param {string|null} fechaDevolucion - Fecha en formato YYYY-MM-DD (opcional)
 * @returns {Promise<object>} Datos de la devolución con posible sanción
 */
async function registrarDevolucion(prestamoId, fechaDevolucion = null) {
    const body = {};
    if (fechaDevolucion) body.fecha_devolucion = fechaDevolucion;
    return fetchAPI(`/prestamos/${prestamoId}/devolucion`, {
        method: "POST",
        body,
    });
}

/**
 * Lista préstamos con filtros opcionales (solo personal).
 * @param {{estado?: string, dni?: string}} filtros
 * @returns {Promise<Array>} Lista de préstamos enriquecidos
 */
async function listarPrestamos(filtros = {}) {
    const params = new URLSearchParams();
    if (filtros.estado) params.set("estado", filtros.estado);
    if (filtros.dni) params.set("dni", filtros.dni);
    const query = params.toString();
    return fetchAPI(`/prestamos/${query ? "?" + query : ""}`);
}

/**
 * Lista sanciones con filtros opcionales (solo personal).
 * @param {{dni?: string, soloVigentes?: boolean}} filtros
 * @returns {Promise<Array>} Lista de sanciones enriquecidas
 */
async function listarSanciones(filtros = {}) {
    const params = new URLSearchParams();
    if (filtros.dni) params.set("dni", filtros.dni);
    if (filtros.soloVigentes) params.set("solo_vigentes", "true");
    const query = params.toString();
    return fetchAPI(`/sanciones/${query ? "?" + query : ""}`);
}

/**
 * Salda (paga) una sanción (solo personal).
 * @param {number} sancionId - ID de la sanción
 * @returns {Promise<object>} La sanción actualizada
 */
async function pagarSancion(sancionId) {
    return fetchAPI(`/sanciones/${sancionId}/pagar`, { method: "POST" });
}

/* ── Estadísticas ────────────────────────────────────────────── */

/** Obtiene las métricas globales de la biblioteca para el dashboard. */
async function obtenerStats() {
    return fetchAPI("/stats/");
}

/* ── Categorías ──────────────────────────────────────────────── */

/** Lista todas las categorías. */
async function listarCategorias() {
    return fetchAPI("/categorias/");
}

/** Crea una categoría (solo personal). */
async function crearCategoria(nombre) {
    return fetchAPI("/categorias/", { method: "POST", body: { nombre } });
}

/* ── Reservas ────────────────────────────────────────────────── */

/** Reserva un libro sin ejemplares disponibles para el usuario logueado. */
async function reservarLibro(libroId) {
    return fetchAPI("/reservas/", { method: "POST", body: { libro_id: libroId } });
}

/** Lista las reservas del usuario logueado. */
async function listarMisReservas() {
    return fetchAPI("/reservas/mias");
}

/**
 * Lista todas las reservas (solo personal), con filtros opcionales.
 * @param {{dni?: string, estado?: string}} filtros
 */
async function listarReservas(filtros = {}) {
    const params = new URLSearchParams();
    if (filtros.dni) params.set("dni", filtros.dni);
    if (filtros.estado) params.set("estado", filtros.estado);
    const query = params.toString();
    return fetchAPI(`/reservas/${query ? "?" + query : ""}`);
}

/** Cancela una reserva (propia, o cualquiera si es personal). */
async function cancelarReserva(reservaId) {
    return fetchAPI(`/reservas/${reservaId}/cancelar`, { method: "POST" });
}

/* ── Toast Notifications ─────────────────────────────────────── */

/**
 * Muestra una notificación toast.
 * @param {"success"|"error"|"warning"|"info"} type
 * @param {string} title
 * @param {string} message
 * @param {number} duration - Milisegundos antes de desaparecer (default 5000)
 */
function showToast(type, title, message, duration = 5000) {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const icons = {
        success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
        error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
        warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    };

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        ${icons[type] || icons.info}
        <div class="toast-body">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.classList.add('toast-exit'); setTimeout(() => this.parentElement.remove(), 300);">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
    `;

    container.appendChild(toast);

    // Auto-remove
    setTimeout(() => {
        toast.classList.add("toast-exit");
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Registra un nuevo usuario.
 * @param {object} datos - { nombre, apellido, dni, email, password, rol }
 * @returns {Promise<object>} Datos del usuario creado
 */
async function registrarUsuario(datos) {
    return fetchAPI("/usuarios/", {
        method: "POST",
        body: datos,
    });
}

/**
 * Crea un nuevo libro en el catálogo.
 * @param {object} datos - { titulo, autor, isbn, editorial, anio, categoria_id, cantidad_ejemplares }
 * @returns {Promise<object>} Datos del libro creado
 */
async function crearLibro(datos) {
    return fetchAPI("/libros/", {
        method: "POST",
        body: datos,
    });
}

/**
 * Actualiza un libro existente (actualización parcial).
 *
 * Si `datos.cantidad_ejemplares` se incluye, representa el TOTAL deseado de
 * copias: el backend crea o elimina ejemplares aplicando las reglas de negocio.
 *
 * @param {number} libroId - ID del libro a modificar
 * @param {object} datos - Campos a actualizar (solo se envían los provistos)
 * @returns {Promise<object>} Datos del libro actualizado
 */
async function actualizarLibro(libroId, datos) {
    return fetchAPI(`/libros/${libroId}`, {
        method: "PUT",
        body: datos,
    });
}

/**
 * Elimina un libro del catálogo.
 *
 * El backend rechaza la eliminación (HTTP 409) si el libro tiene préstamos
 * activos, reservas pendientes o sanciones vigentes.
 *
 * @param {number} libroId - ID del libro a eliminar
 * @returns {Promise<any>} Vacío si se eliminó correctamente (HTTP 204)
 */
async function eliminarLibro(libroId) {
    return fetchAPI(`/libros/${libroId}`, {
        method: "DELETE",
    });
}

/* ── Modal Helpers ────────────────────────────────────────────── */

/**
 * Abre el modal de sanción con los datos de la devolución tardía.
 * @param {object} sancion - Datos de la sanción del backend
 * @param {string} mensaje - Mensaje descriptivo del backend
 */
function showSancionModal(sancion, mensaje) {
    const overlay = document.getElementById("modal-overlay");
    if (!overlay) return;

    // Poblar datos
    const setEl = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    setEl("modal-monto", `$${sancion.monto.toFixed(2)}`);
    setEl("modal-tipo", sancion.tipo);
    setEl("modal-fecha-inicio", sancion.fecha_inicio);
    setEl("modal-fecha-fin", sancion.fecha_fin || "Indefinida");
    setEl("modal-mensaje", mensaje);

    overlay.classList.add("active");
}

/**
 * Cierra el modal activo.
 */
function closeModal() {
    const overlay = document.getElementById("modal-overlay");
    if (overlay) overlay.classList.remove("active");
}
