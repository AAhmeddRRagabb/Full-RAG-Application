import {
    ALERTS_CONTAINER,
    APP_SHELL,
    BAD_REQUEST_ERROR,
    INTERNAL_SERVER_ERROR,
    LOGIN_BUTTON,
    LOGIN_FORM,
    LOGOUT_BUTTON,
    REGISTER_FORM,
    START_FORM,
    SUCCESS_MESSAGE,
    USER_PROFILE_LOGO,
    WELCOME_MESSAGE_CONTAINER,
} from "./constants.js";

let alertTimeoutId;




// Show an inline status message in a target element.
export function showMessage(target, message, type = "error") {
    if (!target) {
        return;
    }

    target.textContent = message;
    target.className = `${target.classList[0]} ${type} active`;
}




// Clear all inline status styles from a target element.
export function clearMessage(target) {
    if (!target) {
        return;
    }

    target.textContent = "";
    target.classList.remove("active", "error", "success", "info");
}




// Show a timed global alert.
export function showAlert(message, type = "error") {
    if (!ALERTS_CONTAINER) {
        return;
    }

    clearTimeout(alertTimeoutId);
    ALERTS_CONTAINER.innerHTML = "";

    const alert = document.createElement("p");
    alert.className = `alert ${type}`;
    alert.textContent = message;

    ALERTS_CONTAINER.appendChild(alert);
    ALERTS_CONTAINER.classList.add("active");

    alertTimeoutId = setTimeout(() => {
        ALERTS_CONTAINER.classList.remove("active");
        ALERTS_CONTAINER.innerHTML = "";
    }, 3000);
}




// Extract a usable error string from API responses.
export function getErrorMessage(response, data = {}) {
    if (response.status === BAD_REQUEST_ERROR && data.detail) {
        return data.detail;
    }

    if (response.status === BAD_REQUEST_ERROR && data.message) {
        return data.message;
    }

    if (response.status === INTERNAL_SERVER_ERROR) {
        return data.detail || "Internal Server Error";
    }

    return data.detail || data.message || "Something went wrong. Please try again.";
}




// Safely parse JSON responses that may have an empty body.
export async function parseJsonResponse(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}




// Update the profile controls for a guest or authenticated user.
export function setUserProfile(user = null) {
    const userName = user?.user_name || "Visitor";
    const userInitial = userName.trim().charAt(0).toUpperCase() || "V";

    showMessage(WELCOME_MESSAGE_CONTAINER, `Welcome ${userName}`, SUCCESS_MESSAGE);

    if (USER_PROFILE_LOGO) {
        USER_PROFILE_LOGO.textContent = userInitial;
    }

    if (LOGIN_BUTTON) {
        LOGIN_BUTTON.hidden = Boolean(user);
    }

    if (LOGOUT_BUTTON) {
        LOGOUT_BUTTON.hidden = !user;
    }
}




// Show the main app workspace.
export function activateAppShell(user = null) {
    START_FORM.classList.remove("active");
    REGISTER_FORM.classList.remove("active");
    LOGIN_FORM.classList.remove("active");
    APP_SHELL.classList.add("active");

    setUserProfile(user);
}




// Show the first visitor/subscriber choice screen.
export function activateStartForm() {
    REGISTER_FORM.classList.remove("active");
    LOGIN_FORM.classList.remove("active");
    APP_SHELL.classList.remove("active");
    START_FORM.classList.add("active");
}




// Show the login form.
export function activateLoginForm() {
    REGISTER_FORM.classList.remove("active");
    START_FORM.classList.remove("active");
    APP_SHELL.classList.remove("active");
    LOGIN_FORM.classList.add("active");
}




// Show the registration form.
export function activateRegisterForm() {
    LOGIN_FORM.classList.remove("active");
    START_FORM.classList.remove("active");
    APP_SHELL.classList.remove("active");
    REGISTER_FORM.classList.add("active");
}
