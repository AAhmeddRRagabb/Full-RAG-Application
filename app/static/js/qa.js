import { DATA_ROUTES_PATH, ERROR_MESSAGE, SUCCESS_MESSAGE } from "./constants.js";
import { csrfHeaders, getActiveShellUser, getErrorMessage, parseJsonResponse, showAlert } from "./utils.js";

const list = document.getElementById("filesList");
const fileInput = document.getElementById("fileInput");
const uploadButton = document.getElementById("uploadButton");
const questionForm = document.getElementById("questionForm");
const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");
const answerContent = document.getElementById("answerContent");
const answerSources = document.getElementById("answerSources");


// Render the user's PDFs with their current selection.
function renderFiles(files) {
    const selected = new Map([...list.querySelectorAll("input:checked")].map((input) => [input.value, true]));
    const existing = new Set([...list.querySelectorAll("input")].map((input) => input.value));
    list.replaceChildren();

    if (!files.length) {
        const empty = document.createElement("p");
        empty.className = "empty-files";
        empty.textContent = "No PDFs yet. Use + to upload your first file.";
        list.append(empty);
        return;
    }

    files.forEach((file) => {
        const row = document.createElement("div");
        const label = document.createElement("label");
        const checkbox = document.createElement("input");
        const name = document.createElement("span");
        const remove = document.createElement("button");

        row.className = "file-row";
        checkbox.type = "checkbox";
        checkbox.value = String(file.file_id);
        checkbox.checked = !existing.has(checkbox.value) || selected.has(checkbox.value);
        name.className = "file-name";
        name.textContent = file.filename;
        name.title = file.filename;
        label.append(checkbox, name);

        remove.type = "button";
        remove.className = "file-delete";
        remove.setAttribute("aria-label", `Delete ${file.filename}`);
        remove.innerHTML = '<i class="fa-solid fa-trash" aria-hidden="true"></i>';
        remove.addEventListener("click", () => deleteFile(file.file_id));
        row.append(label, remove);
        list.append(row);
    });
}


// Load the PDFs owned by the signed-in user.
async function loadFiles() {
    try {
        const response = await fetch(`${DATA_ROUTES_PATH}/get_user_files`, { credentials: "include" });
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(getErrorMessage(response, data));
        renderFiles(data.user_files || []);
    } catch (error) {
        showAlert(error.message || "Could not load PDFs.", ERROR_MESSAGE);
    }
}


// Upload and process a PDF before showing it as ready.
async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) return;

    const body = new FormData();
    body.append("file", file);
    uploadButton.disabled = true;
    uploadButton.setAttribute("aria-label", "Uploading PDF");
    try {
        const response = await fetch(`${DATA_ROUTES_PATH}/upload`, {
            method: "POST",
            credentials: "include",
            headers: csrfHeaders(),
            body,
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(getErrorMessage(response, data));
        showAlert(data.message || "PDF ready to use.", SUCCESS_MESSAGE);
        await loadFiles();
    } catch (error) {
        showAlert(error.message || "Could not upload PDF.", ERROR_MESSAGE);
    } finally {
        fileInput.value = "";
        uploadButton.disabled = false;
        uploadButton.setAttribute("aria-label", "Upload PDF");
    }
}


// Delete one owned PDF.
async function deleteFile(fileId) {
    try {
        const response = await fetch(`${DATA_ROUTES_PATH}/files/${fileId}`, {
            method: "DELETE",
            credentials: "include",
            headers: csrfHeaders(),
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(getErrorMessage(response, data));
        showAlert(data.message || "PDF deleted.", SUCCESS_MESSAGE);
        await loadFiles();
    } catch (error) {
        showAlert(error.message || "Could not delete PDF.", ERROR_MESSAGE);
    }
}


// Show one answer and its PDF pages.
function renderAnswer(answer, sources = [], loading = false) {
    answerContent.classList.remove("empty");
    answerContent.classList.toggle("loading", loading);
    answerContent.innerHTML = window.DOMPurify && window.marked
        ? DOMPurify.sanitize(marked.parse(answer))
        : "";
    if (!window.DOMPurify || !window.marked) answerContent.textContent = answer;

    answerSources.replaceChildren();
    [...new Set(sources)].slice(0, 3).forEach((source) => {
        const item = document.createElement("li");
        item.textContent = source;
        answerSources.append(item);
    });
    answerSources.hidden = !answerSources.childElementCount;
}


// Ask one question using the checked PDFs.
async function askQuestion(event) {
    event.preventDefault();
    answerSources.replaceChildren();
    answerSources.hidden = true;
    const files = [...list.querySelectorAll("input:checked")].map((input) => Number(input.value));
    if (!files.length) {
        showAlert("Select at least one PDF.", ERROR_MESSAGE);
        return;
    }

    askButton.disabled = true;
    renderAnswer("Reading your PDFs...", [], true);
    try {
        const response = await fetch("/api/v1/qa/ask", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json", ...csrfHeaders() },
            body: JSON.stringify({ query: questionInput.value.trim(), files }),
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(getErrorMessage(response, data));
        renderAnswer(data.answer, data.sources || []);
    } catch (error) {
        renderAnswer("I couldn't answer that question. Please try again.");
        showAlert(error.message || "Could not answer the question.", ERROR_MESSAGE);
    } finally {
        askButton.disabled = false;
    }
}


// Connect the workspace after session restoration.
document.addEventListener("app-shell-ready", (event) => {
    if (event.detail?.user) loadFiles();
    else {
        list.replaceChildren();
        answerContent.textContent = "Select a PDF, then ask a question.";
        answerContent.classList.add("empty");
        answerSources.replaceChildren();
        answerSources.hidden = true;
    }
});
uploadButton.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", uploadFile);
questionForm.addEventListener("submit", askQuestion);
questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) questionForm.requestSubmit();
});
if (getActiveShellUser()) loadFiles();
