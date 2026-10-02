import {
    DATA_ROUTES_PATH,
    ERROR_MESSAGE,
    SUCCESS_MESSAGE,
} from "./constants.js";

import {
    csrfHeaders,
    getActiveShellUser,
    getErrorMessage,
    parseJsonResponse,
    showAlert,
} from "./utils.js";


const uploadPDFBtn = document.querySelector(".chat-settings-modal .add-new-file-btn");
const fileInput = document.querySelector(".chat-settings-modal #fileInput");
const filesContainer = document.querySelector(".chat-settings-modal .file-list");

let filesLoaded = false;
let filesLoading = false;
let filesLoadPromise = null;
let processingPollTimer = null;




/* File Selection Sync */
function getCurrentFileSelections() {
    return new Map(
        Array.from(filesContainer.querySelectorAll("input[type='checkbox']"))
            .map((input) => [input.value.split("_")[0], input.checked])
    );
}


function notifyFileSelectionChanged() {
    filesContainer.dispatchEvent(new Event("change", { bubbles: true }));
    document.dispatchEvent(new Event("files-selection-updated"));
}


/* Files as dropdown */
function createFileOption(file, index, currentSelections = new Map()) {
    const fileName = file.file_name || file.filename || file;
    const fileId = String(file.file_id || fileName);
    const fileStatus = file.asset_status || "ready";
    const isReady = fileStatus === "ready";

    const fileInputId = `files-cb-${index}`;

    const row = document.createElement("div");
    const label = document.createElement("label");
    const meta = document.createElement("span");
    const deleteBtn = document.createElement("button");

    row.className = `file-option-row ${isReady ? "ready" : fileStatus}`;
    label.setAttribute("for", fileInputId);
    label.className = "file-option";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = fileInputId;
    input.name = fileName;
    input.value = `${fileId}_${fileName}`;
    input.disabled = !isReady;
    input.checked = isReady && (currentSelections.has(fileId) ? currentSelections.get(fileId) : true);

    meta.className = "file-status";
    meta.textContent = fileStatus;

    label.appendChild(input);
    label.appendChild(document.createTextNode(fileName));
    label.appendChild(meta);

    deleteBtn.type = "button";
    deleteBtn.className = "file-delete";
    deleteBtn.setAttribute("aria-label", `Delete ${fileName}`);
    deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
    deleteBtn.addEventListener("click", () => deleteFile(fileId));

    row.append(label, deleteBtn);
    return row;
}


function renderUserFiles(files) {
    const currentSelections = getCurrentFileSelections();

    clearTimeout(processingPollTimer);
    filesContainer.innerHTML = "";
    files.forEach((file, index) => {
        filesContainer.appendChild(createFileOption(file, index, currentSelections));
    });

    filesLoaded = true;
    filesContainer.classList.add("active");
    notifyFileSelectionChanged();

    if (files.some((file) => file.asset_status === "processing")) {
        processingPollTimer = setTimeout(() => loadUserFiles(), 3000);
    }
}


async function fetchUserFiles({ showMessages = false } = {}) {
    let response;
    try {
        response = await fetch(
            `${DATA_ROUTES_PATH}/get_user_files`,
            {
                method: "GET",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
            }
        );
    } catch {
        if (showMessages) {
            showAlert("Could not reach the server.", ERROR_MESSAGE);
        }

        return false;
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        if (showMessages) {
            showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        }

        return false;
    }

    const files = Array.from(data.user_files || []);

    if (!files.length) {
        clearTimeout(processingPollTimer);
        filesContainer.innerHTML = "";
        filesLoaded = false;
        notifyFileSelectionChanged();

        if (showMessages) {
            showAlert("No uploaded files found.", "info");
        }

        return false;
    }

    renderUserFiles(files);

    if (showMessages) {
        showAlert("Uploaded files loaded.", SUCCESS_MESSAGE);
    }

    return true;
}


async function loadUserFiles({ showMessages = false } = {}) {
    if (filesLoading) {
        return await filesLoadPromise;
    }

    filesLoading = true;

    try {
        filesLoadPromise = fetchUserFiles({ showMessages });
        return await filesLoadPromise;
    } finally {
        filesLoading = false;
        filesLoadPromise = null;
    }
}

function preloadUserFiles(event = null) {
    const user = event?.detail?.user || getActiveShellUser();
    if (!user) {
        clearTimeout(processingPollTimer);
        filesContainer.innerHTML = "";
        filesContainer.classList.remove("active");
        filesLoaded = false;
        return;
    }

    loadUserFiles();
}


/* Upload & Retrieve Uploaded Files */
async function uploadSelectedFile() {
    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    let response;
    try {
        response = await fetch(
            `${DATA_ROUTES_PATH}/upload`,
            {
                method: "POST",
                credentials: "include",
                headers: csrfHeaders(),
                body: formData,
            }
        );
    } catch {
        showAlert("Could not reach the server.", ERROR_MESSAGE);
        return;
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return;
    }

    showAlert(data.message || "File uploaded. Processing started.", SUCCESS_MESSAGE);
    fileInput.value = "";
    await loadUserFiles();
}


async function deleteFile(fileId) {
    const response = await fetch(
        `${DATA_ROUTES_PATH}/files/${encodeURIComponent(fileId)}`,
        {
            method: "DELETE",
            credentials: "include",
            headers: csrfHeaders(),
        }
    ).catch(() => null);

    if (!response) {
        showAlert("Could not reach the server.", ERROR_MESSAGE);
        return;
    }

    const data = await parseJsonResponse(response);
    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return;
    }

    showAlert(data.message || "File deleted.", SUCCESS_MESSAGE);
    await loadUserFiles({ showMessages: false });
}




/* Wire Logic */
function bindDataEvents() {
    // - uploading
    uploadPDFBtn?.addEventListener("click", (event) => {
        event.preventDefault();
        fileInput.click();
    });

    fileInput?.addEventListener("change", uploadSelectedFile);

    // - load files list
    document.addEventListener("app-shell-ready", preloadUserFiles);
    window.addEventListener("load", preloadUserFiles);
    preloadUserFiles();
}

bindDataEvents();
