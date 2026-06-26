/**
 * Gestión de Usuarios — Registro y búsqueda
 */

document.addEventListener("DOMContentLoaded", () => {
    // Panel de personal: exige rol bibliotecario/administrador.
    if (!requireStaff()) return;

    const btnRegistrar = document.getElementById("btn-registrar");
    const inputBuscarDni = document.getElementById("input-buscar-dni");
    const inputBuscarNombre = document.getElementById("input-buscar-nombre");
    const previewBusqueda = document.getElementById("preview-usuario-busqueda");

    let debounceTimer = null;
    // Identifica la última búsqueda lanzada para descartar respuestas
    // fuera de orden (una consulta lenta que llega después de una más nueva).
    let busquedaSeq = 0;

    // ── Registro ───────────────────────────────────────────────
    btnRegistrar.addEventListener("click", async () => {
        const nombre = document.getElementById("input-nombre").value.trim();
        const apellido = document.getElementById("input-apellido").value.trim();
        const dni = document.getElementById("input-dni").value.trim();
        const email = document.getElementById("input-email").value.trim();
        const password = document.getElementById("input-password").value;
        const rol = document.getElementById("input-rol").value;

        if (!nombre || !apellido || !dni || !email || !password) {
            showToast("warning", "Campos incompletos", "Completa todos los campos antes de registrar.");
            return;
        }

        if (password.length < 8) {
            showToast("warning", "Contraseña muy corta", "La contraseña debe tener al menos 8 caracteres.");
            return;
        }

        btnRegistrar.disabled = true;
        btnRegistrar.innerHTML = `<div class="spinner"></div> Registrando...`;

        try {
            await registrarUsuario({ nombre, apellido, dni, email, contrasena: password, rol });
            showToast("success", "Usuario registrado", `${nombre} ${apellido} fue registrado exitosamente.`);
            limpiarFormulario();
        } catch (error) {
            showToast("error", "Error al registrar", error.message);
        } finally {
            btnRegistrar.disabled = false;
            btnRegistrar.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="8.5" cy="7" r="4"/>
                    <line x1="20" y1="8" x2="20" y2="14"/>
                    <line x1="23" y1="11" x2="17" y2="11"/>
                </svg>
                Registrar Usuario`;
        }
    });

    // ── Búsqueda incremental con debounce ──────────────────────
    // Ambos campos disparan la misma búsqueda combinada (DNI por prefijo,
    // nombre/apellido por coincidencia parcial).
    [inputBuscarDni, inputBuscarNombre].forEach((input) =>
        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const dni = inputBuscarDni.value.trim();
            const nombre = inputBuscarNombre.value.trim();

            if (!dni && !nombre) {
                busquedaSeq++; // invalida cualquier respuesta en vuelo
                previewBusqueda.innerHTML = "";
                return;
            }

            debounceTimer = setTimeout(() => buscarUsuarios_({ dni, nombre }), 400);
        })
    );

    async function buscarUsuarios_({ dni, nombre }) {
        const seq = ++busquedaSeq;
        previewBusqueda.innerHTML = `<div class="preview-card"><span style="color:var(--text-muted);font-size:.85rem">Buscando...</span></div>`;

        try {
            const usuarios = await buscarUsuarios({ dni: dni || null, nombre: nombre || null });
            if (seq !== busquedaSeq) return; // llegó una búsqueda más nueva

            if (!usuarios.length) {
                previewBusqueda.innerHTML = `
                    <div class="preview-card">
                        <span style="font-size:.85rem;color:var(--text-muted)">No se encontraron usuarios que coincidan.</span>
                    </div>`;
                return;
            }

            const tarjetas = usuarios.map(renderUsuarioCard).join("");
            const resumen =
                usuarios.length === 1
                    ? "1 usuario encontrado"
                    : `${usuarios.length} usuarios encontrados`;
            previewBusqueda.innerHTML = `
                <div class="busqueda-resumen" style="font-size:.8rem;color:var(--text-muted);margin:.5rem 0">${resumen}</div>
                <div class="busqueda-resultados" style="display:flex;flex-direction:column;gap:.6rem">${tarjetas}</div>`;
        } catch (error) {
            if (seq !== busquedaSeq) return;
            previewBusqueda.innerHTML = `
                <div class="preview-card preview-error">
                    <span style="font-size:.85rem;color:var(--danger)">${escapeHtml(error.message)}</span>
                </div>`;
        }
    }

    function renderUsuarioCard(usuario) {
        return `
            <div class="preview-card preview-success">
                <div class="preview-row">
                    <span class="preview-label">Nombre</span>
                    <span class="preview-value">${escapeHtml(usuario.nombre)} ${escapeHtml(usuario.apellido)}</span>
                </div>
                <div class="preview-row">
                    <span class="preview-label">DNI</span>
                    <span class="preview-value">${escapeHtml(usuario.dni)}</span>
                </div>
                <div class="preview-row">
                    <span class="preview-label">Email</span>
                    <span class="preview-value">${escapeHtml(usuario.email)}</span>
                </div>
                <div class="preview-row">
                    <span class="preview-label">Rol</span>
                    <span class="preview-value">
                        <span class="badge badge-info">${escapeHtml(usuario.rol)}</span>
                    </span>
                </div>
            </div>`;
    }

    function limpiarFormulario() {
        ["input-nombre", "input-apellido", "input-dni", "input-email", "input-password"].forEach(
            (id) => (document.getElementById(id).value = "")
        );
        document.getElementById("input-rol").value = "ESTUDIANTE";
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
