document.documentElement.classList.add("has-js");

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".nav-menu");

function closeMenu() {
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Abrir menu");
    navigation.classList.remove("is-open");
}

menuButton.addEventListener("click", () => {
    const isOpen = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "Abrir menu" : "Fechar menu");
    navigation.classList.toggle("is-open", !isOpen);
});

navigation.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
});

document.querySelectorAll(".attend-button").forEach((button) => {
    button.addEventListener("click", () => {
        const isJoining = button.getAttribute("aria-pressed") !== "true";
        const arrow = button.querySelector("span");

        button.setAttribute("aria-pressed", String(isJoining));
        button.classList.toggle("is-confirmed", isJoining);
        button.replaceChildren(document.createTextNode(isJoining ? "Você vai! " : "Participar "), arrow);
    });
});

const revealItems = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    revealItems.forEach((item) => revealObserver.observe(item));
} else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
}