import { DATA_ROUTES_PATH, ERROR_MESSAGE, SUCCESS_MESSAGE } from "./constants.js";
import { csrfHeaders, getActiveShellUser, getErrorMessage, parseJsonResponse, showAlert } from "./utils.js";

const list = document.getElementById("filesList");
const fileInput = document.getElementById("fileInput");
const uploadButton = document.getElementById("uploadButton");
const questionForm = document.getElementById("questionForm");
const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");
const compareButton = document.getElementById("compareButton");
const compareDialog = document.getElementById("compareDialog");
const compareForm = document.getElementById("compareForm");
const compareFirst = document.getElementById("compareFirst");
const compareSecond = document.getElementById("compareSecond");
const answerContent = document.getElementById("answerContent");
const answerSources = document.getElementById("answerSources");
let availableFiles = [];


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
        availableFiles = data.user_files || [];
        renderFiles(availableFiles);
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
    compareButton.disabled = true;
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
        compareButton.disabled = false;
    }
}


// Open a file picker for a two-PDF comparison.
function openCompare() {
    if (!questionInput.value.trim()) {
        showAlert("Enter a comparison question first.", ERROR_MESSAGE);
        return;
    }
    if (availableFiles.length < 2) {
        showAlert("Upload at least two PDFs to compare.", ERROR_MESSAGE);
        return;
    }
    for (const select of [compareFirst, compareSecond]) {
        select.replaceChildren(new Option("Select a PDF", ""));
        availableFiles.forEach((file) => select.add(new Option(file.filename, file.file_id)));
        select.value = "";
    }
    compareDialog.showModal();
}


// Compare the two PDFs selected in the dialog.
async function compareFiles(event) {
    event.preventDefault();
    const query = questionInput.value.trim();
    const files = [Number(compareFirst.value), Number(compareSecond.value)];
    if (!query) {
        showAlert("Enter a comparison question first.", ERROR_MESSAGE);
        return;
    }
    if (files[0] === files[1]) {
        showAlert("Select two different PDFs.", ERROR_MESSAGE);
        return;
    }

    compareDialog.close();
    askButton.disabled = true;
    compareButton.disabled = true;
    renderAnswer("Comparing your PDFs...", [], true);
    try {
        const response = await fetch("/api/v1/qa/compare", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json", ...csrfHeaders() },
            body: JSON.stringify({ query, files }),
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(getErrorMessage(response, data));
        renderAnswer(data.answer, data.sources || []);
    } catch (error) {
        renderAnswer("I couldn't compare those PDFs. Please try again.");
        showAlert(error.message || "Could not compare PDFs.", ERROR_MESSAGE);
    } finally {
        askButton.disabled = false;
        compareButton.disabled = false;
    }
}


// Connect the workspace after session restoration.
document.addEventListener("app-shell-ready", (event) => {
    if (event.detail?.user) loadFiles();
    else {
        availableFiles = [];
        if (compareDialog.open) compareDialog.close();
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
compareButton.addEventListener("click", openCompare);
compareForm.addEventListener("submit", compareFiles);
document.getElementById("cancelCompare").addEventListener("click", () => compareDialog.close());
questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) questionForm.requestSubmit();
});
if (getActiveShellUser()) loadFiles();
