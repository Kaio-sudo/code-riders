
import { supabase } from "./supabase.js";

// =========================================
// ELEMENTOS DA PÁGINA
// =========================================

const profileForm = document.querySelector("#profile-form");
const message = document.querySelector("#profile-message");
const saveButton = document.querySelector("#save-profile");
const logoutButton = document.querySelector("#logout-button");

let currentUser = null;


// =========================================
// MENSAGENS
// =========================================

function showMessage(text, type = "error") {
    message.textContent = text;
    message.className = `profile-message is-visible is-${type}`;
}


// =========================================
// VERIFICAR AUTENTICAÇÃO
// =========================================

async function checkAuthentication() {
    const { data, error } = await supabase.auth.getUser();

    if (error || !data.user) {
        window.location.href = "login.html";
        return false;
    }

    currentUser = data.user;

    document.querySelector("#email").value = currentUser.email || "";

    return true;
}


// =========================================
// CARREGAR PERFIL
// =========================================

async function loadProfile() {
    const { data, error } = await supabase
        .from("profiles")
        .select(`
            full_name,
            username,
            bio,
            city,
            state,
            modalities,
            experience_level,
            is_discoverable
        `)
        .eq("id", currentUser.id)
        .single();

    if (error) {
        console.error("Erro ao carregar perfil:", error);
        showMessage("Não foi possível carregar seu perfil.");
        return;
    }

    document.querySelector("#full-name").value = data.full_name || "";
    document.querySelector("#username").value = data.username || "";
    document.querySelector("#bio").value = data.bio || "";
    document.querySelector("#city").value = data.city || "";
    document.querySelector("#state").value = data.state || "";
    document.querySelector("#experience").value =
        data.experience_level || "";

    document.querySelector("#discoverable").checked =
        data.is_discoverable ?? true;

    // Marcar as modalidades salvas anteriormente.

    const selectedModalities = data.modalities || [];

    document.querySelectorAll('input[name="modality"]').forEach((checkbox) => {
        checkbox.checked = selectedModalities.includes(checkbox.value);
    });
}


// =========================================
// SALVAR PERFIL
// =========================================

profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const fullName = document.querySelector("#full-name").value.trim();

    const usernameInput = document.querySelector("#username").value.trim();

    const username = usernameInput
        ? usernameInput.toLowerCase()
        : null;

    const bio = document.querySelector("#bio").value.trim();
    const city = document.querySelector("#city").value.trim();
    const state = document.querySelector("#state").value.trim();

    const experience = document.querySelector("#experience").value;

    const isDiscoverable =
        document.querySelector("#discoverable").checked;

    const modalities = Array.from(
        document.querySelectorAll('input[name="modality"]:checked')
    ).map((checkbox) => checkbox.value);

    if (!fullName) {
        showMessage("Informe seu nome completo.");
        return;
    }

    if (username && !/^[a-z0-9_]{3,30}$/.test(username)) {
        showMessage(
            "O nome de usuário deve ter de 3 a 30 caracteres, usando apenas letras, números e _."
        );
        return;
    }

    const profileData = {
        full_name: fullName,
        username,
        bio: bio || null,
        city: city || null,
        state: state || null,
        modalities,
        experience_level: experience || null,
        is_discoverable: isDiscoverable
    };

    saveButton.disabled = true;
    saveButton.querySelector("span").textContent = "Salvando...";

    try {
        const { error } = await supabase
            .from("profiles")
            .update(profileData)
            .eq("id", currentUser.id);

        if (error) throw error;

        showMessage(
            "Seu perfil foi atualizado com sucesso!",
            "success"
        );

    } catch (error) {
        console.error("Erro ao salvar perfil:", error);

        if (error.code === "23505") {
            showMessage("Esse nome de usuário já está sendo utilizado.");
        } else {
            showMessage("Não foi possível salvar seu perfil. Tente novamente.");
        }

    } finally {
        saveButton.disabled = false;
        saveButton.querySelector("span").textContent = "Salvar meu perfil";
    }
});


// =========================================
// SAIR DA CONTA
// =========================================

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;

    const { error } = await supabase.auth.signOut();

    if (error) {
        console.error("Erro ao sair:", error);
        showMessage("Não foi possível sair da conta.");
        logoutButton.disabled = false;
        return;
    }

    window.location.href = "login.html";
});


// =========================================
// INICIALIZAÇÃO
// =========================================

async function initializeProfile() {
    const authenticated = await checkAuthentication();

    if (!authenticated) return;

    await loadProfile();
}

initializeProfile();
