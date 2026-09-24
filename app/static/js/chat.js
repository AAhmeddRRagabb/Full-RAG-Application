

import { CHAT_ROUTES_PATH, ERROR_MESSAGE } from "./constants.js";
import { getActiveShellUser, getErrorMessage, parseJsonResponse, showAlert } from "./utils.js";


const headerTitle  = document.querySelector(".header-title");
const messagesArea = document.getElementById("messages");

const queryForm  = document.getElementById("queryForm");
const queryInput = document.getElementById("queryArea");

const chatsList     = document.querySelector(".chats-list");
const addNewChatBtn = document.querySelector(".add-new-chat-btn");

const searchOnlineBtn = document.querySelector(".chat-settings-modal .search-online-btn");
const filesContainer  = document.querySelector(".chat-settings-modal .file-list");
const resourcesStatus = document.querySelector(".chat-settings-modal .resources-status");

const customConfigurations = document.querySelector(".custom-configurations");
const toneOptions          = Array.from(document.querySelectorAll(".tone-option"));
const configInputs         = Array.from(document.querySelectorAll(".config-input"));

const customDefaults = { temperature: 0.5, max_tokens: 512, top_p: 0.9 };
let chats = [];
let activeChat    = null;
let currentUser   = null;
let settingsTimer = null;




/* ------------------------------------------ Helpful Functions --------------------------------------- */

function normalizeSettings(settings = {}) {
    const tone = ["technical", "creative", "custom"].includes(settings?.tone) ? settings.tone : "technical";

    return {
        search_online: Boolean(settings?.search_online),
        files        : Array.isArray(settings?.files) ? settings.files.map(String) : null,
        tone,
        model_configurations: tone === "custom" ? { ...customDefaults, ...(settings?.model_configurations || {}) } : null,
    };
}


function normalizeChat(chat = {}) {
    return {
        id      : chat.chat_id ? String(chat.chat_id) : crypto.randomUUID(),
        serverId: chat.chat_id || null, //!
        title   : chat.chat_name || `chat #${chats.length + 1}`,
        settings: normalizeSettings(chat.settings),
        messages: Array.from(chat.messages || []),
    };
}


function jsonOptions(method, body = null) {
    return {
        method,
        credentials: "include",
        headers    : { "Content-Type": "application/json" },
        ...(body ? { body: JSON.stringify(body) } : {}),
    };
}

/* ------------------------------------------ Acquiring User Selections --------------------------------------- */
function selectedTone() {
    return document.querySelector(".tone-option.selected")?.dataset.tone || "technical";
}

function selectedFiles() {
    const inputs = Array.from(filesContainer.querySelectorAll("input[type='checkbox']"));
    return inputs.length ? inputs.filter((input) => input.checked).map((input) => input.value) : activeChat?.settings.files ?? null;
}

function customConfig() {
    return Object.fromEntries(configInputs.map((input) => [input.dataset.configKey, Number(input.value)]));
}


function readSettings() {
    const tone = selectedTone();

    return normalizeSettings({
        search_online: searchOnlineBtn.classList.contains("active"),
        files        : selectedFiles(),
        tone,
        model_configurations: tone === "custom" ? customConfig() : null,
    });
}


function updateResourcesStatus() {
    if (!activeChat) return;

    const parts = [];
    const files = selectedFiles();

    if (activeChat.settings.search_online) parts.push("web");
    if (files?.length) parts.push(`${files.length} file${files.length === 1 ? "" : "s"}`);

    resourcesStatus.textContent = parts.length ? `Using ${parts.join(" + ")}.` : "Nothing selected.";
}


/* ------------------------------------------ API Function --------------------------------------- */
async function chatApi(path, options) {
    let response;

    try {
        response = await fetch(`${CHAT_ROUTES_PATH}${path}`, options);
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



/* ------------------------------------------ Manage Chat Settings --------------------------------------- */
async function saveSettings(settings = readSettings()) {
    if (!activeChat) return;

    activeChat.settings = normalizeSettings(settings);
    updateResourcesStatus();

    if (!currentUser || !activeChat.serverId) return;

    const data = await chatApi(`/chats/${activeChat.serverId}/settings`, jsonOptions("PATCH", {
        settings: activeChat.settings,
    }));

    if (data?.chat) activeChat.settings = normalizeSettings(data.chat.settings);
}


function queueSettingsSave() {
    clearTimeout(settingsTimer);
    settingsTimer = setTimeout(() => saveSettings(), 300);
}


function applySettings() {
    if (!activeChat) return;

    const settings = activeChat.settings;
    const isCustom = settings.tone === "custom";


    searchOnlineBtn.classList.toggle("active", settings.search_online);
    searchOnlineBtn.setAttribute("aria-pressed", String(settings.search_online));
    customConfigurations.classList.toggle("inactive", !isCustom);

    toneOptions.forEach((option) => {
        const selected = option.dataset.tone === settings.tone;
        option.classList.toggle("selected", selected);
        option.setAttribute("aria-pressed", String(selected));
    });


    configInputs.forEach((input) => {
        const value    = settings.model_configurations?.[input.dataset.configKey] ?? input.value;
        input.disabled = !isCustom;
        input.value    = value;
        input.nextElementSibling.textContent = value;
    });

    filesContainer.querySelectorAll("input[type='checkbox']").forEach((input) => {
        input.checked = settings.files === null || settings.files.includes(input.value);
    });

    updateResourcesStatus();
}

/* ------------------------------------------ Manage Messages --------------------------------------- */
function normalizeLlmResources(llm_resources = null) {
    if (!llm_resources) return [];

    return Array.isArray(llm_resources)
        ? llm_resources.filter(Boolean)
        : [llm_resources].filter(Boolean);
}


function messageNode(role, content, llm_resources = null ) {
    const message      = document.createElement("article");
    const avatar       = document.createElement("div");
    const contentGroup = document.createElement("div");
    const body         = document.createElement("div");
    const resources    = normalizeLlmResources(llm_resources);

    message.className      = `message ${role === "user" ? "user-message" : "assistant-message"}`;
    avatar.className       = "avatar";
    contentGroup.className = "message-body";
    body.className         = "message-content";
    
    avatar.textContent = role === "user" ? "You" : "AI";
    body.innerHTML     = DOMPurify.sanitize(marked.parse(content));
    contentGroup.append(body);

    if (role !== "user" && resources.length) {
        const resourcesList = document.createElement("div");
        resourcesList.className = "message-llm-resources";

        resources.forEach(llm_resource => {
            const resource = document.createElement("span");
            resource.className = "message-llm-resource";
            resource.innerHTML = '<i class="fa-solid fa-bookmark"></i>';
            resource.append(document.createTextNode(String(llm_resource)));
            resourcesList.append(resource);
        }); 

        contentGroup.append(resourcesList);
    }

    message.append(...(role === "user" ? [contentGroup, avatar] : [avatar, contentGroup]));

    return message;
}


function renderMessages() {
    messagesArea.innerHTML = "";

    if (!activeChat) return;

    headerTitle.textContent = activeChat.title;

    if (!activeChat.messages.length) {
        messagesArea.appendChild(messageNode("assistant", "Ask a question to begin."));
        return;
    }

    activeChat.messages.forEach((message) => {
        messagesArea.appendChild(messageNode(
            message.role, message.content, message.llm_resources
        ))
    });
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

/* ------------------------------------------ Load / Render Chats --------------------------------------- */
function renderChats() {
    chatsList.innerHTML = "";

    chats.forEach((chat) => {
        const item      = document.createElement("article");
        const selectBtn = document.createElement("button");
        const actions   = document.createElement("div");
        const editBtn   = document.createElement("button");
        const deleteBtn = document.createElement("button");

        item.className      = `chat-item ${chat.id === activeChat?.id ? "active" : ""}`;
        selectBtn.className = "chat-select";
        actions.className   = "chat-actions";
        editBtn.className   = "chat-edit-name";
        deleteBtn.className = "chat-delete";

        
        selectBtn.type = "button";
        selectBtn.textContent = chat.title;
        selectBtn.addEventListener("click", () => selectChat(chat.id));
        
        editBtn.type = "button";
        editBtn.setAttribute("aria-label", "Rename this chat");
        editBtn.innerHTML = '<i class="fa-solid fa-pen"></i>';
        editBtn.addEventListener("click", () => renameChat(chat, selectBtn));
        
        deleteBtn.type = "button";
        deleteBtn.setAttribute("aria-label", "Delete this chat");
        deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        deleteBtn.addEventListener("click", () => deleteChat(chat));

        actions.append(editBtn, deleteBtn);
        item.append(selectBtn, actions);
        chatsList.appendChild(item);
    });
}


async function selectChat(chatId) {
    activeChat = chats.find((chat) => chat.id === chatId) || null;
    renderChats();
    applySettings();
    renderMessages();

    if (!currentUser || !activeChat?.serverId) return;

    const data = await chatApi(`/chats/${activeChat.serverId}`, jsonOptions("GET"));
    if (!data) return;

    activeChat.title    = data.chat.chat_name;
    activeChat.settings = normalizeSettings(data.chat.settings);
    activeChat.messages = Array.from(data.messages || []);

    renderChats();
    applySettings();
    renderMessages();
}


async function loadChats(user) {
    currentUser = user;

    const data = await chatApi("/chats", jsonOptions("GET"));
    chats = Array.from(data?.chats || []).map(normalizeChat);

    if (!chats.length) {
        await addChat("chat #1");
        return;
    }

    await selectChat(chats[0].id);
}


function loadVisitorChat() {
    currentUser = null;
    chats = [normalizeChat({ chat_name: "chat #1" })];
    activeChat = chats[0];

    renderChats();
    applySettings();
    renderMessages();
}


/* ------------------------------------------ Add / Edit / Delete Chats --------------------------------------- */
async function addChat(chatName = null) {
    let chat = normalizeChat({ chat_name: chatName });

    if (currentUser) {
        const data = await chatApi("/chats", jsonOptions("POST", { chat_name: chatName }));
        if (!data?.chat) return;
        chat = normalizeChat(data.chat);
    }

    chats.push(chat);
    await selectChat(chat.id);
}


function renameChat(chat, selectBtn) {
    const oldTitle = chat.title;
    const input    = document.createElement("input");
    let done       = false;

    input.className = "chat-rename-input";
    input.value     = chat.title;
    selectBtn.replaceWith(input);

    input.focus();
    input.select();

    const finish = async (save) => {
        if (done) return;
        done = true;
        chat.title = save ? input.value.trim() || oldTitle : oldTitle;

        if (save && currentUser && chat.serverId) {
            await chatApi(`/chats/${chat.serverId}`, jsonOptions("PATCH", { chat_name: chat.title }));
        }

        renderChats();
        renderMessages();
    };

    input.addEventListener("input", () => {
        chat.title = input.value.trim() || "Untitled chat";
        if (activeChat?.id === chat.id) headerTitle.textContent = chat.title;
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") finish(true);
        if (event.key === "Escape") finish(false);
    });

    input.addEventListener("blur", () => finish(true), { once: true });
}


async function deleteChat(chat) {
    if (currentUser && chat.serverId) {
        const data = await chatApi(`/chats/${chat.serverId}`, jsonOptions("DELETE"));
        if (!data) return;
    }

    chats = chats.filter((item) => item.id !== chat.id);

    if (!chats.length) {
        await addChat("chat #1");
        return;
    }

    await selectChat((activeChat?.id === chat.id ? chats[0] : activeChat).id);
}

/* ------------------------------------------ Send Query --------------------------------------- */
async function sendQuery(event) {
    event.preventDefault();

    const query = queryInput.value.trim();
    if (!query || !activeChat) {
        showAlert("Please enter a question first.", ERROR_MESSAGE);
        return;
    }

    const settings = readSettings();
    activeChat.settings = settings;
    activeChat.messages.push({ role: "user", content: query });

    queryInput.value = "";
    renderMessages();

    const data = await chatApi("/chat", jsonOptions("POST", {
        query,
        chat_id       : activeChat.serverId,
        retrieve_limit: 5,
        settings,
    }));

    if (!data) return;

    activeChat.settings = normalizeSettings(data.settings);
    activeChat.messages.push({ role: "assistant", content: data.report || "No answer was returned.", llm_resources: data.llm_resources || {} });

    applySettings();
    renderMessages();
}



/* ------------------------------------------ Driver Functions --------------------------------------- */
function handleShellReady(event) {
    const user = event.detail?.user || null;
    user ? loadChats(user) : loadVisitorChat();
}


function bindEvents() {
    queryForm.addEventListener("submit", sendQuery);

    addNewChatBtn.addEventListener("click", () => addChat());

    searchOnlineBtn.addEventListener("click", () => {
        searchOnlineBtn.classList.toggle("active");
        searchOnlineBtn.setAttribute("aria-pressed", String(searchOnlineBtn.classList.contains("active")));
        saveSettings();
    });

    filesContainer.addEventListener("change", () => saveSettings());
    document.addEventListener("files-selection-updated", () => {
        applySettings();
        saveSettings();
    });
    
    document.addEventListener("app-shell-ready", handleShellReady);

    toneOptions.forEach((option) => {
        option.addEventListener("click", () => {
            toneOptions.forEach((item) => item.classList.remove("selected"));
            option.classList.add("selected");
            activeChat.settings = readSettings();
            applySettings();
            saveSettings(activeChat.settings);
        });
    });

    configInputs.forEach((input) => {
        input.addEventListener("input", () => {
            input.nextElementSibling.textContent = input.value;
            queueSettingsSave();
        });
    });
}


function init() {
    bindEvents();

    const user = getActiveShellUser();
    user ? loadChats(user) : loadVisitorChat();
}


init();
