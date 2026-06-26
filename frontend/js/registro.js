/**
 * Registro — auto-registro de estudiantes y docentes.
 * Valida los datos, crea la cuenta e inicia sesión automáticamente.
 */

document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-registro");
    const btnHtmlOriginal = btn.innerHTML;

    const campos = {
        nombre: document.getElementById("reg-nombre"),
        apellido: document.getElementById("reg-apellido"),
        dni: document.getElementById("reg-dni"),
        email: document.getElementById("reg-email"),
        password: document.getElementById("reg-password"),
        rol: document.getElementById("reg-rol"),
    };

    // Permitir Enter en los campos
    Object.values(campos).forEach((input) => {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") btn.click();
        });
    });

    btn.addEventListener("click", async () => {
        const nombre = campos.nombre.value.trim();
        const apellido = campos.apellido.value.trim();
        const dni = campos.dni.value.trim();
        const email = campos.email.value.trim();
        const password = campos.password.value;
        const rol = campos.rol.value;

        if (!nombre || !apellido || !dni || !email || !password) {
            showToast("warning", "Campos incompletos", "Completa todos los campos para registrarte.");
            return;
        }
        if (password.length < 8) {
            showToast("warning", "Contraseña muy corta", "La contraseña debe tener al menos 8 caracteres.");
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Creando cuenta...`;

        try {
            await registroRequest({ nombre, apellido, dni, email, password, rol });
            showToast("success", "¡Cuenta creada!", "Te damos la bienvenida. Ingresando al sistema...");
            // Queda con sesión iniciada → entrar al sistema
            setTimeout(() => (window.location.href = "dashboard.html"), 700);
        } catch (error) {
            showToast("error", "No se pudo registrar", error.message);
            btn.disabled = false;
            btn.innerHTML = btnHtmlOriginal;
        }
    });
});
