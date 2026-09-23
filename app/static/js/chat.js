import {
    CHAT_ROUTES_PATH,
    ERROR_MESSAGE,
} from "./constants.js";

import {
    getErrorMessage,
    parseJsonResponse,
    showAlert,
} from "./utils.js";


const headerTitle = document.querySelector(".header-title");
const queryForm = document.getElementById("queryForm");
const queryInput = document.getElementById("queryArea");
const messagesArea = document.getElementById("messages");

const chatsList = document.querySelector(".chats-list");
const addNewChatBtn = document.querySelector(".add-new-chat-btn");

const resourcesStatus = document.querySelector(".chat-settings-modal .resources-status");
const searchOnlineBtn = document.querySelector(".chat-settings-modal .search-online-btn");
const filesContainer = document.querySelector(".chat-settings-modal .file-list");
const customConfigurations = document.querySelector(".custom-configurations");
const toneOptions = Array.from(document.querySelectorAll(".tone-option"));
const configInputs = Array.from(document.querySelectorAll(".config-input"));

const defaultConfig = {
    temperature: 0.7,
    max_tokens: 1024,
    top_p: 0.9,
};

let chats = [];
let activeChatId = null;




/* Chat State */
function createChat() {
    const chatNumber = chats.length + 1;

    return {
        id: crypto.randomUUID(),
        title: chatNumber === 1 ? "New Chat" : `Chat ${chatNumber}`,
        messages: [],
        settings: {
            searchOnline: false,
            files: null,
            tone: "technical",
            modelConfig: {
                ...defaultConfig,
            },
        },
    };
}




function getActiveChat() {
    return chats.find((chat) => chat.id === activeChatId);
}




function getAllFileIds() {
    return Array.from(filesContainer.querySelectorAll("input[type='checkbox']"))
        .map((input) => input.value);
}




function getSelectedFiles() {
    return Array.from(filesContainer.querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => input.value);
}




function getSelectedResources() {
    const activeChat = getActiveChat();

    return {
        search_online: Boolean(activeChat?.settings.searchOnline),
        files: getSelectedFiles(),
        tone: activeChat?.settings.tone || "technical",
        model_configurations: activeChat?.settings.modelConfig || defaultConfig,
    };
}




function setActiveChat(chatId) {
    activeChatId = chatId;
    renderChatList();
    renderMessages();
    applyActiveChatSettings();
}




function addChat() {
    const chat = createChat();
    chats.push(chat);
    setActiveChat(chat.id);
}




function deleteChat(chatId) {
    if (chats.length === 1) {
        showAlert("Keep at least one chat open.", "info");
        return;
    }

    chats = chats.filter((chat) => chat.id !== chatId);

    if (activeChatId === chatId) {
        setActiveChat(chats[0].id);
        return;
    }

    renderChatList();
}




function renameChat(chatId, chatItem) {
    const chat = chats.find((item) => item.id === chatId);
    const selectButton = chatItem?.querySelector(".chat-select");

    if (!chat || !selectButton) {
        return;
    }

    const previousTitle = chat.title;
    const renameInput = document.createElement("input");
    renameInput.type = "text";
    renameInput.className = "chat-rename-input";
    renameInput.value = chat.title;
    renameInput.setAttribute("aria-label", "Rename chat");

    selectButton.replaceWith(renameInput);
    renameInput.focus();
    renameInput.select();

    let isRenameFinished = false;

    const commitRename = () => {
        if (isRenameFinished) {
            return;
        }

        isRenameFinished = true;
        chat.title = renameInput.value.trim() || previousTitle;
        renderChatList();

        if (activeChatId === chatId) {
            headerTitle.textContent = chat.title;
        }
    };

    const cancelRename = () => {
        if (isRenameFinished) {
            return;
        }

        isRenameFinished = true;
        chat.title = previousTitle;
        renderChatList();

        if (activeChatId === chatId) {
            headerTitle.textContent = chat.title;
        }
    };

    renameInput.addEventListener("input", () => {
        chat.title = renameInput.value.trim() || "Untitled chat";

        if (activeChatId === chatId) {
            headerTitle.textContent = chat.title;
        }
    });

    renameInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            commitRename();
        }

        if (event.key === "Escape") {
            cancelRename();
        }
    });

    renameInput.addEventListener("blur", commitRename);
}




/* Render Messages */
function getReport(responseText) {
    return DOMPurify.sanitize(
        marked.parse(responseText)
    );
}




function createMessageElement(role, message) {
    const report = document.createElement("article");
    report.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "You" : "AI";

    const content = document.createElement("div");
    content.classList.add("message-content");
    content.innerHTML = getReport(message);

    if (role === "user") {
        report.appendChild(content);
        report.appendChild(avatar);
    } else {
        report.appendChild(avatar);
        report.appendChild(content);
    }

    return report;
}




function renderMessages() {
    const activeChat = getActiveChat();
    messagesArea.innerHTML = "";

    if (!activeChat) {
        return;
    }

    headerTitle.textContent = activeChat.title;

    if (!activeChat.messages.length) {
        messagesArea.appendChild(createMessageElement("assistant", "Ask a question to begin."));
        return;
    }

    activeChat.messages.forEach((message) => {
        messagesArea.appendChild(createMessageElement(message.role, message.content));
    });

    messagesArea.scrollTop = messagesArea.scrollHeight;
}




function appendMessage(role, content) {
    const activeChat = getActiveChat();

    if (!activeChat) {
        return;
    }

    activeChat.messages.push({ role, content });

    if (role === "user" && activeChat.messages.length === 1) {
        activeChat.title = content.length > 42 ? `${content.slice(0, 42)}...` : content;
        renderChatList();
    }

    renderMessages();
}




/* Render Chats */
function createChatItem(chat) {
    const item = document.createElement("article");
    item.className = `chat-item ${chat.id === activeChatId ? "active" : ""}`;

    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.className = "chat-select";
    selectButton.textContent = chat.title;
    selectButton.setAttribute("aria-label", `Open workspace chat: ${chat.title}`);
    selectButton.addEventListener("click", () => setActiveChat(chat.id));

    const actions = document.createElement("div");
    actions.className = "chat-actions";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.className = "chat-edit-name";
    editButton.setAttribute("aria-label", "Rename this chat");
    editButton.innerHTML = '<i class="fa-solid fa-pen"></i>';
    editButton.addEventListener("click", () => renameChat(chat.id, item));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "chat-delete";
    deleteButton.setAttribute("aria-label", "Delete this chat");
    deleteButton.innerHTML = '<i class="fa-solid fa-trash"></i>';
    deleteButton.addEventListener("click", () => deleteChat(chat.id));

    actions.append(editButton, deleteButton);
    item.append(selectButton, actions);

    return item;
}




function renderChatList() {
    chatsList.innerHTML = "";

    chats.forEach((chat) => {
        chatsList.appendChild(createChatItem(chat));
    });
}




/* Chat Settings */
function updateResourcesStatus() {
    const activeChat = getActiveChat();
    const statusParts = [];
    const selectedFiles = getSelectedFiles();

    if (!activeChat) {
        return;
    }

    if (activeChat.settings.searchOnline) {
        statusParts.push("Web");
    }

    if (selectedFiles.length) {
        statusParts.push(`${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"}`);
    }

    resourcesStatus.textContent = statusParts.length
        ? `Using ${statusParts.join(" + ")}.`
        : "Nothing selected.";
}




function applyFileSettings() {
    const activeChat = getActiveChat();
    const checkboxes = Array.from(filesContainer.querySelectorAll("input[type='checkbox']"));

    if (!activeChat || !checkboxes.length) {
        updateResourcesStatus();
        return;
    }

    if (activeChat.settings.files === null) {
        checkboxes.forEach((input) => {
            input.checked = true;
        });
        activeChat.settings.files = getAllFileIds();
    } else {
        checkboxes.forEach((input) => {
            input.checked = activeChat.settings.files.includes(input.value);
        });
    }

    updateResourcesStatus();
}




function applyToneSettings() {
    const activeChat = getActiveChat();
    const activeTone = activeChat?.settings.tone || "technical";
    const isCustomTone = activeTone === "custom";

    toneOptions.forEach((option) => {
        const isSelected = option.dataset.tone === activeTone;
        option.classList.toggle("selected", isSelected);
        option.setAttribute("aria-pressed", String(isSelected));
    });

    customConfigurations.classList.toggle("inactive", !isCustomTone);

    configInputs.forEach((input) => {
        input.disabled = !isCustomTone;
    });
}




function applyConfigSettings() {
    const activeChat = getActiveChat();

    configInputs.forEach((input) => {
        const configValue = activeChat?.settings.modelConfig[input.dataset.configKey] ?? input.value;
        input.value = configValue;
        input.nextElementSibling.textContent = configValue;
    });
}




function applyActiveChatSettings() {
    const activeChat = getActiveChat();

    if (!activeChat) {
        return;
    }

    searchOnlineBtn.classList.toggle("active", activeChat.settings.searchOnline);
    searchOnlineBtn.setAttribute("aria-pressed", String(activeChat.settings.searchOnline));

    applyToneSettings();
    applyConfigSettings();
    applyFileSettings();
}




function syncSelectedFiles() {
    const activeChat = getActiveChat();

    if (!activeChat) {
        return;
    }

    activeChat.settings.files = getSelectedFiles();
    updateResourcesStatus();
}




function toggleSearchOnline() {
    const activeChat = getActiveChat();

    if (!activeChat) {
        return;
    }

    activeChat.settings.searchOnline = !activeChat.settings.searchOnline;
    applyActiveChatSettings();
}




function selectTone(event) {
    const activeChat = getActiveChat();
    const selectedTone = event.currentTarget.dataset.tone;

    if (!activeChat || !selectedTone) {
        return;
    }

    activeChat.settings.tone = selectedTone;
    applyToneSettings();
}




function updateModelConfiguration(event) {
    const activeChat = getActiveChat();
    const input = event.currentTarget;
    const configKey = input.dataset.configKey;
    const value = Number(input.value);

    if (!activeChat || !configKey) {
        return;
    }

    activeChat.settings.modelConfig[configKey] = value;
    input.nextElementSibling.textContent = input.value;
}




/* Chat Request */
async function sendQuery(event) {
    event.preventDefault();

    const query = queryInput.value.trim();

    if (!query) {
        showAlert("Please enter a question first.", ERROR_MESSAGE);
        return;
    }

    syncSelectedFiles();

    const selectedResources = getSelectedResources();
    const requestBody = {
        query          : query,
        retrieve_limit : 5,
        search_online  : selectedResources.search_online,
        files          : selectedResources.files,
        tone           : selectedResources.tone,
        model_config   : selectedResources.model_configurations,
    };

    appendMessage("user", query);
    queryInput.value = "";

    let response;
    try {
        response = await fetch(
            `${CHAT_ROUTES_PATH}/chat`,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(requestBody),
            }
        );
    } catch {
        showAlert("Could not reach the chat service.", ERROR_MESSAGE);
        return;
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return;
    }

    appendMessage("assistant", data.answer || data.message || "No answer was returned.");
}




/* Wire Logic */
function bindChatEvents() {
    queryForm.addEventListener("submit", sendQuery);
    addNewChatBtn.addEventListener("click", addChat);
    searchOnlineBtn.addEventListener("click", toggleSearchOnline);
    filesContainer.addEventListener("change", syncSelectedFiles);
    document.addEventListener("files-selection-updated", applyFileSettings);

    toneOptions.forEach((option) => {
        option.addEventListener("click", selectTone);
    });

    configInputs.forEach((input) => {
        input.addEventListener("input", updateModelConfiguration);
    });
}




function initializeChats() {
    const initialChat = createChat();
    chats = [initialChat];
    activeChatId = initialChat.id;

    bindChatEvents();
    renderChatList();
    renderMessages();
    applyActiveChatSettings();
}

initializeChats();
