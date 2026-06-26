/**
 * ═══════════════════════════════════════════════════════════════
 *  Panel de Devoluciones — Búsqueda por DNI y devolución por préstamo
 * ═══════════════════════════════════════════════════════════════
 */

document.addEventListener("DOMContentLoaded", () => {
    if (!requireStaff()) return;

    const inputDni = document.getElementById("input-dni");
    const inputFecha = document.getElementById("input-fecha");
    const resultado = document.getElementById("resultado-prestamos");

    let debounceTimer = null;
    let dniActual = "";

    // ── Búsqueda con debounce ──────────────────────────────────
    inputDni.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        const dni = inputDni.value.trim();
        if (!dni) {
            resultado.innerHTML = "";
            return;
        }
        debounceTimer = setTimeout(() => buscarPrestamos(dni), 450);
    });

    // ── Devolver (delegación de eventos) ───────────────────────
    resultado.addEventListener("click", (e) => {
        const btn = e.target.closest(".btn-devolver");
        if (btn) devolver(parseInt(btn.dataset.prestamoId), btn);
    });

    async function buscarPrestamos(dni) {
        dniActual = dni;
        resultado.innerHTML = `<div class="form-panel"><span style="color:var(--text-muted)">Buscando préstamos...</span></div>`;
        try {
            const prestamos = await listarPrestamos({ dni, estado: "activos" });
            renderPrestamos(prestamos);
        } catch (error) {
            resultado.innerHTML = `
                <div class="form-panel">
                    <span style="color:var(--danger)">${escapeHtml(error.message)}</span>
                </div>`;
        }
    }

    function renderPrestamos(prestamos) {
        if (prestamos.length === 0) {
            resultado.innerHTML = `
                <div class="form-panel" style="text-align:center;color:var(--text-muted)">
                    Este usuario no tiene préstamos en curso.
                </div>`;
            return;
        }

        const usuario = prestamos[0].usuario_nombre;
        const cards = prestamos
            .map((p) => {
                const venc = p.vencido
                    ? `<span class="badge badge-danger"><span class="badge-dot"></span>Vencido hace ${p.dias_vencido} día(s)</span>`
                    : `<span class="badge badge-success"><span class="badge-dot"></span>En plazo</span>`;
                return `
                <div class="preview-card ${p.vencido ? "preview-error" : ""}" style="margin-bottom:12px">
                    <div class="preview-row">
                        <div>
                            <div class="preview-label">Préstamo #${p.id} · ${escapeHtml(p.libro_titulo)}</div>
                            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px">
                                Ejemplar #${p.ejemplar_id} · Vence el ${p.fecha_vencimiento}
                            </div>
                        </div>
                        ${venc}
                    </div>
                    <button class="btn btn-primary btn-devolver" data-prestamo-id="${p.id}" style="margin-top:12px">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 11 12 14 22 4"/>
                            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                        </svg>
                        Registrar Devolución
                    </button>
                </div>`;
            })
            .join("");

        resultado.innerHTML = `
            <div class="form-panel">
                <h3 class="form-section-title" style="margin-bottom:16px">
                    Préstamos en curso de ${escapeHtml(usuario)} (${prestamos.length})
                </h3>
                ${cards}
            </div>`;
    }

    async function devolver(prestamoId, btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Procesando...`;
        try {
            const fecha = inputFecha.value || null;
            const resp = await registrarDevolucion(prestamoId, fecha);

            if (resp.sancion) {
                showToast("warning", "Devolución con sanción", resp.mensaje);
                showSancionModal(resp.sancion, resp.mensaje);
            } else {
                showToast("success", "Devolución registrada", resp.mensaje);
            }
            // Refrescar la lista del mismo usuario
            if (dniActual) buscarPrestamos(dniActual);
        } catch (error) {
            showToast("error", "Error al devolver", error.message);
            btn.disabled = false;
            btn.innerHTML = "Registrar Devolución";
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
