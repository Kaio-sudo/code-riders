import { supabase } from "./supabase.js";

// ==========================================
// CODE RIDERS — COMUNIDADE
// ==========================================

// ELEMENTOS HTML
const realtimeStatus = document.querySelector(
    "#realtime-status"
);

const realtimeLabel = document.querySelector(
    "#realtime-label"
);
// ELEMENTOS DE UPLOAD

const addImageButton = document.querySelector(
    "#add-image-button"
);

const imageInput = document.querySelector(
    "#post-image-input"
);

const imagePreview = document.querySelector(
    "#image-preview"
);

const imagePreviewContainer = document.querySelector(
    "#image-preview-container"
);

const removeImageButton = document.querySelector(
    "#remove-image-button"
);

const postForm = document.querySelector("#post-form");
const postContent = document.querySelector("#post-content");
const postCounter = document.querySelector("#post-counter");
const publishButton = document.querySelector("#publish-button");

const composerAvatar = document.querySelector("#composer-avatar");
const composerUserName = document.querySelector("#composer-user-name");
const composerStatus = document.querySelector("#composer-status");

const postsFeed = document.querySelector("#posts-feed");
const feedStatus = document.querySelector("#feed-status");

const sidebarAvatar = document.querySelector("#sidebar-avatar");
const sidebarUserName = document.querySelector("#sidebar-user-name");
const sidebarUserLocation = document.querySelector("#sidebar-user-location");

const myPostsCount = document.querySelector("#my-posts-count");
const myLikesCount = document.querySelector("#my-likes-count");
const myMatchesCount = document.querySelector("#my-matches-count");

// ESTADO DA APLICAÇÃO
let communityChannel = null;

let refreshTimer = null;

let isRefreshing = false;

let refreshPending = false;

let fallbackTimer = null;
let selectedImage = null;

let previewUrl = null;

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;

const ALLOWED_IMAGE_TYPES = {

    "image/jpeg": "jpg",

    "image/png": "png",

    "image/webp": "webp"

};

let currentUser = null;
let currentProfile = null;
let posts = [];
let likedPostIds = new Set();

const pendingLikes = new Set();

let isPublishing = false;
let isReady = false;

// ==========================================
// SELECIONAR IMAGEM
// ==========================================

addImageButton.addEventListener("click", () => {

    if (!isReady || isPublishing) return;

    imageInput.click();

});

imageInput.addEventListener("change", () => {

    if (!isReady || isPublishing) return;

    const file = imageInput.files[0];

    if (!file) return;

    if (!Object.hasOwn(ALLOWED_IMAGE_TYPES, file.type)) {

        setStatus(
            composerStatus,
            "Selecione uma imagem JPG, PNG ou WebP.",
            true
        );

        imageInput.value = "";

        return;

    }

    if (file.size > MAX_IMAGE_SIZE) {

        setStatus(
            composerStatus,
            "A imagem deve ter no máximo 5 MB.",
            true
        );

        imageInput.value = "";

        return;

    }

    if (previewUrl) {

        URL.revokeObjectURL(previewUrl);

    }

    selectedImage = file;

    previewUrl = URL.createObjectURL(file);

    imagePreview.src = previewUrl;

    imagePreviewContainer.hidden = false;

    setStatus(composerStatus, "");

});

removeImageButton.addEventListener("click", () => {

    if (isPublishing) return;

    clearSelectedImage();

});

function clearSelectedImage() {

    if (previewUrl) {

        URL.revokeObjectURL(previewUrl);

    }

    selectedImage = null;

    previewUrl = null;

    imageInput.value = "";

    imagePreview.removeAttribute("src");

    imagePreviewContainer.hidden = true;

}

// ==========================================
// INICIALIZAR COMUNIDADE
// ==========================================

async function initCommunity() {

    try {

        setStatus(feedStatus, "Carregando comunidade...");

        const { data: { user }, error } =
            await supabase.auth.getUser();

        if (error || !user) {

            window.location.href = "./login.html";
            return;

        }

        currentUser = user;

        await loadCurrentProfile();
        await loadPosts();

        isReady = true;

        postContent.disabled = false;

        addImageButton.disabled = false;

        updatePostCounter();

        await refreshStats();
        subscribeToCommunity();

    } catch (error) {

        console.error(
            "Erro ao iniciar comunidade:",
            error
        );

        setStatus(
            feedStatus,
            "Não foi possível carregar a comunidade.",
            true
        );

    }
    
}

// ==========================================
// CARREGAR PERFIL DO USUÁRIO
// ==========================================

async function loadCurrentProfile() {

    const { data, error } = await supabase
        .from("profiles")
        .select(`
            id,
            full_name,
            username,
            avatar_url,
            city,
            state
        `)
        .eq("id", currentUser.id)
        .single();

    if (error) throw error;

    currentProfile = data;

    composerUserName.textContent =
        currentProfile.full_name;

    sidebarUserName.textContent =
        currentProfile.full_name;

    const location = [
        currentProfile.city,
        currentProfile.state
    ].filter(Boolean).join(", ");

    sidebarUserLocation.textContent =
        location || "Code Riders Community";

    renderAvatar(composerAvatar, currentProfile);
    renderAvatar(sidebarAvatar, currentProfile);

}

// ==========================================
// CARREGAR CURTIDAS DO USUÁRIO
// ==========================================

async function loadMyLikes(postIds) {

    if (postIds.length === 0) {

        likedPostIds = new Set();

        return;

    }

    const { data, error } = await supabase
        .from("post_likes")
        .select("post_id")
        .eq("user_id", currentUser.id)
        .in("post_id", postIds);

    if (error) throw error;

    likedPostIds = new Set(

        (data || []).map(
            like => like.post_id
        )

    );

}

// ==========================================
// CARREGAR PUBLICAÇÕES
// ==========================================

async function loadPosts() {

    setStatus(
        feedStatus,
        "Carregando publicações..."
    );

    try {

        const { data, error } = await supabase
            .from("posts")
            .select(`
                id,
                author_id,
                content,
                image_path,
                created_at,
                updated_at,

                author:profiles!posts_author_id_fkey (
                    id,
                    full_name,
                    username,
                    avatar_url,
                    city,
                    state
                ),

                post_likes(count),

                post_comments(count)
                
            `)
            .order("created_at", {
                ascending: false
            })
            .order("id", {
                ascending: false
            })
            .limit(50);

        if (error) throw error;

       const nextPosts = data || [];

if (isRefreshing && hasActiveInteraction()) {

    refreshPending = true;

    setStatus(feedStatus, "");

    return;

}

const previousLikes = likedPostIds;

await loadMyLikes(
    nextPosts.map(post => post.id)
);

if (isRefreshing && hasActiveInteraction()) {

    likedPostIds = previousLikes;

    refreshPending = true;

    setStatus(feedStatus, "");

    return;

}

posts = nextPosts;

renderPosts();

        setStatus(feedStatus, "");

    } catch (error) {

        setStatus(
            feedStatus,
            "Não foi possível atualizar o feed.",
            true
        );

        throw error;

    }
}

// ==========================================
// EXIBIR PUBLICAÇÕES
// ==========================================

function renderPosts() {
    if (!posts.length) {
        renderEmptyFeed();
        return;
    }
    const existing = new Map([...postsFeed.querySelectorAll('.post-card')]
        .map(card => [card.dataset.postId, card]));
    postsFeed.querySelector('.feed-empty')?.remove();
    const ids = new Set(posts.map(post => post.id));
    for (const [id, card] of existing) {
        if (!ids.has(id)) card.remove();
    }
    let cursor = postsFeed.firstElementChild;
    for (const post of posts) {
        let card = existing.get(post.id);
        if (!card) card = createPostCard(post);
        else {
            updateLikeButton(card.querySelector('[data-action="like"]'), post);
            const count = post.post_comments?.[0]?.count ?? 0;
            card.querySelector('[data-action="comments"]').textContent =
                `💬 ${count} ${count === 1 ? "comentário" : "comentários"}`;
            card.querySelector('.post-content').textContent = post.content;
        }
        if (card !== cursor) postsFeed.insertBefore(card, cursor);
        cursor = card.nextElementSibling;
    }
}

// ==========================================
// CRIAR CARD DE PUBLICAÇÃO
// ==========================================

function createPostCard(post) {

    const author = post.author || {
        full_name: "Ciclista da comunidade",
        avatar_url: null
    };

    const isOwnPost =
        post.author_id === currentUser.id;

    const likesCount =
        post.post_likes?.[0]?.count ?? 0;

    const commentsCount =
        post.post_comments?.[0]?.count ?? 0;

    // CARD

    const card = document.createElement("article");

    card.className = "post-card";
    card.dataset.postId = post.id;

    // CABEÇALHO

    const header = document.createElement("header");

    header.className = "post-header";

    const avatar = document.createElement("div");

    avatar.className = "community-avatar";

    renderAvatar(avatar, author);

    const authorInfo = document.createElement("div");

    authorInfo.className = "post-author-info";

    const authorName = document.createElement("h3");

    authorName.className = "post-author-name";

    authorName.textContent =
        author.full_name || "Ciclista";

    const meta = document.createElement("p");

    meta.className = "post-meta";

    const location = [
        author.city,
        author.state
    ].filter(Boolean).join(", ");

    meta.textContent = [
        location,
        formatDate(post.created_at)
    ].filter(Boolean).join(" · ");

    authorInfo.append(authorName, meta);

    header.append(avatar, authorInfo);

    // BOTÃO EXCLUIR

    if (isOwnPost) {

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";

        deleteButton.className =
            "post-delete-button";

        deleteButton.dataset.action = "delete";

        deleteButton.textContent = "Excluir";

        deleteButton.setAttribute(
            "aria-label",
            "Excluir publicação"
        );

        header.appendChild(deleteButton);

    }

    // CONTEÚDO

    const content = document.createElement("p");

    content.className = "post-content";

    content.textContent = post.content;

    // INTERAÇÕES

    const actions = document.createElement("div");

    actions.className = "post-actions";

    // CURTIDAS

const likeButton = document.createElement("button");

likeButton.type = "button";

likeButton.className = "post-action-button";

likeButton.dataset.action = "like";

updateLikeButton(likeButton, post);

// COMENTÁRIOS

const commentButton = document.createElement("button");

commentButton.type = "button";
commentButton.className = "post-action-button";
commentButton.dataset.action = "comments";

commentButton.textContent =
    `💬 ${commentsCount} comentários`;
commentButton.disabled = false;

commentButton.setAttribute("aria-expanded", "false");

commentButton.setAttribute(
    "aria-controls",
    `comments-${post.id}`
);

actions.append(likeButton, commentButton);

// ÁREA DE COMENTÁRIOS

const commentsSection = document.createElement("section");

commentsSection.className = "post-comments";
commentsSection.id = `comments-${post.id}`;
commentsSection.hidden = true;

commentsSection.innerHTML = `
    <div class="comments-list"></div>

    <form class="comment-form">

        <textarea
            class="comment-input"
            aria-label="Escreva um comentário"
            placeholder="Escreva um comentário..."
            maxlength="1000"
            rows="2"
            required
        ></textarea>

        <button
            type="submit"
            class="comment-submit"
        >
            Enviar
        </button>

    </form>

    <p class="community-status comment-status"
       role="status"></p>
`;

card.append(header, content);

// IMAGEM DA PUBLICAÇÃO

if (post.image_path) {

    const { data } = supabase.storage
        .from("post-images")
        .getPublicUrl(post.image_path);

    const image = document.createElement("img");

    image.className = "post-image";

    image.src = data.publicUrl;

    image.alt = "Foto compartilhada pelo ciclista";

    image.loading = "lazy";

    image.addEventListener("error", () => {

        image.remove();

    });

    card.appendChild(image);

}

card.append(actions, commentsSection);

return card;

}

// ==========================================
// ATUALIZAR BOTÃO DE CURTIDA
// ==========================================

function updateLikeButton(button, post) {

    const isLiked = likedPostIds.has(
        post.id
    );

    const likesCount =
        post.post_likes?.[0]?.count ?? 0;

    const label = likesCount === 1
        ? "curtida"
        : "curtidas";

    button.textContent =

        `${isLiked ? "♥" : "♡"} ${likesCount} ${label}`;

    button.classList.toggle(
        "is-liked",
        isLiked
    );

    button.setAttribute(
        "aria-pressed",
        String(isLiked)
    );

    button.title = isLiked
        ? "Remover curtida"
        : "Curtir publicação";

    button.disabled =
        pendingLikes.has(post.id);

}

// ==========================================
// FEED VAZIO
// ==========================================

function renderEmptyFeed() {

    postsFeed.innerHTML = `
        <div class="feed-empty">

            <h3>Todo caminho tem um começo.</h3>

            <p>
                Ainda não existem publicações.
                Compartilhe sua primeira aventura
                com a comunidade Code Riders!
            </p>

        </div>
    `;

}

// ==========================================
// PUBLICAR TEXTO E IMAGEM
// ==========================================

postForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    if (!isReady || isPublishing) return;

    const content = postContent.value.trim();

    if (!content || content.length > 3000) return;

    isPublishing = true;

    publishButton.disabled = true;
    postContent.disabled = true;
    addImageButton.disabled = true;
    removeImageButton.disabled = true;

    publishButton.textContent = "Publicando...";

    setStatus(composerStatus, "");

    let imagePath = null;

    let publicationSaved = false;

    let insertAttempted = false;

    try {

        // ENVIAR IMAGEM

        if (selectedImage) {

            publishButton.textContent = "Enviando foto...";

            imagePath = await uploadPostImage(
                selectedImage
            );

        }

        publishButton.textContent = "Publicando...";

        // SALVAR PUBLICAÇÃO

        insertAttempted = true;

        const { error } = await supabase
            .from("posts")
            .insert({

                author_id: currentUser.id,

                content: content,

                image_path: imagePath

            });

        if (error) {

            // Erro explícito do banco: publicação rejeitada

            if (/^(22|23|42)[0-9A-Z]{3}$/.test(error.code || "")) {

                insertAttempted = false;

            }

            throw error;

        }

        publicationSaved = true;

        postContent.value = "";

        clearSelectedImage();

        setStatus(
            composerStatus,
            "Publicação realizada com sucesso!"
        );

        await loadPosts();

        await refreshStats();

    } catch (error) {

        console.error(error);

        // REMOVER IMAGEM SE A PUBLICAÇÃO
        // DEFINITIVAMENTE NÃO FOI SALVA

        if (imagePath && !publicationSaved && !insertAttempted) {

            try {

                await removeStoredImage(imagePath);

            } catch (storageError) {

                console.error(
                    "Erro ao limpar imagem:",
                    storageError
                );

            }

        }

        setStatus(

            composerStatus,

            publicationSaved
                ? "Publicação salva. Atualize a página."
                : "Não foi possível confirmar a publicação. Confira o feed antes de tentar novamente.",

            true

        );

    } finally {

        isPublishing = false;

        postContent.disabled = !isReady;
        addImageButton.disabled = !isReady;
        removeImageButton.disabled = false;

        publishButton.textContent = "Publicar →";

        updatePostCounter();

    }

});
// ==========================================
// CONTADOR DE CARACTERES
// ==========================================

postContent.addEventListener(
    "input",
    updatePostCounter
);

function updatePostCounter() {

    const length = postContent.value.length;

    postCounter.textContent =
        `${length}/3000`;

    publishButton.disabled =

        !isReady ||

        isPublishing ||

        postContent.value.trim().length === 0 ||

        length > 3000;

}

// ==========================================
// EVENTOS DAS PUBLICAÇÕES
// ==========================================

postsFeed.addEventListener("click", async (event) => {

    const button = event.target.closest(
        "button[data-action]"
    );

    if (!button || button.disabled) return;

    const card = button.closest(".post-card");

    if (!card) return;

    const postId = card.dataset.postId;

    const action = button.dataset.action;

    // CURTIDAS

    if (action === "like") {

        await toggleLike(postId, button);

        return;

    }

    // ABRIR COMENTÁRIOS

    if (action === "comments") {

        await toggleComments(
            postId,
            card,
            button
        );

        return;

    }

    // EXCLUIR COMENTÁRIO

    if (action === "delete-comment") {

        button.disabled = true;

        try {

            await deleteComment(
                postId,
                button.dataset.commentId,
                card
            );

        } finally {

            button.disabled = false;

        }

        return;

    }

    // EXCLUIR PUBLICAÇÃO

    if (action === "delete") {

        button.disabled = true;

        try {

            await deletePost(postId);

        } finally {

            button.disabled = false;

        }

    }

});

// ==========================================
// CARREGAR COMENTÁRIOS
// ==========================================

async function loadComments(postId, card) {

    const list = card.querySelector(".comments-list");

    list.textContent = "Carregando comentários...";

    const { data, error } = await supabase
        .from("post_comments")
        .select(`
            id,
            post_id,
            author_id,
            content,
            created_at,

            author:profiles!post_comments_author_id_fkey (
                full_name,
                avatar_url
            )
        `)
        .eq("post_id", postId)
        .order("created_at", {
            ascending: true
        })
        .order("id", {
            ascending: true
        })
        .limit(100);

    if (error) {

        console.error(error);

        list.textContent =
            `Não foi possível carregar os comentários: ${error.message || "erro desconhecido"}.`;

        return;

    }

    list.replaceChildren();

    if (!data.length) {

        list.textContent =
            "Seja a primeira pessoa a comentar!";

        return;

    }

    data.forEach(comment => {

        list.appendChild(
            createCommentElement(comment)
        );

    });

}
// ==========================================
// CRIAR COMENTÁRIO
// ==========================================

function createCommentElement(comment) {

    const author = comment.author || {
        full_name: "Ciclista da comunidade",
        avatar_url: null
    };

    const item = document.createElement("div");

    item.className = "comment-item";
    item.dataset.commentId = comment.id;

    const avatar = document.createElement("div");

    avatar.className = "community-avatar";

    renderAvatar(avatar, author);

    const body = document.createElement("div");

    body.className = "comment-body";

    const header = document.createElement("div");

    header.className = "comment-header";

    const name = document.createElement("span");

    name.className = "comment-author";
    name.textContent = author.full_name;

    header.appendChild(name);

    // EXCLUIR O PRÓPRIO COMENTÁRIO

    if (comment.author_id === currentUser.id) {

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";

        deleteButton.className =
            "comment-delete-button";

        deleteButton.dataset.action =
            "delete-comment";

        deleteButton.dataset.commentId =
            comment.id;

        deleteButton.textContent = "Excluir";

        header.appendChild(deleteButton);

    }

    const content = document.createElement("p");

    content.className = "comment-content";

    content.textContent = comment.content;

    const time = document.createElement("span");

    time.className = "comment-time";

    time.textContent = formatDate(
        comment.created_at
    );

    body.append(header, content, time);

    item.append(avatar, body);

    return item;

}
// ==========================================
// ABRIR E FECHAR COMENTÁRIOS
// ==========================================

async function toggleComments(postId, card, button) {

    const section = card.querySelector(
        ".post-comments"
    );

    const isOpening = section.hidden;

    section.hidden = !isOpening;

    button.setAttribute(
        "aria-expanded",
        String(isOpening)
    );

    if (isOpening) {

        await loadComments(postId, card);

    }

}

// ==========================================
// CURTIR OU DESCURTIR PUBLICAÇÃO
// ==========================================

async function toggleLike(postId, button) {

    if (!isReady) return;

    if (pendingLikes.has(postId)) return;

    const post = posts.find(
        item => item.id === postId
    );

    if (!post) return;

    pendingLikes.add(postId);

    updateLikeButton(button, post);

    setStatus(feedStatus, "");

    let saved = false;

    try {

        const isLiked =
            likedPostIds.has(postId);

        if (isLiked) {

            // REMOVER CURTIDA

            const { error } = await supabase
                .from("post_likes")
                .delete()
                .eq("post_id", postId)
                .eq("user_id", currentUser.id);

            if (error) throw error;

            likedPostIds.delete(postId);

        } else {

            // ADICIONAR CURTIDA

            const { error } = await supabase
                .from("post_likes")
                .insert({

                    post_id: postId,

                    user_id: currentUser.id

                });

            // Ignora duplicidade caso a curtida
            // já exista em outra sessão

            if (error && error.code !== "23505") {
                throw error;
            }

            likedPostIds.add(postId);

        }

        saved = true;

        // CONSULTAR TOTAL ATUALIZADO

        const { count, error: countError } =
            await supabase
                .from("post_likes")
                .select("id", {

                    count: "exact",

                    head: true

                })
                .eq("post_id", postId);

        if (countError) throw countError;

        // Atualiza o objeto atual do feed

        const currentPost = posts.find(
            item => item.id === postId
        );

        if (currentPost) {

            currentPost.post_likes = [
                { count: count ?? 0 }
            ];

        }

        // Atualizar estatísticas pessoais

        await refreshStats();

    } catch (error) {

        console.error(
            "Erro ao atualizar curtida:",
            error
        );

        setStatus(

            feedStatus,

            saved
                ? "Curtida salva. Atualize a página para sincronizar o contador."
                : "Não foi possível atualizar a curtida.",

            true

        );

    } finally {

        pendingLikes.delete(postId);

        const currentPost = posts.find(
            item => item.id === postId
        );

        const currentButton = postsFeed.querySelector(
            `.post-card[data-post-id="${postId}"] button[data-action="like"]`
        );

        if (currentPost && currentButton) {

            updateLikeButton(
                currentButton,
                currentPost
            );

        }

    }

}

// ==========================================
// EXCLUIR PUBLICAÇÃO
// ==========================================

async function deletePost(postId) {

    const post = posts.find(
        item => item.id === postId
    );

    if (!post) return;

    if (post.author_id !== currentUser.id) return;

    const confirmed = window.confirm(
        "Deseja realmente excluir esta publicação?"
    );

    if (!confirmed) return;

    try {

        const { data, error } = await supabase
            .from("posts")
            .delete()
            .eq("id", postId)
            .eq("author_id", currentUser.id)
            .select("id")
            .maybeSingle();

        if (error) throw error;

        if (!data) {

            throw new Error(
                "Publicação não encontrada ou sem permissão."
            );

        }

    // EXCLUIR IMAGEM DO STORAGE

if (post.image_path) {

    try {

        await removeStoredImage(
            post.image_path
        );

    } catch (storageError) {

        console.error(
            "Publicação excluída, mas a imagem não foi removida:",
            storageError
        );

        setStatus(
            composerStatus,
            "A publicação foi excluída, mas a foto precisa ser removida do Storage.",
            true
        );

    }

}

        posts = posts.filter(
            item => item.id !== postId
        );

        renderPosts();

        setStatus(
            feedStatus,
            "Publicação excluída com sucesso."
        );

        await refreshStats();

    } catch (error) {

        console.error(
            "Erro ao excluir publicação:",
            error
        );

        setStatus(
            feedStatus,
            "Não foi possível excluir a publicação.",
            true
        );

    }

}

// ==========================================
// ESTATÍSTICAS PESSOAIS
// ==========================================

async function loadStats() {

    const [
        postsResult,
        likesResult,
        sentResult,
        receivedResult
    ] = await Promise.all([

        // TOTAL DE PUBLICAÇÕES

        supabase
            .from("posts")
            .select("id", {
                count: "exact",
                head: true
            })
            .eq("author_id", currentUser.id),

        // TOTAL DE CURTIDAS RECEBIDAS

        supabase
            .from("post_likes")
            .select("id, posts!inner(author_id)", {
                count: "exact",
                head: true
            })
            .eq(
                "posts.author_id",
                currentUser.id
            ),

        // INTERESSES ENVIADOS

        supabase
            .from("rider_interests")
            .select("receiver_id")
            .eq("sender_id", currentUser.id),

        // INTERESSES RECEBIDOS

        supabase
            .from("rider_interests")
            .select("sender_id")
            .eq("receiver_id", currentUser.id)

    ]);

    for (const result of [
        postsResult,
        likesResult,
        sentResult,
        receivedResult
    ]) {

        if (result.error) throw result.error;

    }

    // CALCULAR MATCHES

    const sentIds = new Set(

        (sentResult.data || []).map(
            item => item.receiver_id
        )

    );

    const receivedIds = new Set(

        (receivedResult.data || []).map(
            item => item.sender_id
        )

    );

    const matchIds = [...sentIds].filter(

        id => receivedIds.has(id)

    );

    // ATUALIZAR INTERFACE

    myPostsCount.textContent =

        String(postsResult.count ?? 0)
            .padStart(2, "0");

    myLikesCount.textContent =

        String(likesResult.count ?? 0)
            .padStart(2, "0");

    myMatchesCount.textContent =

        String(matchIds.length)
            .padStart(2, "0");

}

async function refreshStats() {

    try {

        await loadStats();

    } catch (error) {

        console.error(
            "Erro ao carregar estatísticas:",
            error
        );

        myPostsCount.textContent = "—";
        myLikesCount.textContent = "—";
        myMatchesCount.textContent = "—";

    }

}

// ==========================================
// AVATARES
// ==========================================

function renderAvatar(element, profile) {

    element.replaceChildren();

    const initials = getInitials(
        profile.full_name
    );

    const avatarUrl = getSafeAvatarUrl(
        profile.avatar_url
    );

    if (!avatarUrl) {

        element.textContent = initials;

        return;

    }

    const image = document.createElement("img");

    image.src = avatarUrl;

    image.alt =
        `Foto de ${profile.full_name || "ciclista"}`;

    image.loading = "lazy";

    image.referrerPolicy = "no-referrer";

    image.addEventListener("error", () => {

        element.textContent = initials;

    });

    element.appendChild(image);

}

// ==========================================
// FUNÇÕES AUXILIARES
// ==========================================

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

    const now = new Date();

    const difference = Math.max(
        0,
        now.getTime() - date.getTime()
    );

    const minutes = Math.floor(
        difference / 60000
    );

    const hours = Math.floor(
        minutes / 60
    );

    const days = Math.floor(
        hours / 24
    );

    if (minutes < 1) {

        return "Agora";

    }

    if (minutes < 60) {

        return `Há ${minutes} min`;

    }

    if (hours < 24) {

        return `Há ${hours} h`;

    }

    if (days < 7) {

        return `Há ${days} d`;

    }

    return date.toLocaleDateString(
        "pt-BR"
    );

}

function setStatus(
    element,
    message,
    isError = false
) {

    element.textContent = message;

    element.classList.toggle(
        "is-error",
        isError
    );

}
// ==========================================
// ENVIAR COMENTÁRIO
// ==========================================

postsFeed.addEventListener("submit", async (event) => {

    const form = event.target.closest(".comment-form");

    if (!form) return;

    event.preventDefault();

    if (!isReady) return;

    const card = form.closest(".post-card");

    const postId = card.dataset.postId;

    const input = form.querySelector(".comment-input");

    const button = form.querySelector(".comment-submit");

    const status = card.querySelector(".comment-status");

    const content = input.value.trim();

    if (!content || content.length > 1000) return;

    if (button.disabled) return;

    button.disabled = true;
    input.disabled = true;

    button.textContent = "Enviando...";

    setStatus(status, "");

    try {

        const { error } = await supabase
            .from("post_comments")
            .insert({

                post_id: postId,

                author_id: currentUser.id,

                content: content

            });

        if (error) throw error;

        input.value = "";

        await loadComments(postId, card);

        await refreshCommentCount(postId, card);

    } catch (error) {

        console.error(error);

        setStatus(
            status,
            `Não foi possível enviar ou atualizar o comentário: ${error.message || "erro desconhecido"}. Confira a lista antes de tentar novamente.`,
            true
        );

    } finally {

        button.disabled = false;
        input.disabled = false;

        button.textContent = "Enviar";

    }

});
// ==========================================
// ATUALIZAR CONTADOR DE COMENTÁRIOS
// ==========================================

async function refreshCommentCount(postId, card) {

    const { count, error } = await supabase
        .from("post_comments")
        .select("id", {

            count: "exact",

            head: true

        })
        .eq("post_id", postId);

    if (error) throw error;

    const total = count ?? 0;

    const post = posts.find(
        item => item.id === postId
    );

    if (post) {

        post.post_comments = [
            { count: total }
        ];

    }

    const button = card.querySelector(
        '[data-action="comments"]'
    );

    const label = total === 1
        ? "comentário"
        : "comentários";

    button.textContent = `💬 ${total} ${label}`;

}
// ==========================================
// CONECTAR SUPABASE REALTIME
// ==========================================

function subscribeToCommunity() {

    if (communityChannel) return;

    updateRealtimeStatus("connecting");

    communityChannel = supabase

        .channel("code-riders-community")

        // PUBLICAÇÕES

        .on(

            "postgres_changes",

            {

                event: "*",

                schema: "public",

                table: "posts"

            },

            () => {

                scheduleFeedRefresh();

            }

        )

        // CURTIDAS

        .on(

            "postgres_changes",

            {

                event: "*",

                schema: "public",

                table: "post_likes"

            },

            () => {

                scheduleFeedRefresh();

            }

        )

        // COMENTÁRIOS

        .on(

            "postgres_changes",

            {

                event: "*",

                schema: "public",

                table: "post_comments"

            },

            () => {

                scheduleFeedRefresh();

            }

        )

        .subscribe(status => {

            if (status === "SUBSCRIBED") {

                console.log(
                    "Comunidade Realtime conectada!"
                );

                updateRealtimeStatus("online");

                scheduleFeedRefresh();

            }

            if (

                status === "CHANNEL_ERROR" ||

                status === "TIMED_OUT" ||

                status === "CLOSED"

            ) {

                updateRealtimeStatus("offline");

            }

        });

    // SINCRONIZAÇÃO DE SEGURANÇA

    clearInterval(fallbackTimer);

    fallbackTimer = setInterval(() => {

        if (!document.hidden) {

            scheduleFeedRefresh();

        }

    }, 30000);

}

// ==========================================
// STATUS DA CONEXÃO
// ==========================================

function updateRealtimeStatus(status) {
    if (!realtimeStatus || !realtimeLabel) return;

    realtimeStatus.classList.remove(
        "is-online",
        "is-offline"
    );

    if (status === "online") {

        realtimeStatus.classList.add(
            "is-online"
        );

        realtimeLabel.textContent = "Ao vivo";

        return;

    }

    if (status === "offline") {

        realtimeStatus.classList.add(
            "is-offline"
        );

        realtimeLabel.textContent =
            "Reconectando...";

        return;

    }

    realtimeLabel.textContent =
        "Conectando...";

}
// ==========================================
// UPLOAD PARA SUPABASE STORAGE
// ==========================================

async function uploadPostImage(file) {

    if (!file) return null;

    const extension =
        ALLOWED_IMAGE_TYPES[file.type];

    const fileName =
        `${crypto.randomUUID()}.${extension}`;

    const filePath =
        `${currentUser.id}/${fileName}`;

    const { data, error } = await supabase.storage
        .from("post-images")
        .upload(filePath, file, {

            contentType: file.type,

            cacheControl: "3600",

            upsert: false

        });

    if (error) throw error;

    return data.path;

}
async function removeStoredImage(path) {

    if (!path) return;

    const { error } = await supabase.storage
        .from("post-images")
        .remove([path]);

    if (error) throw error;

}

// ==========================================
// EXCLUIR COMENTÁRIO
// ==========================================

async function deleteComment(postId, commentId, card) {

    const confirmed = window.confirm(
        "Deseja excluir este comentário?"
    );

    if (!confirmed) return;

    const status = card.querySelector(".comment-status");

    try {

        const { data, error } = await supabase
            .from("post_comments")
            .delete()
            .eq("id", commentId)
            .eq("post_id", postId)
            .eq("author_id", currentUser.id)
            .select("id")
            .maybeSingle();

        if (error) throw error;

        if (!data) {

            throw new Error(
                "Comentário não encontrado ou sem permissão."
            );

        }

        await loadComments(postId, card);

        await refreshCommentCount(postId, card);

    } catch (error) {

        console.error(error);

        setStatus(
            status,
            "Não foi possível excluir ou atualizar o comentário.",
            true
        );

    }

}
// ==========================================
// VERIFICAR INTERAÇÕES EM ANDAMENTO
// ==========================================

function hasActiveInteraction() {

    if (isPublishing) return true;

    if (pendingLikes.size > 0) return true;

    const activeElement = document.activeElement;

    if (activeElement?.matches(".comment-input")) {

        return true;

    }

    const inputs = postsFeed.querySelectorAll(
        ".comment-input"
    );

    for (const input of inputs) {

        if (input.value.trim()) {

            return true;

        }

    }

    const pendingAction = postsFeed.querySelector(
        ".comment-submit:disabled, " +
        ".comment-delete-button:disabled, " +
        ".post-delete-button:disabled"
    );

    return Boolean(pendingAction);

}

// ==========================================
// AGENDAR ATUALIZAÇÃO DO FEED
// ==========================================

function scheduleFeedRefresh() {

    refreshPending = true;

    clearTimeout(refreshTimer);

    refreshTimer = setTimeout(
        refreshCommunityFeed,
        700
    );

}

// ==========================================
// ATUALIZAR COMUNIDADE
// ==========================================

async function refreshCommunityFeed() {

    if (!isReady || !refreshPending) return;

    if (isRefreshing || hasActiveInteraction()) {

        refreshTimer = setTimeout(
            refreshCommunityFeed,
            1500
        );

        return;

    }

    isRefreshing = true;

    refreshPending = false;

    // GUARDAR COMENTÁRIOS ABERTOS

    const openedPostIds = [

        ...postsFeed.querySelectorAll(
            ".post-comments:not([hidden])"
        )

    ].map(section => {

        return section.closest(
            ".post-card"
        ).dataset.postId;

    });

    try {

        await loadPosts();
        if (hasActiveInteraction()) {

    refreshPending = true;

    return;

}

        // REABRIR COMENTÁRIOS

        for (const postId of openedPostIds) {

            const card = postsFeed.querySelector(
                `.post-card[data-post-id="${postId}"]`
            );

            if (!card) continue;

            const button = card.querySelector(
                '[data-action="comments"]'
            );

            if (!card.querySelector(".post-comments").hidden) {
                await loadComments(postId, card);
            }

        }

        await refreshStats();

    } catch (error) {

        console.error(
            "Erro ao sincronizar comunidade:",
            error
        );

        refreshPending = true;

    } finally {

        isRefreshing = false;

        if (refreshPending) {

            clearTimeout(refreshTimer);

            refreshTimer = setTimeout(
                refreshCommunityFeed,
                1500
            );

        }

    }

}

// ==========================================
// INICIAR APLICAÇÃO
// ==========================================
// ==========================================
// ENCERRAR CONEXÃO AO SAIR DA PÁGINA
// ==========================================

window.addEventListener("pagehide", () => {

    clearTimeout(refreshTimer);

    clearInterval(fallbackTimer);

    refreshPending = false;

    if (communityChannel) {

        const channel = communityChannel;

        communityChannel = null;

        supabase.removeChannel(channel);

    }

});

// RESTAURAR CONEXÃO AO VOLTAR

window.addEventListener("pageshow", (event) => {

    if (event.persisted && isReady) {

        subscribeToCommunity();

    }

});

// SINCRONIZAR AO VOLTAR PARA A ABA

document.addEventListener("visibilitychange", () => {

    if (!document.hidden && isReady) {

        scheduleFeedRefresh();

    }

});
initCommunity(); 