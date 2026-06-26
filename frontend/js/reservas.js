/**
 * ═══════════════════════════════════════════════════════════════
 *  Panel de Reservas — vista por rol
 *  - Personal: todas las reservas, con filtros, y puede cancelar cualquiera.
 *  - Estudiante/Docente: solo sus reservas, puede cancelar las propias.
 * ═══════════════════════════════════════════════════════════════
 */

document.addEventListener("DOMContentLoaded", () => {
    if (!requireAuth()) return;

    const staff = esStaff();
    const resultado = document.getElementById("resultado-reservas");
    const panelFiltros = document.getElementById("panel-filtros");
    const subtitulo = document.getElementById("reservas-subtitulo");
    const inputDni = document.getElementById("input-dni");
    const selectEstado = document.getElementById("select-estado");

    let debounceTimer = null;

    if (staff) {
        panelFiltros.style.display = "";
        subtitulo.textContent = "Gestioná las reservas de libros de todos los usuarios";
        inputDni.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(cargar, 450);
        });
        selectEstado.addEventListener("change", cargar);
    } else {
        subtitulo.textContent = "Tus reservas de libros";
    }

    cargar();

    // Cancelar (delegación de eventos)
    resultado.addEventListener("click", (e) => {
        const btn = e.target.closest(".btn-cancelar-reserva");
        if (btn) cancelar(parseInt(btn.dataset.reservaId), btn);
    });

    async function cargar() {
        resultado.innerHTML = `<div class="form-panel"><span style="color:var(--text-muted)">Cargando reservas...</span></div>`;
        try {
            const reservas = staff
                ? await listarReservas({ dni: inputDni.value.trim() || null, estado: selectEstado.value || null })
                : await listarMisReservas();
            render(reservas);
        } catch (error) {
            resultado.innerHTML = `<div class="form-panel"><span style="color:var(--danger)">${esc(error.message)}</span></div>`;
        }
    }

    function render(reservas) {
        if (reservas.length === 0) {
            resultado.innerHTML = `<div class="form-panel" style="text-align:center;color:var(--text-muted)">No hay reservas para mostrar.</div>`;
            return;
        }

        const badges = {
            PENDIENTE: "badge-warning",
            COMPLETADA: "badge-success",
            CANCELADA: "badge-danger",
            EXPIRADA: "badge-danger",
        };

        const cards = reservas
            .map((r) => {
                const fecha = new Date(r.fecha_reserva).toLocaleDateString();
                const puedeCancelar = r.estado === "PENDIENTE";
                const quien = staff ? `${esc(r.usuario_nombre)} · DNI ${esc(r.usuario_dni)} — ` : "";
                return `
                <div class="preview-card" style="margin-bottom:12px">
                    <div class="preview-row">
                        <div>
                            <div class="preview-label">${esc(r.libro_titulo)}</div>
                            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px">${quien}reservado el ${fecha}</div>
                        </div>
                        <span class="badge ${badges[r.estado] || "badge-info"}"><span class="badge-dot"></span>${esc(r.estado)}</span>
                    </div>
                    ${puedeCancelar ? `
                    <button class="btn btn-secondary btn-cancelar-reserva" data-reserva-id="${r.id}" style="margin-top:12px">
                        Cancelar reserva
                    </button>` : ""}
                </div>`;
            })
            .join("");

        resultado.innerHTML = `<div class="form-panel">${cards}</div>`;
    }

    async function cancelar(reservaId, btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Cancelando...`;
        try {
            await cancelarReserva(reservaId);
            showToast("success", "Reserva cancelada", "La reserva fue cancelada.");
            cargar();
        } catch (error) {
            showToast("error", "No se pudo cancelar", error.message);
            btn.disabled = false;
            btn.innerHTML = "Cancelar reserva";
        }
    }

    function esc(text) {
        if (text === null || text === undefined) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
