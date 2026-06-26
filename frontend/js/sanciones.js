/**
 * ═══════════════════════════════════════════════════════════════
 *  Panel de Sanciones — Consulta y saldado de multas
 * ═══════════════════════════════════════════════════════════════
 */

document.addEventListener("DOMContentLoaded", () => {
    if (!requireStaff()) return;

    const inputDni = document.getElementById("input-dni");
    const selectVigentes = document.getElementById("check-vigentes");
    const resultado = document.getElementById("resultado-sanciones");

    let debounceTimer = null;

    // Carga inicial
    cargarSanciones();

    inputDni.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(cargarSanciones, 450);
    });
    selectVigentes.addEventListener("change", cargarSanciones);

    // Saldar (delegación de eventos)
    resultado.addEventListener("click", (e) => {
        const btn = e.target.closest(".btn-saldar");
        if (btn) saldar(parseInt(btn.dataset.sancionId), btn);
    });

    async function cargarSanciones() {
        const dni = inputDni.value.trim();
        const soloVigentes = selectVigentes.value === "vigentes";
        resultado.innerHTML = `<div class="form-panel"><span style="color:var(--text-muted)">Cargando sanciones...</span></div>`;
        try {
            const sanciones = await listarSanciones({ dni: dni || null, soloVigentes });
            renderSanciones(sanciones);
        } catch (error) {
            resultado.innerHTML = `<div class="form-panel"><span style="color:var(--danger)">${escapeHtml(error.message)}</span></div>`;
        }
    }

    function renderSanciones(sanciones) {
        if (sanciones.length === 0) {
            resultado.innerHTML = `
                <div class="form-panel" style="text-align:center;color:var(--text-muted)">
                    No hay sanciones que coincidan con el filtro.
                </div>`;
            return;
        }

        const cards = sanciones
            .map((s) => {
                const badge = s.vigente
                    ? `<span class="badge badge-danger"><span class="badge-dot"></span>Vigente</span>`
                    : `<span class="badge badge-success"><span class="badge-dot"></span>Saldada</span>`;
                const boton = s.vigente
                    ? `<button class="btn btn-primary btn-saldar" data-sancion-id="${s.id}" style="margin-top:12px">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M20 6L9 17l-5-5"/>
                            </svg>
                            Saldar sanción
                       </button>`
                    : "";
                return `
                <div class="preview-card ${s.vigente ? "preview-error" : ""}" style="margin-bottom:12px">
                    <div class="preview-row">
                        <div>
                            <div class="preview-label">${escapeHtml(s.usuario_nombre)} · DNI ${escapeHtml(s.usuario_dni)}</div>
                            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px">
                                ${escapeHtml(s.tipo)} · Préstamo #${s.prestamo_id} · desde ${s.fecha_inicio}${s.fecha_fin ? " hasta " + s.fecha_fin : ""}
                            </div>
                        </div>
                        <div style="text-align:right">
                            <div class="preview-value text-danger" style="font-size:1.1rem">$${s.monto.toFixed(2)}</div>
                            ${badge}
                        </div>
                    </div>
                    ${boton}
                </div>`;
            })
            .join("");

        resultado.innerHTML = `<div class="form-panel">${cards}</div>`;
    }

    async function saldar(sancionId, btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Saldando...`;
        try {
            await pagarSancion(sancionId);
            showToast("success", "Sanción saldada", "La multa fue marcada como pagada.");
            cargarSanciones();
        } catch (error) {
            showToast("error", "No se pudo saldar", error.message);
            btn.disabled = false;
            btn.innerHTML = "Saldar sanción";
        }
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
