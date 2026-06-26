/**
 * Login — autenticación real contra el backend.
 * Valida credenciales, guarda el token de sesión y redirige al dashboard.
 */

document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-login");
    const emailInput = document.getElementById("login-email");
    const passwordInput = document.getElementById("login-password");

    const btnHtmlOriginal = btn.innerHTML;

    // Permitir Enter en los campos
    [emailInput, passwordInput].forEach((input) => {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") btn.click();
        });
    });

    btn.addEventListener("click", async () => {
        const email = emailInput.value.trim();
        const password = passwordInput.value;

        if (!email || !password) {
            emailInput.style.borderColor = !email ? "var(--danger)" : "";
            passwordInput.style.borderColor = !password ? "var(--danger)" : "";
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Ingresando...`;

        try {
            await loginRequest(email, password);
            window.location.href = "dashboard.html";
        } catch (error) {
            showToast("error", "No se pudo iniciar sesión", error.message);
            btn.disabled = false;
            btn.innerHTML = btnHtmlOriginal;
        }
    });

    // Reset border color al escribir
    emailInput.addEventListener("input", () => (emailInput.style.borderColor = ""));
    passwordInput.addEventListener("input", () => (passwordInput.style.borderColor = ""));
});
