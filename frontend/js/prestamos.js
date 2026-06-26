/**
 * ═══════════════════════════════════════════════════════════════
 *  Panel de Préstamos — Lógica del formulario bibliotecario
 * ═══════════════════════════════════════════════════════════════
 */

document.addEventListener("DOMContentLoaded", () => {
    if (!requireStaff()) return;

    const inputDni = document.getElementById("input-dni");
    const inputNombre = document.getElementById("input-nombre");
    const inputLibroId = document.getElementById("input-libro-id");
    const btnPrestar = document.getElementById("btn-prestar");
    const previewUsuario = document.getElementById("preview-usuario");
    const previewLibro = document.getElementById("preview-libro");

    // Estado de validación
    let usuarioValidado = null; // Objeto usuario si está OK
    let libroValidado = null;   // Objeto disponibilidad si está OK

    let dniTimer = null;
    let libroTimer = null;
    // Identifica la última búsqueda lanzada para descartar respuestas
    // que llegan fuera de orden.
    let busquedaSeq = 0;
    // Candidatos de la última búsqueda, para resolver la selección por clic.
    let candidatos = [];

    // ── Búsqueda de usuario por DNI o nombre (debounce) ────────
    [inputDni, inputNombre].forEach((input) =>
        input.addEventListener("input", () => {
            clearTimeout(dniTimer);
            usuarioValidado = null;
            actualizarBoton();

            const dni = inputDni.value.trim();
            const nombre = inputNombre.value.trim();
            if (!dni && !nombre) {
                busquedaSeq++; // invalida respuestas en vuelo
                candidatos = [];
                previewUsuario.innerHTML = "";
                return;
            }

            dniTimer = setTimeout(() => buscarCandidatos({ dni, nombre }), 400);
        })
    );

    // Selección de un candidato de la lista (delegación de eventos).
    previewUsuario.addEventListener("click", (e) => {
        const card = e.target.closest("[data-candidato-idx]");
        if (!card) return;
        const usuario = candidatos[Number(card.dataset.candidatoIdx)];
        if (usuario) seleccionarUsuario(usuario);
    });

    // ── Búsqueda de libro por ID (debounce) ────────────────────
    inputLibroId.addEventListener("input", () => {
        clearTimeout(libroTimer);
        libroValidado = null;
        actualizarBoton();

        const id = inputLibroId.value.trim();
        if (!id) {
            previewLibro.innerHTML = "";
            return;
        }

        libroTimer = setTimeout(() => verificarLibro(parseInt(id)), 500);
    });

    inputLibroId.addEventListener("blur", () => {
        const id = inputLibroId.value.trim();
        if (id && !libroValidado) {
            clearTimeout(libroTimer);
            verificarLibro(parseInt(id));
        }
    });

    // ── Registrar Préstamo ─────────────────────────────────────
    btnPrestar.addEventListener("click", async () => {
        if (!usuarioValidado || !libroValidado) return;

        btnPrestar.disabled = true;
        btnPrestar.innerHTML = `<div class="spinner"></div> Procesando...`;

        try {
            const prestamo = await registrarPrestamo(
                usuarioValidado.id,
                libroValidado.libro_id
            );

            showToast(
                "success",
                "Préstamo registrado",
                `Ejemplar #${prestamo.ejemplar_id} prestado a ${usuarioValidado.nombre} ${usuarioValidado.apellido}. ` +
                `Vence el ${prestamo.fecha_vencimiento}.`
            );

            // Limpiar formulario
            inputDni.value = "";
            inputNombre.value = "";
            inputLibroId.value = "";
            previewUsuario.innerHTML = "";
            previewLibro.innerHTML = "";
            usuarioValidado = null;
            libroValidado = null;
            candidatos = [];
        } catch (error) {
            showToast("error", "Error al registrar", error.message);
        } finally {
            btnPrestar.disabled = false;
            btnPrestar.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="12" y1="18" x2="12" y2="12"/>
                    <line x1="9" y1="15" x2="15" y2="15"/>
                </svg>
                Registrar Préstamo
            `;
            actualizarBoton();
        }
    });

    // ── Helpers ─────────────────────────────────────────────────

    // Busca candidatos por prefijo de DNI y/o nombre y muestra la lista.
    // Atajo: si se escribió un DNI que coincide EXACTO con un candidato,
    // se selecciona automáticamente (flujo rápido del bibliotecario).
    async function buscarCandidatos({ dni, nombre }) {
        const seq = ++busquedaSeq;
        previewUsuario.innerHTML = `<div class="preview-card"><div class="preview-value" style="color:var(--text-muted)">Buscando...</div></div>`;

        try {
            const usuarios = await buscarUsuarios({ dni: dni || null, nombre: nombre || null });
            if (seq !== busquedaSeq) return; // llegó una búsqueda más nueva

            candidatos = usuarios;

            if (!usuarios.length) {
                previewUsuario.innerHTML = `
                    <div class="preview-card">
                        <div class="preview-value" style="color:var(--text-muted);font-size:.9rem">No se encontraron usuarios que coincidan.</div>
                    </div>`;
                return;
            }

            // Atajo: DNI completo que coincide exacto → seleccionar directo.
            if (dni) {
                const exacto = usuarios.find((u) => u.dni === dni);
                if (exacto) {
                    seleccionarUsuario(exacto);
                    return;
                }
            }

            // Si hay un único resultado, también se autoselecciona.
            if (usuarios.length === 1) {
                seleccionarUsuario(usuarios[0]);
                return;
            }

            const items = usuarios.map(renderCandidato).join("");
            previewUsuario.innerHTML = `
                <div style="font-size:.8rem;color:var(--text-muted);margin:.5rem 0">
                    ${usuarios.length} usuarios — elegí uno para prestarle
                </div>
                <div style="display:flex;flex-direction:column;gap:.5rem">${items}</div>`;
        } catch (error) {
            if (seq !== busquedaSeq) return;
            usuarioValidado = null;
            previewUsuario.innerHTML = `
                <div class="preview-card preview-error">
                    <div class="preview-label">Error</div>
                    <div class="preview-value" style="color:var(--danger)">${escapeHtml(error.message)}</div>
                </div>
            `;
            actualizarBoton();
        }
    }

    // Tarjeta clickeable de un candidato dentro de la lista.
    function renderCandidato(usuario, idx) {
        return `
            <div class="preview-card" data-candidato-idx="${idx}" role="button" tabindex="0" style="cursor:pointer">
                <div class="preview-row">
                    <div>
                        <div class="preview-value">${escapeHtml(usuario.nombre)} ${escapeHtml(usuario.apellido)}</div>
                        <div style="font-size:.8rem;color:var(--text-muted)">DNI ${escapeHtml(usuario.dni)} · ${escapeHtml(usuario.email)}</div>
                    </div>
                    ${estadoBadge(usuario.estado)}
                </div>
            </div>`;
    }

    // Fija el usuario elegido como validado y muestra su ficha.
    function seleccionarUsuario(usuario) {
        usuarioValidado = usuario;
        candidatos = [];

        previewUsuario.innerHTML = `
            <div class="preview-card preview-success">
                <div class="preview-row">
                    <div>
                        <div class="preview-label">Usuario Seleccionado</div>
                        <div class="preview-value">${escapeHtml(usuario.nombre)} ${escapeHtml(usuario.apellido)}</div>
                    </div>
                    ${estadoBadge(usuario.estado)}
                </div>
                <div class="preview-row" style="margin-top:8px">
                    <span style="font-size:0.8rem;color:var(--text-muted)">ID: ${usuario.id} · DNI ${escapeHtml(usuario.dni)} · ${escapeHtml(usuario.email)}</span>
                    <span class="meta-tag">${usuario.rol}</span>
                </div>
            </div>
        `;
        actualizarBoton();
    }

    function estadoBadge(estado) {
        if (estado === "ACTIVO")
            return `<span class="badge badge-success"><span class="badge-dot"></span>Activo</span>`;
        if (estado === "SANCIONADO")
            return `<span class="badge badge-danger"><span class="badge-dot"></span>Sancionado</span>`;
        return `<span class="badge badge-warning">Inactivo</span>`;
    }

    async function verificarLibro(libroId) {
        if (isNaN(libroId) || libroId < 1) {
            previewLibro.innerHTML = "";
            return;
        }

        previewLibro.innerHTML = `<div class="preview-card"><div class="preview-value" style="color:var(--text-muted)">Verificando...</div></div>`;
        try {
            const disp = await consultarDisponibilidad(libroId);
            libroValidado = disp;

            const disponible = disp.ejemplares_disponibles > 0;

            previewLibro.innerHTML = `
                <div class="preview-card ${disponible ? "preview-success" : "preview-error"}">
                    <div class="preview-row">
                        <div>
                            <div class="preview-label">Libro Encontrado</div>
                            <div class="preview-value">${escapeHtml(disp.titulo)}</div>
                        </div>
                        <span class="badge ${disponible ? "badge-success" : "badge-danger"}">
                            <span class="badge-dot"></span>
                            ${disp.ejemplares_disponibles}/${disp.total_ejemplares} disp.
                        </span>
                    </div>
                    <div style="margin-top:6px;font-size:0.8rem;color:var(--text-muted)">ISBN: ${escapeHtml(disp.isbn)}</div>
                </div>
            `;

            if (!disponible) {
                libroValidado = null; // No se puede prestar
            }
        } catch (error) {
            libroValidado = null;
            previewLibro.innerHTML = `
                <div class="preview-card preview-error">
                    <div class="preview-label">Error</div>
                    <div class="preview-value" style="color:var(--danger)">${escapeHtml(error.message)}</div>
                </div>
            `;
        }
        actualizarBoton();
    }

    function actualizarBoton() {
        btnPrestar.disabled = !(usuarioValidado && libroValidado);
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
