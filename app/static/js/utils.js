import {
    ALERTS_CONTAINER,
    APP_SHELL,
    BAD_REQUEST_ERROR,
    INTERNAL_SERVER_ERROR,
    LOGIN_BUTTON,
    LOGIN_FORM,
    LOGOUT_BUTTON,
    REGISTER_FORM,
    SUCCESS_MESSAGE,
    WELCOME_MESSAGE_CONTAINER,
} from "./constants.js";

let alertTimeoutId;
let activeShellUser = null;


/*
    auth backdrop state
*/
function setAuthBackdrop(isActive) {
    document.body.classList.toggle("auth-form-active", isActive);

    if (isActive) {
        document.querySelectorAll(".app-modal.active, .rail-button.active, .header-icon-button.active")
            .forEach((element) => {
                element.classList.remove("active");

                if (element.matches("button")) {
                    element.setAttribute("aria-expanded", "false");
                }
            });
    }
}


function notifyAppShellReady(user = null) {
    activeShellUser = user;

    document.dispatchEvent(
        new CustomEvent("app-shell-ready", {
            detail: {
                user,
            },
        })
    );
}


export function getActiveShellUser() {
    return activeShellUser;
}




/*
    show / clear messages / alerts
*/


export function showMessage(target, message, type = "error") {
    if (!target) {
        return;
    }

    target.textContent = message;
    target.className = `${target.classList[0]} ${type} active`;
}


export function clearMessage(target) {
    if (!target) {
        return;
    }

    target.textContent = "";
    target.classList.remove("active", "error", "success", "info");
}


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



/*
    Parse Backend responses
*/
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


export async function parseJsonResponse(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}


/*
    UI State
*/

export function setUserProfile(user = null) {
    const userName = user?.user_name || "Visitor";

    showMessage(WELCOME_MESSAGE_CONTAINER, `Welcome ${userName}`, SUCCESS_MESSAGE);

    if (LOGIN_BUTTON) {
        LOGIN_BUTTON.hidden = Boolean(user);
    }

    if (LOGOUT_BUTTON) {
        LOGOUT_BUTTON.hidden = !user;
    }
}


export function activateAppShell(user = null) {
    setAuthBackdrop(false);
    REGISTER_FORM.classList.remove("active");
    LOGIN_FORM.classList.remove("active");

    APP_SHELL?.classList.add("active");

    setUserProfile(user);
    notifyAppShellReady(user);
}


export function activateGuestShell() {
    setAuthBackdrop(false);
    REGISTER_FORM.classList.remove("active");
    LOGIN_FORM.classList.remove("active");
    APP_SHELL?.classList.add("active");
    setUserProfile(null);
    notifyAppShellReady(null);
}


export function activateLoginForm() {
    setAuthBackdrop(true);
    REGISTER_FORM.classList.remove("active");
    APP_SHELL?.classList.add("active");
    LOGIN_FORM.classList.add("active");
}


export function activateRegisterForm() {
    setAuthBackdrop(true);
    LOGIN_FORM.classList.remove("active");
    APP_SHELL?.classList.add("active");
    REGISTER_FORM.classList.add("active");
}
