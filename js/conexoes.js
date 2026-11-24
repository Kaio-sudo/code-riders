import { supabase } from "./supabase.js";

// ==========================================
// CODE RIDERS — MEUS MATCHES
// ==========================================

// Elementos HTML
const matchesGrid = document.querySelector("#matches-grid");
const matchesCount = document.querySelector("#matches-count");
const matchesStatus = document.querySelector("#matches-status");

// Estado da aplicação
let currentUser = null;
let matches = [];

// ==========================================
// INICIALIZAÇÃO
// ==========================================

async function initConnections() {

    const { data: { user }, error } =
        await supabase.auth.getUser();

    if (error || !user) {
        window.location.href = "./login.html";
        return;
    }

    currentUser = user;

    await loadMatches();
}

// ==========================================
// BUSCAR MATCHES
// ==========================================

async function loadMatches() {

    matchesStatus.textContent = "Buscando suas conexões...";
    matchesCount.textContent = "—";
    matchesGrid.innerHTML = "";

    try {

        // Busca interesses enviados
        const { data: sent, error: sentError } = await supabase
            .from("rider_interests")
            .select("receiver_id")
            .eq("sender_id", currentUser.id);

        if (sentError) throw sentError;

        // Busca interesses recebidos
        const { data: received, error: receivedError } = await supabase
            .from("rider_interests")
            .select("sender_id")
            .eq("receiver_id", currentUser.id);

        if (receivedError) throw receivedError;

        // Organiza os IDs
        const sentIds = new Set(
            sent.map(interest => interest.receiver_id)
        );

        const receivedIds = new Set(
            received.map(interest => interest.sender_id)
        );

        // Identifica interesses mútuos
        const matchIds = [...sentIds].filter(
            id => receivedIds.has(id)
        );

        // Verifica se existem matches
        if (matchIds.length === 0) {
            matches = [];
            renderMatches();
            return;
        }

        // Busca os perfis dos ciclistas conectados
        const { data: profiles, error: profilesError } = await supabase
            .from("profiles")
            .select(`
                id,
                full_name,
                username,
                avatar_url,
                bio,
                city,
                state,
                modalities,
                experience_level
            `)
            .in("id", matchIds)
            .eq("is_discoverable", true)
            .order("full_name");

        if (profilesError) throw profilesError;

        matches = profiles || [];

        renderMatches();

    } catch (error) {

        console.error("Erro ao carregar matches:", error);

        matchesStatus.textContent =
            "Não foi possível carregar suas conexões. Tente novamente.";

    }
}

// ==========================================
// RENDERIZAR MATCHES
// ==========================================

function renderMatches() {

    matchesCount.textContent = String(matches.length)
        .padStart(2, "0");

    matchesStatus.textContent = "";

    if (matches.length === 0) {

        matchesGrid.innerHTML = `
            <div class="matches-empty">

                <h3>Seu próximo pedal começa aqui.</h3>

                <p>
                    Você ainda não possui conexões disponíveis.
                    Explore a comunidade e encontre novos
                    parceiros de pedal.
                </p>

                <a href="./encontrar.html">
                    Encontrar ciclistas →
                </a>

            </div>
        `;

        return;
    }

    matchesGrid.innerHTML = matches
        .map(rider => createMatchCard(rider))
        .join("");
}

// ==========================================
// CRIAR CARD
// ==========================================

function createMatchCard(rider) {

    const name = escapeHTML(rider.full_name || "Ciclista");
    const username = escapeHTML(rider.username || "");
    const bio = escapeHTML(rider.bio || "");

    const location = [rider.city, rider.state]
        .filter(Boolean)
        .map(escapeHTML)
        .join(", ");

    const modalities = Array.isArray(rider.modalities)
        ? rider.modalities
        : [];

    const modalityTags = modalities.length
        ? modalities.map(modality => `
            <span class="match-modality">
                ${escapeHTML(modality)}
            </span>
        `).join("")
        : `<span class="match-modality">Não informado</span>`;

    const experience = getExperienceLabel(
        rider.experience_level
    );

    const avatarUrl = getSafeAvatarUrl(rider.avatar_url);

    const avatar = avatarUrl
        ? `
            <img
                src="${escapeHTML(avatarUrl)}"
                alt="Foto de ${name}"
                loading="lazy"
                referrerpolicy="no-referrer"
            >
        `
        : `
            <span class="match-avatar-placeholder">
                ${escapeHTML(getInitials(rider.full_name))}
            </span>
        `;

    return `

        <article class="match-card">

            <div class="match-avatar">
                ${avatar}
            </div>

            <span class="match-badge">
                ✓ Match
            </span>

            <div class="match-content">

                <h3 class="match-name">
                    ${name}
                </h3>

                <p class="match-username">
                    ${username ? `@${username}` : ""}
                </p>

                <p class="match-location">
                    ${location || "Localização não informada"}
                </p>

                ${bio ? `
                    <p class="match-bio">
                        ${bio}
                    </p>
                ` : ""}

                <div class="match-modalities">
                    ${modalityTags}
                </div>

                <p class="match-experience">
                    Experiência: ${experience}
                </p>

                <button
                    type="button"
                    class="match-chat-button"
                    data-rider-id="${rider.id}"
                    disabled
                >
                    Chat em breve
                </button>

            </div>

        </article>

    `;
}

// ==========================================
// FUNÇÕES AUXILIARES
// ==========================================

function getExperienceLabel(level) {

    const labels = {
        iniciante: "Iniciante",
        intermediario: "Intermediário",
        avancado: "Avançado"
    };

    return labels[level] || "Não informado";
}

function getInitials(name) {

    if (!name) return "CR";

    return name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map(part => part.charAt(0))
        .join("")
        .toUpperCase();
}

function getSafeAvatarUrl(value) {

    if (!value) return "";

    try {
        const url = new URL(value);

        return url.protocol === "https:"
            ? url.href
            : "";

    } catch {
        return "";
    }
}

function escapeHTML(value) {

    return String(value).replace(/[&<>"']/g, character => {

        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return entities[character];

    });
}

// ==========================================
// INICIAR APLICAÇÃO
// ==========================================

initConnections();