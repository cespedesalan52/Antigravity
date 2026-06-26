/**
 * ═══════════════════════════════════════════════════════════════
 *  Catálogo de Libros — Lógica de la vista principal
 * ═══════════════════════════════════════════════════════════════
 */

/* ── Estado del catálogo ─────────────────────────────────────── */

// Caché de los libros actualmente cargados, para poder precargar el modal
// de edición sin pedir de nuevo los datos al backend.
let _librosCargados = [];

// Categorías cargadas (para los selectores de los modales de libro).
let _categorias = [];

function _esc(text) {
    const d = document.createElement("div");
    d.textContent = text == null ? "" : text;
    return d.innerHTML;
}

/* ── Categorías ──────────────────────────────────────────────── */

async function cargarCategorias() {
    try {
        _categorias = await listarCategorias();
    } catch {
        _categorias = [];
    }
    poblarSelectCategorias("libro-categoria");
    poblarSelectCategorias("edit-libro-categoria");
}

function poblarSelectCategorias(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const valorActual = sel.value;
    sel.innerHTML =
        '<option value="">Sin categoría</option>' +
        _categorias.map((c) => `<option value="${c.id}">${_esc(c.nombre)}</option>`).join("");
    sel.value = valorActual;
}

/** Crea una categoría desde un prompt y la selecciona en el selector dado. */
async function nuevaCategoria(selectId) {
    const nombre = (prompt("Nombre de la nueva categoría:") || "").trim();
    if (!nombre) return;
    try {
        const cat = await crearCategoria(nombre);
        await cargarCategorias();
        const sel = document.getElementById(selectId);
        if (sel) sel.value = String(cat.id);
        showToast("success", "Categoría creada", `"${cat.nombre}" se agregó al catálogo.`);
    } catch (error) {
        showToast("error", "No se pudo crear la categoría", error.message);
    }
}

/* ── Reservas ────────────────────────────────────────────────── */

/** Reserva un libro sin stock para el usuario logueado. */
async function reservarLibroUI(libroId) {
    try {
        await reservarLibro(libroId);
        showToast("success", "Reserva registrada", "Te avisaremos cuando haya un ejemplar disponible.");
    } catch (error) {
        showToast("error", "No se pudo reservar", error.message);
    }
}

/* ── Modal de Registro de Libro ──────────────────────────────── */

function cerrarModalLibro() {
    document.getElementById("modal-libro-overlay").classList.remove("active");
}

function limpiarFormularioLibro() {
    ["libro-titulo", "libro-autor", "libro-isbn", "libro-editorial", "libro-anio", "libro-categoria"].forEach(
        (id) => (document.getElementById(id).value = "")
    );
    document.getElementById("libro-ejemplares").value = "1";
}

/* ── Modal de Edición de Libro ───────────────────────────────── */

function cerrarModalEditarLibro() {
    document.getElementById("modal-editar-libro-overlay").classList.remove("active");
}

/**
 * Abre el modal de edición precargado con los datos de un libro.
 * @param {number} libroId - ID del libro a editar
 */
function abrirEditarLibro(libroId) {
    const libro = _librosCargados.find((l) => l.id === libroId);
    if (!libro) return;

    const ejemplares = libro.ejemplares || [];
    const total = ejemplares.length;
    const disponibles = ejemplares.filter((e) => e.estado === "DISPONIBLE").length;
    const noDisponibles = total - disponibles;

    document.getElementById("edit-libro-id").value = libro.id;
    document.getElementById("edit-libro-titulo").value = libro.titulo || "";
    document.getElementById("edit-libro-autor").value = libro.autor || "";
    document.getElementById("edit-libro-isbn").value = libro.isbn || "";
    document.getElementById("edit-libro-editorial").value = libro.editorial || "";
    document.getElementById("edit-libro-anio").value = libro.anio || "";
    document.getElementById("edit-libro-categoria").value = libro.categoria_id ? String(libro.categoria_id) : "";

    const inputEjemplares = document.getElementById("edit-libro-ejemplares");
    inputEjemplares.value = total;
    // No se puede bajar de la cantidad de copias no disponibles (prestadas, etc.)
    inputEjemplares.min = noDisponibles;

    document.getElementById("edit-ejemplares-info").textContent =
        `Actualmente: ${total} ejemplar(es) — ${disponibles} disponible(s), ${noDisponibles} en préstamo u otro estado. ` +
        (noDisponibles > 0
            ? `No puedes reducir por debajo de ${noDisponibles}.`
            : "Puedes ajustar la cantidad libremente.");

    document.getElementById("modal-editar-libro-overlay").classList.add("active");
}

/* ── Modal de Eliminación de Libro ───────────────────────────── */

function cerrarModalEliminarLibro() {
    document.getElementById("modal-eliminar-libro-overlay").classList.remove("active");
}

/**
 * Abre el modal de confirmación para eliminar un libro.
 * @param {number} libroId - ID del libro a eliminar
 */
function abrirEliminarLibro(libroId) {
    const libro = _librosCargados.find((l) => l.id === libroId);
    if (!libro) return;

    document.getElementById("eliminar-libro-id").value = libro.id;
    document.getElementById("eliminar-libro-titulo").textContent = `«${libro.titulo}»`;
    document.getElementById("modal-eliminar-libro-overlay").classList.add("active");
}

/* ── Catálogo ─────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
    if (!requireAuth()) return;

    const searchInput = document.getElementById("search-input");
    const bookGrid = document.getElementById("book-grid");
    const emptyState = document.getElementById("empty-state");

    const paginacion = document.getElementById("paginacion");

    // ── Estado de paginación ───────────────────────────────────
    const TAM_PAGINA = 12;
    let paginaActual = 0;
    let busquedaActual = null;

    let debounceTimer = null;

    // ── Solo el personal autorizado puede registrar/editar/eliminar ──
    if (!esStaff()) {
        const btnRegistrar = document.getElementById("btn-abrir-modal-libro");
        if (btnRegistrar) btnRegistrar.style.display = "none";
    }

    // ── Carga inicial ──────────────────────────────────────────
    cargarCategorias();
    cargarCatalogo();

    // ── Búsqueda con debounce (vuelve a la primera página) ─────
    searchInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            busquedaActual = searchInput.value.trim() || null;
            paginaActual = 0;
            cargarCatalogo();
        }, 400);
    });

    // ── Modal: abrir ───────────────────────────────────────────
    document.getElementById("btn-abrir-modal-libro").addEventListener("click", () => {
        document.getElementById("modal-libro-overlay").classList.add("active");
    });

    // ── Modal: confirmar registro ──────────────────────────────
    document.getElementById("btn-confirmar-libro").addEventListener("click", async () => {
        const titulo = document.getElementById("libro-titulo").value.trim();
        const autor = document.getElementById("libro-autor").value.trim();
        const isbn = document.getElementById("libro-isbn").value.trim() || null;
        const editorial = document.getElementById("libro-editorial").value.trim() || null;
        const anio = parseInt(document.getElementById("libro-anio").value) || null;
        const ejemplares = parseInt(document.getElementById("libro-ejemplares").value) || 1;
        const categoriaId = parseInt(document.getElementById("libro-categoria").value) || null;

        if (!titulo || !autor) {
            showToast("warning", "Campos requeridos", "Título y autor son obligatorios.");
            return;
        }

        const btnConfirmar = document.getElementById("btn-confirmar-libro");
        btnConfirmar.disabled = true;
        btnConfirmar.innerHTML = `<div class="spinner"></div> Guardando...`;

        try {
            const body = { titulo, autor, isbn, editorial, anio, cantidad_ejemplares: ejemplares };
            if (categoriaId) body.categoria_id = categoriaId;

            await crearLibro(body);
            showToast("success", "Libro registrado", `"${titulo}" fue agregado al catálogo.`);
            cerrarModalLibro();
            limpiarFormularioLibro();
            paginaActual = 0;
            cargarCatalogo();
        } catch (error) {
            showToast("error", "Error al registrar", error.message);
        } finally {
            btnConfirmar.disabled = false;
            btnConfirmar.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                Agregar Libro`;
        }
    });

    // ── Modal Editar: confirmar cambios ────────────────────────
    document.getElementById("btn-confirmar-editar-libro").addEventListener("click", async () => {
        const libroId = parseInt(document.getElementById("edit-libro-id").value);
        const titulo = document.getElementById("edit-libro-titulo").value.trim();
        const autor = document.getElementById("edit-libro-autor").value.trim();
        const isbn = document.getElementById("edit-libro-isbn").value.trim();
        const editorial = document.getElementById("edit-libro-editorial").value.trim() || null;
        const anioRaw = document.getElementById("edit-libro-anio").value.trim();
        const anio = anioRaw ? parseInt(anioRaw) : null;
        const ejemplaresRaw = document.getElementById("edit-libro-ejemplares").value.trim();
        const categoriaRaw = document.getElementById("edit-libro-categoria").value.trim();
        const categoriaId = categoriaRaw ? parseInt(categoriaRaw) : null;

        if (!titulo || !autor || !isbn) {
            showToast("warning", "Campos requeridos", "Título, autor e ISBN son obligatorios.");
            return;
        }

        const cantidad = ejemplaresRaw === "" ? null : parseInt(ejemplaresRaw);
        if (cantidad !== null && (isNaN(cantidad) || cantidad < 0)) {
            showToast("warning", "Cantidad inválida", "La cantidad de ejemplares no puede ser negativa.");
            return;
        }

        const btn = document.getElementById("btn-confirmar-editar-libro");
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Guardando...`;

        try {
            const body = { titulo, autor, isbn, editorial, anio, categoria_id: categoriaId };
            if (cantidad !== null) body.cantidad_ejemplares = cantidad;

            await actualizarLibro(libroId, body);
            showToast("success", "Libro actualizado", `"${titulo}" se actualizó correctamente.`);
            cerrarModalEditarLibro();
            cargarCatalogo();
        } catch (error) {
            showToast("error", "Error al actualizar", error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6L9 17l-5-5"/>
                </svg>
                Guardar Cambios`;
        }
    });

    // ── Modal Eliminar: confirmar borrado ──────────────────────
    document.getElementById("btn-confirmar-eliminar-libro").addEventListener("click", async () => {
        const libroId = parseInt(document.getElementById("eliminar-libro-id").value);
        if (!libroId) return;

        const btn = document.getElementById("btn-confirmar-eliminar-libro");
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Eliminando...`;

        try {
            await eliminarLibro(libroId);
            showToast("success", "Libro eliminado", "El libro se quitó del catálogo.");
            cerrarModalEliminarLibro();
            cargarCatalogo();
        } catch (error) {
            showToast("error", "No se pudo eliminar", error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                Eliminar`;
        }
    });

    /**
     * Carga la página actual del catálogo y renderiza las tarjetas.
     */
    async function cargarCatalogo() {
        bookGrid.innerHTML = `
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
        `;
        emptyState.style.display = "none";
        if (paginacion) paginacion.innerHTML = "";

        // Las tarjetas de stats muestran totales GLOBALES (no de la página).
        actualizarStatsGlobales();

        try {
            const pagina = await buscarLibros(busquedaActual, paginaActual * TAM_PAGINA, TAM_PAGINA);
            _librosCargados = pagina.items;

            if (pagina.items.length === 0) {
                bookGrid.innerHTML = "";
                emptyState.style.display = "block";
                return;
            }

            renderizarLibros(pagina.items);
            renderPaginacion(pagina.total);
        } catch (error) {
            bookGrid.innerHTML = "";
            emptyState.style.display = "block";
            emptyState.querySelector("h3").textContent = "Error al cargar";
            emptyState.querySelector("p").textContent = error.message;
            showToast("error", "Error de conexión", error.message);
        }
    }

    /** Actualiza las tarjetas de estadísticas con totales globales del sistema. */
    async function actualizarStatsGlobales() {
        try {
            const s = await obtenerStats();
            document.getElementById("stat-total").textContent = s.total_libros;
            document.getElementById("stat-disponibles").textContent = s.ejemplares_disponibles;
            document.getElementById("stat-prestados").textContent = s.ejemplares_prestados;
        } catch {
            /* Si falla, no rompe el catálogo */
        }
    }

    /** Dibuja los controles de paginación (Anterior / Siguiente + contador). */
    function renderPaginacion(total) {
        if (!paginacion) return;
        if (total <= TAM_PAGINA && paginaActual === 0) {
            // Una sola página: solo el contador, sin botones.
            paginacion.innerHTML = `<span class="paginacion-info">${total} libro${total !== 1 ? "s" : ""}</span>`;
            return;
        }

        const inicio = paginaActual * TAM_PAGINA + 1;
        const fin = Math.min((paginaActual + 1) * TAM_PAGINA, total);
        const hayPrev = paginaActual > 0;
        const hayNext = fin < total;

        paginacion.innerHTML = `
            <button class="btn btn-secondary" id="pag-prev" ${hayPrev ? "" : "disabled"}>‹ Anterior</button>
            <span class="paginacion-info">Mostrando ${inicio}–${fin} de ${total}</span>
            <button class="btn btn-secondary" id="pag-next" ${hayNext ? "" : "disabled"}>Siguiente ›</button>
        `;

        const prev = document.getElementById("pag-prev");
        const next = document.getElementById("pag-next");
        if (prev) prev.onclick = () => { if (paginaActual > 0) { paginaActual--; cargarCatalogo(); } };
        if (next) next.onclick = () => { if (hayNext) { paginaActual++; cargarCatalogo(); } };
    }

    function renderizarLibros(libros) {
        bookGrid.innerHTML = "";

        libros.forEach((libro, index) => {
            const ejemplares = libro.ejemplares || [];
            const disponibles = ejemplares.filter((e) => e.estado === "DISPONIBLE").length;
            const total = ejemplares.length;

            const esDisponible = disponibles > 0;
            const badgeClass = esDisponible ? "badge-success" : "badge-danger";
            const badgeText = esDisponible
                ? `${disponibles} disponible${disponibles > 1 ? "s" : ""}`
                : "Sin stock";

            const card = document.createElement("div");
            card.className = "book-card fade-in";
            card.style.animationDelay = `${index * 60}ms`;
            card.innerHTML = `
                <div class="book-card-header">
                    <div class="book-title">${escapeHtml(libro.titulo)}</div>
                    ${esStaff() ? `
                    <div class="book-card-actions">
                        <button class="book-edit-btn" onclick="abrirEditarLibro(${libro.id})" title="Editar libro" aria-label="Editar libro">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                        </button>
                        <button class="book-delete-btn" onclick="abrirEliminarLibro(${libro.id})" title="Eliminar libro" aria-label="Eliminar libro">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                                <line x1="10" y1="11" x2="10" y2="17"/>
                                <line x1="14" y1="11" x2="14" y2="17"/>
                            </svg>
                        </button>
                    </div>` : ""}
                </div>
                <div class="book-author">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;opacity:0.5;">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                    ${escapeHtml(libro.autor)}
                </div>
                <div class="book-meta">
                    ${libro.isbn ? `<span class="meta-tag">ISBN: ${escapeHtml(libro.isbn)}</span>` : ""}
                    ${libro.editorial ? `<span class="meta-tag">${escapeHtml(libro.editorial)}</span>` : ""}
                    ${libro.anio ? `<span class="meta-tag">${libro.anio}</span>` : ""}
                    ${libro.categoria ? `<span class="meta-tag">📁 ${escapeHtml(libro.categoria.nombre)}</span>` : ""}
                </div>
                <div class="book-footer">
                    <span class="badge ${badgeClass}">
                        <span class="badge-dot"></span>
                        ${badgeText}
                    </span>
                    <span class="meta-tag">${total} ejemplar${total !== 1 ? "es" : ""}</span>
                </div>
                ${!esDisponible ? `
                <button class="btn btn-secondary" style="width:100%;margin-top:14px" onclick="reservarLibroUI(${libro.id})">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                    </svg>
                    Reservar
                </button>` : ""}
            `;

            bookGrid.appendChild(card);
        });
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
