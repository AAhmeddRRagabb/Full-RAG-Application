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

const queryForm = document.getElementById("queryForm");
const uploadPDFBtn = queryForm.querySelector(".buttons div .upload-pdf");
const fileInput = queryForm.querySelector(".buttons div #fileInput");
const listFilesBtn = document.querySelector(".chat-header .control-area .list-files-btn");
const filesContainer = document.querySelector(".chat-header .control-area .files");




// Create a selectable file row for the files menu.
function createFileOption(fileName, index) {
    const fileInputId = `files-cb-${index}`;
    const label = document.createElement("label");
    label.setAttribute("for", fileInputId);
    label.className = "file";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = fileInputId;
    input.name = fileName;
    input.value = fileName;
    input.checked = true;

    label.appendChild(input);
    label.appendChild(document.createTextNode(fileName));

    return label;
}




// Toggle the visible files menu off.
function closeFilesMenu() {
    filesContainer.innerHTML = "";
    filesContainer.classList.remove("active");
}




// Upload and process the selected file.
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
    closeFilesMenu();
}




// Fetch and display the current user's uploaded files.
async function toggleUserFiles() {
    if (filesContainer.classList.contains("active")) {
        closeFilesMenu();
        return;
    }

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
        showAlert("Could not reach the server.", ERROR_MESSAGE);
        return;
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return;
    }

    const files = Array.from(data.user_files || []);

    if (!files.length) {
        showAlert("No uploaded files found.", "info");
        return;
    }

    filesContainer.innerHTML = "";
    files.forEach((fileName, index) => {
        filesContainer.appendChild(createFileOption(fileName, index));
    });

    filesContainer.classList.add("active");
    showAlert("Uploaded files loaded.", SUCCESS_MESSAGE);
}




// Wire data UI events.
function bindDataEvents() {
    uploadPDFBtn.addEventListener("click", (event) => {
        event.preventDefault();
        fileInput.click();
    });

    fileInput.addEventListener("change", uploadSelectedFile);
    listFilesBtn.addEventListener("click", toggleUserFiles);
}

bindDataEvents();
