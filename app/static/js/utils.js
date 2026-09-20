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


/*
    auth backdrop state
*/
function setAuthBackdrop(isActive) {
    document.body.classList.toggle("auth-form-active", isActive);
}


function notifyAppShellReady(user = null) {
    document.dispatchEvent(
        new CustomEvent("app-shell-ready", {
            detail: {
                user,
            },
        })
    );
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
    control UI
*/

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


export function activateAppShell(user = null) {
    setAuthBackdrop(false);
    START_FORM?.classList.remove("active");
    REGISTER_FORM.classList.remove("active");
    LOGIN_FORM.classList.remove("active");

    APP_SHELL?.classList.add("active");

    setUserProfile(user);
    notifyAppShellReady(user);
}


export function activateStartForm() {
    setAuthBackdrop(Boolean(START_FORM));
    REGISTER_FORM.classList.remove("active");
    LOGIN_FORM.classList.remove("active");
    APP_SHELL?.classList.add("active");
    START_FORM?.classList.add("active");
    setUserProfile(null);
}


export function activateLoginForm() {
    setAuthBackdrop(true);
    REGISTER_FORM.classList.remove("active");
    START_FORM?.classList.remove("active");
    APP_SHELL?.classList.add("active");
    LOGIN_FORM.classList.add("active");
}


export function activateRegisterForm() {
    setAuthBackdrop(true);
    LOGIN_FORM.classList.remove("active");
    START_FORM?.classList.remove("active");
    APP_SHELL?.classList.add("active");
    REGISTER_FORM.classList.add("active");
}
