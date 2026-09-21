import {
    CHAT_ROUTES_PATH,
    ERROR_MESSAGE,
} from "./constants.js";

import {
    getErrorMessage,
    parseJsonResponse,
    showAlert,
} from "./utils.js";


const resourcesStatus = document.querySelector(".control-area .resources-status");

const searchOnlineBtn = document.querySelector(".control-area .search-online-btn");

const filesContainer = document.querySelector(".control-area .files");

const queryForm = document.getElementById("queryForm");
const queryInput = document.getElementById("queryArea");
const messagesArea = document.getElementById("messages");

let searchOnlineSelected = false;




/* Render Markdown Response */
function getReport(responseText) {
    return DOMPurify.sanitize(
        marked.parse(responseText)
    );
}


/* Messages */
function generateUserMessage(message) {
    const report = document.createElement("article");
    report.className = "message user-message";

    const content = document.createElement("div");
    content.classList.add("message-content");
    content.innerHTML = getReport(message);
    report.appendChild(content);

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "You";
    report.appendChild(avatar);

    messagesArea.appendChild(report);
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

function generateAIMessage(message) {
    const report = document.createElement("article");
    report.className = "message assistant-message";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "AI";
    report.appendChild(avatar);

    const content = document.createElement("div");
    content.classList.add("message-content");
    content.innerHTML = getReport(message);
    report.appendChild(content);

    messagesArea.appendChild(report);
    messagesArea.scrollTop = messagesArea.scrollHeight;
}




/* Selected Resources */
function getSelectedFiles() {
    return Array.from(filesContainer.querySelectorAll("input[type='checkbox']:checked"))
        .map((fileInput) => fileInput.value);
}

function getSelectedResources() {
    const filesToUse = getSelectedFiles();

    return {
        search_online: searchOnlineSelected,
        files: filesToUse,
    }
}


function updateResourcesStatus() {
    const selectedFiles = getSelectedFiles();
    const statusParts = [];

    if (searchOnlineSelected) {
        statusParts.push("Online search");
    }

    if (selectedFiles.length) {
        statusParts.push(`${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"}`);
    }

    resourcesStatus.textContent = statusParts.length
        ? `Selected: ${statusParts.join(" + ")}.`
        : "Nothing selected.";
}



function toggleSearchOnline() {
    searchOnlineSelected = !searchOnlineSelected;
    searchOnlineBtn.classList.toggle("active", searchOnlineSelected);
    searchOnlineBtn.setAttribute("aria-pressed", String(searchOnlineSelected));
    updateResourcesStatus();
}



/* Chat */
async function sendQuery(event) {
    event.preventDefault();
    const query = queryInput.value.trim();

    if (!query) {
        showAlert("Please enter a question first.", ERROR_MESSAGE);
        return;
    }

    const selectedResources = getSelectedResources();
    const requestBody = {
        query         : query,
        retrieve_limit: 5,
        search_online : selectedResources.search_online,
        files         : selectedResources.files
    };

    generateUserMessage(query);
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

    generateAIMessage(data.answer || data.message || "No answer was returned.");
}




/* Wire Logic */
function bindChatEvents() {
    searchOnlineBtn.addEventListener("click", toggleSearchOnline);
    filesContainer.addEventListener("change", updateResourcesStatus);
    queryForm.addEventListener("submit", sendQuery);
    updateResourcesStatus();
}

bindChatEvents();
