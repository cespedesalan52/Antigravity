/**
 * Dashboard — Panel de Control
 * Carga las métricas globales desde el backend y las renderiza.
 */

document.addEventListener("DOMContentLoaded", async () => {
    if (!requireAuth()) return;

    // Las acciones rápidas de personal se ocultan para estudiantes/docentes.
    if (!esStaff()) {
        ["prestamos.html", "devoluciones.html", "usuarios.html"].forEach((href) => {
            const card = document.querySelector(`.quick-action-card[href="${href}"]`);
            if (card) card.style.display = "none";
        });
    }

    try {
        const s = await obtenerStats();

        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        set("stat-libros", s.total_libros);
        set("stat-disponibles", s.ejemplares_disponibles);
        set("stat-prestados", s.prestamos_activos);
        set("stat-vencidos", s.prestamos_vencidos);
        set("stat-sanciones", s.sanciones_vigentes);
        set("stat-reservas", s.reservas_pendientes);

        // Barras de porcentaje del catálogo
        const total = s.total_ejemplares;
        if (total > 0) {
            const pctDisp = Math.round((s.ejemplares_disponibles / total) * 100);
            const pctPrest = Math.round((s.ejemplares_prestados / total) * 100);
            document.getElementById("bar-disponibles-pct").textContent = `${pctDisp}%`;
            document.getElementById("bar-prestados-pct").textContent = `${pctPrest}%`;
            setTimeout(() => {
                document.getElementById("bar-disponibles").style.width = `${pctDisp}%`;
                document.getElementById("bar-prestados").style.width = `${pctPrest}%`;
            }, 100);
        }
    } catch (error) {
        showToast("error", "Error de conexión", error.message);
        ["stat-libros", "stat-disponibles", "stat-prestados", "stat-vencidos", "stat-sanciones", "stat-reservas"].forEach(
            (id) => {
                const el = document.getElementById(id);
                if (el) el.textContent = "—";
            }
        );
    }
});
