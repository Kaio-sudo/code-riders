import { supabase } from "./supabase.js";

// ==========================================
// CODE RIDERS — ENCONTRAR CICLISTAS
// ==========================================

// Elementos HTML
const ridersGrid = document.querySelector("#riders-grid");
const resultsCount = document.querySelector("#results-count");

const cityFilter = document.querySelector("#filter-city");
const modalityFilter = document.querySelector("#filter-modality");
const experienceFilter = document.querySelector("#filter-experience");

// Estado da aplicação
let currentUser = null;
let riders = [];
let sentInterests = new Set();
let receberInteresses = new Set();

// ==========================================
// INICIALIZAÇÃO
// ==========================================

async function initDiscover() {
    // Verifica se existe usuário autenticado
    const { data: { user }, error: authError } =
        await supabase.auth.getUser();

    if (authError || !user) {
        window.location.href = "./login.html";
        return;
    }

    currentUser = user;

    await loadRiders();
    setupFilters();
}

// ==========================================
// BUSCAR CICLISTAS
// ==========================================

async function loadRiders() {
    showMessage("Buscando ciclistas...");

    // Busca perfis que podem ser descobertos
    const { data: profiles, error: profilesError } = await supabase
        .from("profiles")
        .select(`
            id,
            username,
            full_name,
            bio,
            avatar_url,
            city,
            state,
            modalities,
            experience_level,
            is_discoverable
        `)
        .eq("is_discoverable", true)
        .neq("id", currentUser.id)
        .order("full_name");

    if (profilesError) {
        console.error("Erro ao buscar perfis:", profilesError);
        showMessage("Não foi possível carregar os ciclistas. Tente novamente.");
        return;
    }

    // Guarda os perfis encontrados
    riders = profiles || [];

    // Busca interesses enviados pelo usuário atual
    const { data: interests, error: interestsError } = await supabase
        .from("rider_interests")
        .select("receiver_id")
        .eq("sender_id", currentUser.id);

    if (interestsError) {
        console.error("Erro ao buscar interesses:", interestsError);
        showMessage("Não foi possível carregar seus interesses.");
        return;
    }

    // Transforma os interesses em um Set para facilitar a consulta
    sentInterests = new Set(
        (interests || []).map(interest => interest.receiver_id)
    );
    const { data: received, error: receivedError } = await supabase
    .from("rider_interests")
    .select("sender_id")
    .eq("receiver_id", currentUser.id);

if (receivedError) {
    console.error("Erro ao buscar interesses recebidos:", receivedError);
    showMessage("Não foi possível carregar os matches.");
    return;
}

receberInteresses = new Set(
    (received || []).map(interest => interest.sender_id)
);

    renderRiders();
}

// ==========================================
// RENDERIZAR CICLISTAS
// ==========================================

function renderRiders() {
    const filteredRiders = getFilteredRiders();

    resultsCount.textContent = `${filteredRiders.length} ${
        filteredRiders.length === 1 ? "ciclista encontrado" : "ciclistas encontrados"
    }`;

    if (filteredRiders.length === 0) {
        showMessage("Nenhum ciclista encontrado com esses filtros.");
        return;
    }

    ridersGrid.innerHTML = filteredRiders
        .map(rider => createRiderCard(rider))
        .join("");
}
//função de match
function isMatch(riderId) {
    return sentInterests.has(riderId) &&
           receberInteresses.has(riderId);
}
// ==========================================
// CRIAR CARD
// ==========================================

function createRiderCard(rider) {
    const interested = sentInterests.has(rider.id);
    const matched = isMatch(rider.id);
    const name = escapeHTML(rider.full_name || "Ciclista");
    const username = escapeHTML(rider.username || "");
    const bio = escapeHTML(rider.bio || "");
    const city = escapeHTML(rider.city || "");
    const state = escapeHTML(rider.state || "");

    const location = [city, state]
        .filter(Boolean)
        .join(", ");

    const modalities = Array.isArray(rider.modalities)
        ? rider.modalities
        : [];

    const modalityTags = modalities.length
        ? modalities.map(modality => `
            <span class="modality-tag">
                ${escapeHTML(modality)}
            </span>
        `).join("")
        : `<span class="modality-tag">Não informado</span>`;

    const experience = getExperienceLabel(rider.experience_level);

    // Avatar
    const avatar = rider.avatar_url
        ? `
            <img
                src="${escapeHTML(rider.avatar_url)}"
                alt="Foto de ${name}"
                loading="lazy"
            >
        `
        : `
            <span class="rider-avatar-placeholder">
                ${escapeHTML(getInitials(rider.full_name))}
            </span>
        `;

    return `
        <article class="rider-card">

            <div class="rider-card-avatar">
                ${avatar}
            </div>

            <div class="rider-card-content">

                <h3 class="rider-card-name">
                    ${name}
                </h3>

                <p class="rider-card-username">
                    ${username ? `@${username}` : ""}
                </p>

                <p class="rider-card-location">
                    ${location || "Localização não informada"}
                </p>

                ${bio ? `
                    <p class="rider-card-bio">
                        ${bio}
                    </p>
                ` : ""}

                <div class="rider-card-modalities">
                    ${modalityTags}
                </div>

                <p class="rider-card-experience">
                    Experiência: ${experience}
                </p>

                <button
    class="rider-interest-button
        ${interested ? "is-interested" : ""}
        ${matched ? "is-match" : ""}"
    data-rider-id="${rider.id}"
    aria-pressed="${interested}"
>
    ${matched
        ? "🤝 Deu Match!"
        : interested
            ? "✓ Interesse enviado"
            : "Tenho interesse"
    }
</button>

            </div>

        </article>
    `;
}

// ==========================================
// FILTROS
// ==========================================

function getFilteredRiders() {
    const city = cityFilter.value.trim().toLowerCase();
    const modality = modalityFilter.value;
    const experience = experienceFilter.value;

    return riders.filter(rider => {
        const riderCity = (rider.city || "").toLowerCase();
        const riderState = (rider.state || "").toLowerCase();

        const matchesCity = !city ||
            riderCity.includes(city) ||
            riderState.includes(city);

        const matchesModality = !modality ||
            (rider.modalities || []).includes(modality);

        const matchesExperience = !experience ||
            rider.experience_level === experience;

        return matchesCity && matchesModality && matchesExperience;
    });
}

function setupFilters() {
    cityFilter.addEventListener("input", renderRiders);
    modalityFilter.addEventListener("change", renderRiders);
    experienceFilter.addEventListener("change", renderRiders);
}

// ==========================================
// INTERESSE
// ==========================================

ridersGrid.addEventListener("click", async (event) => {
    const button = event.target.closest(".rider-interest-button");

    if (!button) return;

    const riderId = button.dataset.riderId;

    if (!riderId || button.disabled) return;

    await toggleInterest(riderId, button);
});

async function toggleInterest(riderId, button) {
    const alreadyInterested = sentInterests.has(riderId);

    button.disabled = true;

    try {
        if (alreadyInterested) {
            // Remove interesse
            const { error } = await supabase
                .from("rider_interests")
                .delete()
                .eq("sender_id", currentUser.id)
                .eq("receiver_id", riderId);

            if (error) throw error;

            sentInterests.delete(riderId);

        } else {
            // Envia interesse
            const { error } = await supabase
                .from("rider_interests")
                .insert({
                    sender_id: currentUser.id,
                    receiver_id: riderId
                });

            if (error) throw error;

            sentInterests.add(riderId);
        }

        // Atualiza o visual do botão
        updateInterestButton(button, sentInterests.has(riderId));

    } catch (error) {
        console.error("Erro ao atualizar interesse:", error);

        alert("Não foi possível atualizar seu interesse. Tente novamente.");

    } finally {
        button.disabled = false;
    }
}

function updateInterestButton(button, interested) {
    const riderId = button.dataset.riderId;
    const matched = isMatch(riderId);

    button.classList.toggle("is-interested", interested);
    button.classList.toggle("is-match", matched);

    button.setAttribute(
        "aria-pressed",
        String(interested)
    );

    if (matched) {
        button.textContent = "🤝 Deu Match!";
    } else if (interested) {
        button.textContent = "✓ Interesse enviado";
    } else {
        button.textContent = "Tenho interesse";
    }
}

// ==========================================
// UTILITÁRIOS
// ==========================================

// Nome de exibição do nível
function getExperienceLabel(level) {
    const labels = {
        iniciante: "Iniciante",
        intermediario: "Intermediário",
        avancado: "Avançado"
    };

    return labels[level] || "Não informado";
}

// Gera iniciais para avatar
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

// Evita inserção de HTML não confiável nos cards
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

// Mensagens de estado
function showMessage(message) {
    ridersGrid.innerHTML = `
        <div class="discover-message">
            ${escapeHTML(message)}
        </div>
    `;

    resultsCount.textContent = "";
}

// ==========================================
// INICIAR
// ==========================================

initDiscover();