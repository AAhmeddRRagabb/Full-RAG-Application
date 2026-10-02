import { CHAT_ROUTES_PATH, DATA_ROUTES_PATH, ERROR_MESSAGE } from "./constants.js";
import { csrfHeaders, getActiveShellUser, getErrorMessage, parseJsonResponse, showAlert } from "./utils.js";


const headerTitle = document.querySelector(".header-title");
const messagesArea = document.getElementById("messages");
const queryForm = document.getElementById("queryForm");
const queryInput = document.getElementById("queryArea");
const sendBtn = document.querySelector(".query-form_submit-btn");
const cancelBtn = document.querySelector(".query-cancel-btn");
const runStatus = document.querySelector(".run-status");
const chatsList = document.querySelector(".chats-list");
const addChatBtn = document.querySelector(".add-new-chat-btn");
const filesBox = document.querySelector(".chat-settings-modal .file-list");
const summaryText = document.querySelector(".chat-settings-modal .resources-status");

let chats = [];
let activeChat = null;
let currentUser = null;
let activeRun = null;
const defaultTitle = document.title || "Ahmed Bot";




/* ------------------------------------------ API --------------------------------------- */
function headers(method = "GET") {
    return {
        "Content-Type": "application/json",
        ...(method === "GET" ? {} : csrfHeaders()),
    };
}


async function api(path, method = "GET", body = null) {
    let response;

    try {
        response = await fetch(`${CHAT_ROUTES_PATH}${path}`, {
            method,
            credentials: "include",
            headers: headers(method),
            ...(body ? { body: JSON.stringify(body) } : {}),
        });
    } catch {
        showAlert("Could not reach the chat service.", ERROR_MESSAGE);
        return null;
    }

    const data = await parseJsonResponse(response);
    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return null;
    }

    return data;
}


const getChats = () => api("/chats");
const getChat = (chatId) => api(`/chats/${encodeURIComponent(chatId)}`);
const createChatApi = (name) => api(`/chats?chat_name=${encodeURIComponent(name)}`, "POST");
const renameChatApi = (chatId, name) => api(`/chats/${encodeURIComponent(chatId)}?chat_name=${encodeURIComponent(name)}`, "PATCH");
const deleteChatApi = (chatId) => api(`/chats/${encodeURIComponent(chatId)}`, "DELETE");


async function streamChat(body, signal) {
    try {
        return await fetch(`${CHAT_ROUTES_PATH}/chat/stream`, {
            method: "POST",
            credentials: "include",
            headers: headers("POST"),
            body: JSON.stringify(body),
            signal,
        });
    } catch (error) {
        if (error.name === "AbortError") throw error;
        showAlert("Could not reach the chat service.", ERROR_MESSAGE);
        return null;
    }
}




/* ------------------------------------------ Current Controls --------------------------------------- */
function selectedFiles() {
    return Array.from(filesBox.querySelectorAll("input[type='checkbox']"))
        .filter((input) => input.checked && !input.disabled)
        .map((input) => input.value);
}


function selectedTone() {
    return document.querySelector("input[name='chatTone']:checked")?.value || "technical";
}


function selectedDepth() {
    return document.querySelector("input[name='answerDepth']:checked")?.value || "moderate";
}


function currentRequestOptions() {
    return {
        files: selectedFiles(),
        tone: selectedTone(),
        depth: selectedDepth(),
    };
}


function updateControlSummary() {
    if (!summaryText) return;

    const options = currentRequestOptions();
    const fileText = options.files.length ? `${options.files.length} file${options.files.length === 1 ? "" : "s"}` : "No files";
    summaryText.textContent = `${fileText} | ${options.tone} | ${options.depth} depth`;
}




/* ------------------------------------------ URLs --------------------------------------- */
function slugify(value) {
    return String(value || "chat")
        .trim()
        .toLowerCase()
        .replace(/[^\p{L}\p{N}]+/gu, "-")
        .replace(/^-+|-+$/g, "") || "chat";
}


function userSlug() {
    return `${currentUser?.user_uuid_prefix || "usr"}_${slugify(currentUser?.user_name || "user")}`;
}


function chatUrl(chat) {
    return `/${encodeURIComponent(userSlug())}/${encodeURIComponent(slugify(chat?.title || "chat"))}`;
}


function currentChatSlug() {
    const [, , chatSlug = null] = window.location.pathname.split("/");
    return chatSlug ? decodeURIComponent(chatSlug) : null;
}


function pushChatUrl(chat, replace = false) {
    if (!currentUser || !chat?.serverId) return;

    const nextUrl = chatUrl(chat);
    if (window.location.pathname !== nextUrl) {
        window.history[replace ? "replaceState" : "pushState"]({}, "", nextUrl);
    }
}




/* ------------------------------------------ Resource Rendering --------------------------------------- */
function normalizeResources(resources) {
    if (!resources) return [];
    if (Array.isArray(resources)) return resources.filter(Boolean);
    if (typeof resources === "object") return Object.values(resources).flat().filter(Boolean);
    return [resources].filter(Boolean);
}


function websiteName(url) {
    try {
        return new URL(url).hostname.replace(/^www\./, "");
    } catch {
        return "web source";
    }
}


function documentResource(resource) {
    const text = String(resource).trim();
    const direct = text.match(/^(\d+)_(.+)$/);
    if (direct) return { id: direct[1], name: direct[2] };

    const input = Array.from(filesBox.querySelectorAll("input[type='checkbox']")).find((fileInput) => {
        const [, fileName = ""] = fileInput.value.match(/^[^_]+_(.*)$/) || [];
        return fileInput.name === text || fileName === text || fileInput.value === text;
    });

    return input
        ? { id: input.value.split("_")[0], name: input.name || text }
        : { id: null, name: text };
}


function scrollToMessage(messageId) {
    const target = messagesArea.querySelector(`[data-message-id="${CSS.escape(String(messageId))}"]`);
    if (!target) {
        showAlert("Referenced message is not visible in this chat.", ERROR_MESSAGE);
        return;
    }

    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("message-highlight");
    setTimeout(() => target.classList.remove("message-highlight"), 1600);
}


function resourceButton(resource) {
    const text = String(resource).trim();
    const icon = document.createElement("i");
    let node;

    if (/^https?:\/\//i.test(text)) {
        const name = websiteName(text);
        node = document.createElement("a");
        node.href = text;
        node.target = "_blank";
        node.rel = "noopener noreferrer";
        node.title = name;
        node.setAttribute("aria-label", `Open ${name}`);
        icon.className = "fa-solid fa-arrow-up-right-from-square";
    } else if (text.startsWith("message:")) {
        const messageId = text.replace("message:", "").trim();
        node = document.createElement("button");
        node.type = "button";
        node.title = "Go to referenced message";
        node.setAttribute("aria-label", "Go to referenced message");
        node.addEventListener("click", () => scrollToMessage(messageId));
        icon.className = "fa-solid fa-message";
    } else {
        const doc = documentResource(text);
        node = doc.id ? document.createElement("a") : document.createElement("span");
        node.title = doc.name;
        node.setAttribute("aria-label", `Open document source: ${doc.name}`);
        icon.className = doc.name.toLowerCase().endsWith(".pdf") ? "fa-solid fa-file-pdf" : "fa-solid fa-file-lines";

        if (doc.id) {
            node.href = `${DATA_ROUTES_PATH}/files/${encodeURIComponent(doc.id)}`;
            node.target = "_blank";
            node.rel = "noopener noreferrer";
        }
    }

    node.className = "message-llm-resource";
    node.dataset.resource = text;
    node.append(icon);
    return node;
}




/* ------------------------------------------ Rendering --------------------------------------- */
function chatFromApi(chat) {
    return {
        id: String(chat.chat_id),
        serverId: chat.chat_id,
        title: chat.chat_name,
        messages: Array.from(chat.messages || []),
    };
}


function renderMessages() {
    messagesArea.innerHTML = "";

    if (!activeChat) {
        headerTitle.textContent = "New Chat";
        document.title = defaultTitle;
        return;
    }

    headerTitle.textContent = activeChat.title;
    document.title = activeChat.title || defaultTitle;

    const messages = activeChat.messages.length
        ? activeChat.messages
        : [{ role: "assistant", content: "Ask a question to begin." }];

    messages.forEach((message) => messagesArea.append(messageNode(message)));
    messagesArea.scrollTop = messagesArea.scrollHeight;
}


function messageNode(message) {
    const article = document.createElement("article");
    const avatar = document.createElement("div");
    const bodyWrap = document.createElement("div");
    const body = document.createElement("div");
    const isUser = message.role === "user";

    article.className = `message ${isUser ? "user-message" : "assistant-message"}`;
    avatar.className = "avatar";
    bodyWrap.className = "message-body";
    body.className = "message-content";
    avatar.textContent = isUser ? "You" : "AI";
    body.innerHTML = DOMPurify.sanitize(marked.parse(message.content || ""));

    if (message.message_id) article.dataset.messageId = String(message.message_id);

    bodyWrap.append(body);

    if (!isUser) {
        const resources = normalizeResources(message.llm_resources).slice(0, 3);
        if (resources.length) {
            const list = document.createElement("div");
            list.className = "message-llm-resources";
            resources.forEach((resource) => list.append(resourceButton(resource)));
            bodyWrap.append(list);
        }
    }

    article.append(...(isUser ? [bodyWrap, avatar] : [avatar, bodyWrap]));
    return article;
}


function renderChats() {
    chatsList.innerHTML = "";

    chats.forEach((chat) => {
        const item = document.createElement("article");
        const select = document.createElement("button");
        const actions = document.createElement("div");
        const rename = document.createElement("button");
        const remove = document.createElement("button");

        item.className = `chat-item ${chat.id === activeChat?.id ? "active" : ""}`;
        select.className = "chat-select";
        actions.className = "chat-actions";
        rename.className = "chat-edit-name";
        remove.className = "chat-delete";

        select.type = "button";
        select.textContent = chat.title;
        select.addEventListener("click", () => selectChat(chat.id));

        rename.type = "button";
        rename.setAttribute("aria-label", "Rename this chat");
        rename.innerHTML = '<i class="fa-solid fa-pen"></i>';
        rename.addEventListener("click", () => renameChat(chat, select));

        remove.type = "button";
        remove.setAttribute("aria-label", "Delete this chat");
        remove.innerHTML = '<i class="fa-solid fa-trash"></i>';
        remove.addEventListener("click", () => deleteChat(chat));

        actions.append(rename, remove);
        item.append(select, actions);
        chatsList.append(item);
    });
}




/* ------------------------------------------ Chat Actions --------------------------------------- */
async function loadChats(user) {
    currentUser = user;
    const data = await getChats();
    chats = Array.from(data?.chats || []).map(chatFromApi);

    if (!chats.length) {
        await createChat("chat #1");
        return;
    }

    const slug = currentChatSlug();
    const requested = slug ? chats.find((chat) => slugify(chat.title) === slug) : null;
    await selectChat((requested || chats[0]).id);
}


async function selectChat(chatId, updateUrl = true) {
    activeChat = chats.find((chat) => chat.id === chatId) || null;
    renderChats();
    renderMessages();

    if (!activeChat) return;

    const data = await getChat(activeChat.serverId);
    if (!data) return;

    activeChat.title = data.chat.chat_name;
    activeChat.messages = Array.from(data.messages || []);
    renderChats();
    renderMessages();
    if (updateUrl) pushChatUrl(activeChat);
}


async function createChat(name = `chat #${chats.length + 1}`) {
    if (!currentUser) return;

    const data = await createChatApi(name);
    if (!data?.chat) return;

    const chat = chatFromApi(data.chat);
    chats.push(chat);
    await selectChat(chat.id);
}


function renameChat(chat, button) {
    const oldTitle = chat.title;
    const input = document.createElement("input");
    let finished = false;

    input.className = "chat-rename-input";
    input.value = chat.title;
    button.replaceWith(input);
    input.focus();
    input.select();

    const finish = async (save) => {
        if (finished) return;
        finished = true;

        chat.title = save ? input.value.trim() || oldTitle : oldTitle;

        if (save) {
            const data = await renameChatApi(chat.serverId, chat.title);
            if (data?.chat) chat.title = data.chat.chat_name;
        }

        renderChats();
        renderMessages();
        if (activeChat?.id === chat.id) pushChatUrl(chat, true);
    };

    input.addEventListener("input", () => {
        chat.title = input.value.trim() || "Untitled chat";
        if (activeChat?.id === chat.id) {
            headerTitle.textContent = chat.title;
            document.title = chat.title;
            pushChatUrl(chat, true);
        }
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") finish(true);
        if (event.key === "Escape") finish(false);
    });
    input.addEventListener("blur", () => finish(true), { once: true });
}


async function deleteChat(chat) {
    const data = await deleteChatApi(chat.serverId);
    if (!data) return;

    chats = chats.filter((item) => item.id !== chat.id);

    if (!chats.length) {
        await createChat("chat #1");
        return;
    }

    await selectChat(activeChat?.id === chat.id ? chats[0].id : activeChat.id);
}


function clearChats() {
    currentUser = null;
    chats = [];
    activeChat = null;
    renderChats();
    renderMessages();
}




/* ------------------------------------------ Streaming --------------------------------------- */
function setRunState(text = "", running = false) {
    runStatus.textContent = text;
    runStatus.classList.toggle("active", Boolean(text));
    cancelBtn.hidden = !running;
    sendBtn.disabled = running;
}


function applyStreamEvent(event, assistantMessage, chat) {
    if (event.type === "stage") {
        setRunState(event.message || "thinking", true);
        return;
    }

    if (event.type === "token") {
        if (assistantMessage.content === "...") assistantMessage.content = "";
        assistantMessage.content += event.value || "";
        if (activeChat?.id === chat.id) renderMessages();
        return;
    }

    if (event.type === "done") {
        assistantMessage.content = event.report || "No answer was returned.";
        assistantMessage.llm_resources = event.llm_resources || [];
        return;
    }

    if (event.type === "error") {
        assistantMessage.content = "The response could not be completed.";
        showAlert(event.detail || "The chat request failed.", ERROR_MESSAGE);
    }
}


async function readStream(response, assistantMessage, chat) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
            if (line.trim()) applyStreamEvent(JSON.parse(line), assistantMessage, chat);
        }

        if (done) break;
    }

    if (buffer.trim()) applyStreamEvent(JSON.parse(buffer), assistantMessage, chat);
}


async function sendQuery(event) {
    event.preventDefault();

    if (activeRun) {
        showAlert("A response is already running.", ERROR_MESSAGE);
        return;
    }

    const query = queryInput.value.trim();
    if (!query || !currentUser || !activeChat?.serverId) {
        showAlert("Please enter a question first.", ERROR_MESSAGE);
        return;
    }

    const options = currentRequestOptions();
    const targetChat = activeChat;
    const assistantMessage = { role: "assistant", content: "...", llm_resources: [] };

    targetChat.messages.push({ role: "user", content: query }, assistantMessage);
    queryInput.value = "";
    renderMessages();

    activeRun = new AbortController();
    setRunState("parsing query", true);

    try {
        const response = await streamChat(
            {
                query,
                chat_id: targetChat.serverId,
                files: options.files,
                tone: options.tone,
                depth: options.depth,
            },
            activeRun.signal,
        );

        if (!response) {
            assistantMessage.content = "The response could not be completed.";
            return;
        }

        if (!response.ok) {
            const data = await parseJsonResponse(response);
            showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
            assistantMessage.content = "The response could not be completed.";
            return;
        }

        await readStream(response, assistantMessage, targetChat);
    } catch (error) {
        assistantMessage.content = error.name === "AbortError"
            ? "Still working. Reopen this chat in a moment."
            : "The response could not be completed.";

        showAlert(
            error.name === "AbortError" ? "Stopped waiting. The answer will finish in this chat." : "Could not reach the chat service.",
            ERROR_MESSAGE,
        );
    } finally {
        activeRun = null;
        setRunState("", false);
        if (activeChat?.id === targetChat.id) renderMessages();
    }
}




/* ------------------------------------------ Events --------------------------------------- */
function bindEvents() {
    queryForm.addEventListener("submit", sendQuery);
    cancelBtn?.addEventListener("click", () => activeRun?.abort());
    addChatBtn.addEventListener("click", () => createChat());

    filesBox.addEventListener("change", updateControlSummary);
    document.querySelectorAll("input[name='chatTone'], input[name='answerDepth']").forEach((input) => {
        input.addEventListener("change", updateControlSummary);
    });
    document.addEventListener("files-selection-updated", updateControlSummary);

    document.addEventListener("app-shell-ready", (event) => {
        const user = event.detail?.user || null;
        user ? loadChats(user) : clearChats();
    });

    window.addEventListener("popstate", () => {
        const slug = currentChatSlug();
        const chat = chats.find((item) => slugify(item.title) === slug);
        if (chat && chat.id !== activeChat?.id) selectChat(chat.id, false);
    });
}


bindEvents();
updateControlSummary();

const user = getActiveShellUser();
user ? loadChats(user) : clearChats();
