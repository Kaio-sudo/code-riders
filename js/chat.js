import { supabase } from "./supabase.js";

// ==========================================
// CODE RIDERS — CHAT PRIVADO
// ==========================================

// Elementos HTML
const chatAvatar = document.querySelector("#chat-avatar");
const chatUserName = document.querySelector("#chat-user-name");
const chatUserStatus = document.querySelector("#chat-user-status");
const chatStatus = document.querySelector("#chat-status");
const chatMessages = document.querySelector("#chat-messages");

const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");
const messageCounter = document.querySelector("#message-counter");
const sendButton = document.querySelector("#send-button");

// Estado da aplicação
let currentUser = null;
let otherRider = null;
let riderId = null;
let messages = [];
let canSend = false;
let isSending = false;

// ==========================================
// INICIALIZAÇÃO
// ==========================================

async function initChat() {

    setStatus("Carregando conversa...");

    try {

        // Verifica autenticação
        const { data: { user }, error } =
            await supabase.auth.getUser();

        if (error || !user) {
            window.location.href = "./login.html";
            return;
        }

        currentUser = user;

        // Captura o ID do ciclista pela URL
        const params = new URLSearchParams(
            window.location.search
        );

        riderId = params.get("rider");

        const validId =
            /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

        if (
            !riderId ||
            !validId.test(riderId) ||
            riderId.toLowerCase() === currentUser.id.toLowerCase()
        ) {
            throw new Error("Conversa inválida.");
        }

        // Verifica se existe match
        const matched = await checkMatch();

        if (!matched) {
            throw new Error(
                "Você precisa ter um match para iniciar esta conversa."
            );
        }

        // Carrega perfil e mensagens
        await loadRider();
        await loadMessages();

        // Libera o formulário
        canSend = true;
        messageInput.disabled = false;

        updateCounter();
        setStatus("");

    } catch (error) {

        console.error("Erro ao iniciar chat:", error);

        setStatus(
            error.message || "Não foi possível abrir a conversa.",
            true
        );

        chatUserName.textContent = "Conversa indisponível";
        chatUserStatus.textContent = "";

        canSend = false;
        messageInput.disabled = true;
        sendButton.disabled = true;
    }
}

// ==========================================
// VERIFICAR MATCH
// ==========================================

async function checkMatch() {

    const { data: sent, error: sentError } =
        await supabase
            .from("rider_interests")
            .select("id")
            .eq("sender_id", currentUser.id)
            .eq("receiver_id", riderId)
            .maybeSingle();

    if (sentError) throw sentError;

    const { data: received, error: receivedError } =
        await supabase
            .from("rider_interests")
            .select("id")
            .eq("sender_id", riderId)
            .eq("receiver_id", currentUser.id)
            .maybeSingle();

    if (receivedError) throw receivedError;

    return Boolean(sent && received);
}

// ==========================================
// CARREGAR PERFIL DO CICLISTA
// ==========================================

async function loadRider() {

    const { data, error } = await supabase
        .from("profiles")
        .select(`
            id,
            full_name,
            username,
            avatar_url
        `)
        .eq("id", riderId)
        .single();

    if (error) throw error;

    otherRider = data;

    chatUserName.textContent =
        otherRider.full_name || "Ciclista";

    chatUserStatus.textContent =
        "🤝 Conexão Code Riders";

    renderAvatar();
}

function renderAvatar() {

    chatAvatar.replaceChildren();

    const avatarUrl = getSafeAvatarUrl(
        otherRider.avatar_url
    );

    if (avatarUrl) {

        const image = document.createElement("img");

        image.src = avatarUrl;
        image.alt = `Foto de ${otherRider.full_name}`;
        image.referrerPolicy = "no-referrer";

        image.addEventListener("error", () => {
            chatAvatar.textContent =
                getInitials(otherRider.full_name);
        });

        chatAvatar.appendChild(image);

    } else {

        chatAvatar.textContent =
            getInitials(otherRider.full_name);
    }
}

// ==========================================
// CARREGAR MENSAGENS
// ==========================================

async function loadMessages() {

    const { data, error } = await supabase
        .from("messages")
        .select(`
            id,
            sender_id,
            receiver_id,
            content,
            created_at
        `)
        .or(
            `and(sender_id.eq.${currentUser.id},receiver_id.eq.${riderId}),` +
            `and(sender_id.eq.${riderId},receiver_id.eq.${currentUser.id})`
        )
        .order("created_at", { ascending: false })
        .order("id", { ascending: false })
        .limit(100);

    if (error) throw error;

    messages = (data || []).reverse();

    renderMessages();
}

// ==========================================
// EXIBIR MENSAGENS
// ==========================================

function renderMessages() {

    chatMessages.replaceChildren();

    if (messages.length === 0) {

        renderWelcome();

        return;
    }

    let lastDate = null;

    messages.forEach(message => {

        const date = new Date(
            message.created_at
        ).toLocaleDateString("pt-BR");

        // Separador de datas
        if (date !== lastDate) {

            const separator = document.createElement("div");

            separator.className = "chat-date";

            separator.textContent = formatDate(
                message.created_at
            );

            chatMessages.appendChild(separator);

            lastDate = date;
        }

        chatMessages.appendChild(
            createMessageElement(message)
        );
    });

    scrollToBottom();
}

// ==========================================
// CRIAR BOLHA DE MENSAGEM
// ==========================================

function createMessageElement(message) {

    const isMine =
        message.sender_id === currentUser.id;

    const bubble = document.createElement("article");

    bubble.className = isMine
        ? "message sent"
        : "message received";

    const content = document.createElement("p");

    content.className = "message-content";
    content.textContent = message.content;

    const time = document.createElement("time");

    time.className = "message-time";
    time.dateTime = message.created_at;

    time.textContent = new Date(
        message.created_at
    ).toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit"
    });

    bubble.append(content, time);

    return bubble;
}

// ==========================================
// MENSAGEM DE BOAS-VINDAS
// ==========================================

function renderWelcome() {

    chatMessages.innerHTML = `
        <div class="chat-welcome">

            <span class="chat-welcome-icon">
                🤝
            </span>

            <h3>Vocês deram Match!</h3>

            <p>
                Toda grande aventura começa
                com uma conversa.
                Que tal combinar o próximo pedal?
            </p>

        </div>
    `;
}

// ==========================================
// ENVIAR MENSAGEM
// ==========================================

chatForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    if (!canSend || isSending) return;

    const content = messageInput.value.trim();

    if (!content || content.length > 2000) return;

    isSending = true;

    sendButton.disabled = true;
    messageInput.disabled = true;
    sendButton.textContent = "Enviando...";

    setStatus("");

    try {

        // Confirma se o match ainda existe
        const matched = await checkMatch();

        if (!matched) {

            canSend = false;

            chatUserStatus.textContent =
                "Conexão encerrada";

            throw new Error(
                "Este match não está mais ativo."
            );
        }

        // Salva a mensagem no Supabase
        const { data, error } = await supabase
            .from("messages")
            .insert({
                sender_id: currentUser.id,
                receiver_id: riderId,
                content: content
            })
            .select(`
                id,
                sender_id,
                receiver_id,
                content,
                created_at
            `)
            .single();

        if (error) throw error;

        // Adiciona a mensagem ao histórico local
        messages.push(data);

        messageInput.value = "";

        renderMessages();

    } catch (error) {

        console.error("Erro ao enviar mensagem:", error);

        setStatus(
            "Não foi possível enviar: " + error.message,
            true
        );

    } finally {

        isSending = false;

        sendButton.textContent = "Enviar →";

        messageInput.disabled = !canSend;

        updateCounter();

        if (canSend) {
            messageInput.focus();
        }
    }
});

// ==========================================
// CONTADOR DE CARACTERES
// ==========================================

messageInput.addEventListener("input", updateCounter);

function updateCounter() {

    const length = messageInput.value.length;

    messageCounter.textContent =
        `${length}/2000`;

    sendButton.disabled =
        !canSend ||
        isSending ||
        messageInput.value.trim().length === 0 ||
        length > 2000;
}

// ==========================================
// ENTER PARA ENVIAR
// ==========================================

messageInput.addEventListener("keydown", (event) => {

    if (
        event.key === "Enter" &&
        !event.shiftKey &&
        !event.isComposing
    ) {

        event.preventDefault();

        if (!sendButton.disabled) {
            chatForm.requestSubmit();
        }
    }
});

// ==========================================
// FUNÇÕES AUXILIARES
// ==========================================

function setStatus(message, isError = false) {

    chatStatus.textContent = message;

    chatStatus.classList.toggle(
        "is-error",
        isError
    );
}

function scrollToBottom() {

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
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

function formatDate(value) {

    const date = new Date(value);
    const today = new Date();

    const yesterday = new Date();

    yesterday.setDate(
        yesterday.getDate() - 1
    );

    if (date.toDateString() === today.toDateString()) {
        return "Hoje";
    }

    if (date.toDateString() === yesterday.toDateString()) {
        return "Ontem";
    }

    return date.toLocaleDateString("pt-BR");
}

// ==========================================
// INICIAR APLICAÇÃO
// ==========================================

initChat();