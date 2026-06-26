/**
 * Sidebar dinámico compartido — Conocimiento Abierto
 * Inyecta el HTML del sidebar en #sidebar-container y marca el link activo.
 * @param {"dashboard"|"catalogo"|"prestamos"|"devoluciones"|"usuarios"} activePage
 */
function renderSidebar(activePage) {
    const container = document.getElementById("sidebar-container");
    if (!container) return;

    const links = [
        {
            id: "dashboard",
            href: "dashboard.html",
            label: "Dashboard",
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/>
                <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>`,
        },
        {
            id: "catalogo",
            href: "index.html",
            label: "Catálogo",
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>`,
        },
        {
            id: "reservas",
            href: "reservas.html",
            label: "Reservas",
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
            </svg>`,
        },
        {
            id: "prestamos",
            href: "prestamos.html",
            label: "Préstamos",
            staffOnly: true,
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
            </svg>`,
        },
        {
            id: "devoluciones",
            href: "devoluciones.html",
            label: "Devoluciones",
            staffOnly: true,
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 11 12 14 22 4"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
            </svg>`,
        },
        {
            id: "sanciones",
            href: "sanciones.html",
            label: "Sanciones",
            staffOnly: true,
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>`,
        },
        {
            id: "usuarios",
            href: "usuarios.html",
            label: "Usuarios",
            staffOnly: true,
            svg: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>`,
        },
    ];

    // El rol se lee de localStorage porque este script corre antes que api.js.
    let usuarioActual = null;
    try {
        usuarioActual = JSON.parse(localStorage.getItem("usuario"));
    } catch {
        usuarioActual = null;
    }
    const esStaffLocal =
        !!usuarioActual &&
        (usuarioActual.rol === "BIBLIOTECARIO" || usuarioActual.rol === "ADMINISTRADOR");

    // Los enlaces de personal solo se muestran a bibliotecarios/administradores.
    const navLinks = links
        .filter((link) => !link.staffOnly || esStaffLocal)
        .map(
            (link) => `
        <a href="${link.href}" class="nav-link${activePage === link.id ? " active" : ""}">
            ${link.svg}
            ${link.label}
        </a>`
        )
        .join("\n");

    const usuario = usuarioActual;

    const escapeHtml = (t) => {
        const d = document.createElement("div");
        d.textContent = t == null ? "" : t;
        return d.innerHTML;
    };

    const footer = usuario
        ? `<div class="sidebar-footer">
                <div class="sidebar-user">
                    <div class="sidebar-user-avatar">${escapeHtml((usuario.nombre || "?").charAt(0).toUpperCase())}</div>
                    <div class="sidebar-user-info">
                        <span class="sidebar-user-name">${escapeHtml(usuario.nombre)} ${escapeHtml(usuario.apellido)}</span>
                        <span class="sidebar-user-role">${escapeHtml(usuario.rol)}</span>
                    </div>
                </div>
                <button class="sidebar-logout" onclick="cerrarSesion()" title="Cerrar sesión" aria-label="Cerrar sesión">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                        <polyline points="16 17 21 12 16 7"/>
                        <line x1="21" y1="12" x2="9" y2="12"/>
                    </svg>
                </button>
           </div>`
        : `<div class="sidebar-footer">
                <a href="login.html" class="nav-link">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                        <polyline points="10 17 15 12 10 7"/>
                        <line x1="15" y1="12" x2="3" y2="12"/>
                    </svg>
                    Iniciar sesión
                </a>
           </div>`;

    container.innerHTML = `
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-brand">
                <div class="sidebar-brand-icon">📚</div>
                <h1>Conocimiento<br>Abierto<span>Biblioteca Universitaria</span></h1>
            </div>
            <nav class="sidebar-nav">
                ${navLinks}
            </nav>
            ${footer}
        </aside>
        <button class="mobile-menu-btn" id="mobile-menu-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
    `;
}
