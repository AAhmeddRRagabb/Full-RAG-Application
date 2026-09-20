import {
    DATA_ROUTES_PATH,
    ERROR_MESSAGE,
    SUCCESS_MESSAGE,
} from "./constants.js";

import {
    getErrorMessage,
    parseJsonResponse,
    showAlert,
} from "./utils.js";


const uploadPDFBtn = document.querySelector(".control-area .upload-pdf");
const fileInput = document.querySelector(".control-area #fileInput");
const listFilesBtn = document.querySelector(".control-area .list-files-btn");
const filesContainer = document.querySelector(".control-area .files");

let filesLoaded = false;
let filesLoading = false;
let filesLoadPromise = null;




/* File Selection Sync */
function getCurrentFileSelections() {
    return new Map(
        Array.from(filesContainer.querySelectorAll("input[type='checkbox']"))
            .map((input) => [input.value, input.checked])
    );
}


function notifyFileSelectionChanged() {
    filesContainer.dispatchEvent(new Event("change", { bubbles: true }));
}


/* Files as dropdown */
function createFileOption(file, index, currentSelections = new Map()) {
    const fileName = file.file_name || file;
    const fileId = file.file_id || fileName;

    const fileInputId = `files-cb-${index}`;

    const label = document.createElement("label");
    label.setAttribute("for", fileInputId);
    label.className = "file";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = fileInputId;
    input.name = fileName;
    input.value = fileId;
    input.checked = currentSelections.has(fileId) ? currentSelections.get(fileId) : true;

    label.appendChild(input);
    label.appendChild(document.createTextNode(fileName));

    return label;
}


function setFilesMenuVisibility(isVisible) {
    filesContainer.classList.toggle("active", isVisible);
}


function renderUserFiles(files) {
    const currentSelections = getCurrentFileSelections();

    filesContainer.innerHTML = "";
    files.forEach((file, index) => {
        filesContainer.appendChild(createFileOption(file, index, currentSelections));
    });

    filesLoaded = true;
    notifyFileSelectionChanged();
}


function closeFilesMenu() {
    setFilesMenuVisibility(false);
}


async function fetchUserFiles({ showMenu = false, showMessages = false } = {}) {
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
        filesContainer.innerHTML = "";
        filesLoaded = false;
        notifyFileSelectionChanged();

        if (showMessages) {
            showAlert("No uploaded files found.", "info");
        }

        return false;
    }

    renderUserFiles(files);
    setFilesMenuVisibility(showMenu);

    if (showMessages) {
        showAlert("Uploaded files loaded.", SUCCESS_MESSAGE);
    }

    return true;
}


async function loadUserFiles({ showMenu = false, showMessages = false } = {}) {
    if (filesLoading) {
        const filesWereLoaded = await filesLoadPromise;

        if (showMenu && filesWereLoaded) {
            setFilesMenuVisibility(true);
            notifyFileSelectionChanged();
        }

        return filesWereLoaded;
    }

    filesLoading = true;

    try {
        filesLoadPromise = fetchUserFiles({ showMenu, showMessages });
        return await filesLoadPromise;
    } finally {
        filesLoading = false;
        filesLoadPromise = null;
    }
}

function preloadUserFiles() {
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

    showAlert(data.message || "File uploaded successfully.", SUCCESS_MESSAGE);
    fileInput.value = "";
    await loadUserFiles();
    closeFilesMenu();
}


async function toggleUserFiles() {
    if (filesContainer.classList.contains("active")) {
        closeFilesMenu();
        return;
    }

    if (filesLoaded) {
        setFilesMenuVisibility(true);
        notifyFileSelectionChanged();
        return;
    }

    await loadUserFiles({ showMenu: true, showMessages: true });
}




/* Wire Logic */
function bindDataEvents() {
    uploadPDFBtn.addEventListener("click", (event) => {
        event.preventDefault();
        fileInput.click();
    });

    fileInput.addEventListener("change", uploadSelectedFile);
    listFilesBtn.addEventListener("click", toggleUserFiles);
    document.addEventListener("app-shell-ready", preloadUserFiles);
    window.addEventListener("load", preloadUserFiles);
    preloadUserFiles();
}

bindDataEvents();
