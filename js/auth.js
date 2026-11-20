
import { supabase } from "./supabase.js";

// =========================================
// ELEMENTOS DA PÁGINA
// =========================================

const signupForm = document.querySelector("#signup-form");
const loginForm = document.querySelector("#login-form");

const message = document.querySelector("#auth-message");


// =========================================
// MOSTRAR MENSAGENS
// =========================================

function showMessage(text, type = "error") {
    if (!message) return;

    message.textContent = text;
    message.className = `auth-message is-visible is-${type}`;
}


// =========================================
// TRADUZIR ERROS MAIS COMUNS
// =========================================

function getErrorMessage(error) {
    const messages = {
        "User already registered":
            "Este e-mail já está cadastrado.",

        "Invalid login credentials":
            "E-mail ou senha incorretos.",

        "Password should be at least 6 characters":
            "A senha precisa ter pelo menos 6 caracteres.",

        "Email not confirmed":
            "Confirme seu e-mail antes de entrar."
    };

    return messages[error.message] ||
        "Não foi possível concluir a operação. Tente novamente.";
}


// =========================================
// CADASTRO
// =========================================

if (signupForm) {
    signupForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = signupForm.querySelector("button");
        const fullName = signupForm.querySelector("#full-name").value.trim();
        const email = signupForm.querySelector("#email").value.trim();
        const password = signupForm.querySelector("#password").value;
        const confirmPassword =
            signupForm.querySelector("#confirm-password").value;

        if (password !== confirmPassword) {
            showMessage("As senhas não são iguais.");
            return;
        }

        button.disabled = true;
        button.querySelector("span").textContent = "Criando conta...";

        try {
            const { data, error } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    data: {
                        full_name: fullName
                    }
                }
            });

            if (error) throw error;

            if (data.session) {
                showMessage(
                    "Conta criada com sucesso! Redirecionando...",
                    "success"
                );

                window.location.href = "../index.html";
            } else {
                showMessage(
                    "Cadastro realizado! Confira seu e-mail para confirmar sua conta antes de entrar.",
                    "success"
                );

                signupForm.reset();
            }

        } catch (error) {
            console.error("Erro no cadastro:", error);
            showMessage(getErrorMessage(error));

        } finally {
            button.disabled = false;
            button.querySelector("span").textContent = "Criar minha conta";
        }
    });
}


// =========================================
// LOGIN
// =========================================

if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = loginForm.querySelector("button");
        const email = loginForm.querySelector("#email").value.trim();
        const password = loginForm.querySelector("#password").value;

        button.disabled = true;
        button.querySelector("span").textContent = "Entrando...";

        try {
            const { error } = await supabase.auth.signInWithPassword({
                email,
                password
            });

            if (error) throw error;

            showMessage(
                "Login realizado! Redirecionando...",
                "success"
            );

            window.location.href = "../index.html";

        } catch (error) {
            console.error("Erro no login:", error);
            showMessage(getErrorMessage(error));

        } finally {
            button.disabled = false;
            button.querySelector("span").textContent = "Entrar na minha conta";
        }
    });
}
