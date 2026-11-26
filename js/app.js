
import { supabase } from "./supabase.js";

// =========================================
// CODE RIDERS | CONEXÃO COM SUPABASE
// =========================================

async function verificarConexao() {
    try {
        const { error } = await supabase.auth.getSession();

        if (error) {
            throw error;
        }

        console.log("Supabase conectado e cliente inicializado!");
    } catch (error) {
        console.error("Erro ao inicializar o Supabase:", error.message);
    }
}

verificarConexao();


// =========================================
// MENU DE NAVEGAÇÃO
// =========================================

document.documentElement.classList.add("has-js");

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".nav-menu");

function closeMenu() {
    if (!menuButton || !navigation) return;

    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Abrir menu");
    navigation.classList.remove("is-open");
}

if (menuButton && navigation) {
    menuButton.addEventListener("click", () => {
        const isOpen =
            menuButton.getAttribute("aria-expanded") === "true";

        menuButton.setAttribute("aria-expanded", String(!isOpen));

        menuButton.setAttribute(
            "aria-label",
            isOpen ? "Abrir menu" : "Fechar menu"
        );

        navigation.classList.toggle("is-open", !isOpen);
    });

    navigation.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeMenu();
        }
    });
}


// =========================================
// BOTÕES DE PARTICIPAÇÃO NOS EVENTOS
// =========================================

document.querySelectorAll(".attend-button").forEach((button) => {
    button.addEventListener("click", () => {
        const isJoining =
            button.getAttribute("aria-pressed") !== "true";

        const arrow = button.querySelector("span");

        button.setAttribute("aria-pressed", String(isJoining));

        button.classList.toggle("is-confirmed", isJoining);

        button.replaceChildren(
            document.createTextNode(
                isJoining ? "Você vai! " : "Participar "
            ),
            ...(arrow ? [arrow] : [])
        );
    });
});


// =========================================
// ANIMAÇÕES DE ENTRADA
// =========================================

const revealItems = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
        (entries, observer) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12 }
    );

    revealItems.forEach((item) => {
        revealObserver.observe(item);
    });

} else {
    revealItems.forEach((item) => {
        item.classList.add("is-visible");
    });
}
