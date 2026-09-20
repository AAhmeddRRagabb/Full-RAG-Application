/*
    Authentication Logic
*/

import {
    AUTH_ROUTES_PATH,

    SUCCESS_MESSAGE,
    ERROR_MESSAGE,

    LOGIN_BUTTON,
    LOGOUT_BUTTON,

    LOGIN_FORM,
    REGISTER_FORM,
} from "./constants.js";

import {
    activateAppShell,
    activateLoginForm,
    activateRegisterForm,
    activateStartForm,

    showMessage,
    clearMessage,
    showAlert,

    getErrorMessage,
    parseJsonResponse,
} from "./utils.js";

let csrfToken = null;

const visitorBtn = document.querySelector(".start-form button.visitor");
const subscriberBtn = document.querySelector(".start-form button.subscriber");
const closeFormBtns = document.querySelectorAll(".close-form");

const loginMessage = LOGIN_FORM.querySelector(".form-message");
const registerMessage = REGISTER_FORM.querySelector(".form-message");

const loginSubmitBtn = LOGIN_FORM.querySelector("#submitBtn");
const registerSubmitBtn = REGISTER_FORM.querySelector("#submitBtn");

const userEmailLoginIP = LOGIN_FORM.querySelector("#userEmail");
const userPassLoginIP = LOGIN_FORM.querySelector("#userPassword");

const userEmailIP = REGISTER_FORM.querySelector("#userEmail");
const userNameIP = REGISTER_FORM.querySelector("#userName");
const userPassIP = REGISTER_FORM.querySelector("#userPassword");
const confirmPassIP = REGISTER_FORM.querySelector("#confirmPassword");

const haveEmailBtn = REGISTER_FORM.querySelector(".have-email");
const haveNoEmailBtn = LOGIN_FORM.querySelector(".have-no-email");




/* Csrf Token Handlers */
function updateCsrfToken(token) {
    csrfToken = token || null;
}

async function refreshCsrfToken() {
    const response = await fetch(
        `${AUTH_ROUTES_PATH}/csrf`,
        {
            credentials: "include",
        }
    );

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        throw new Error(getErrorMessage(response, data));
    }

    updateCsrfToken(data.csrf_token);
    return csrfToken;
}


/* Restore user session */
async function restoreAuthentication() {
    let userResponse;

    try {
        userResponse = await fetch(
            `${AUTH_ROUTES_PATH}/me`,
            {
                credentials: "include",
            }
        );
    } catch {
        activateStartForm();
        return;
    }

    if (!userResponse.ok) {
        activateStartForm();
        return;
    }

    try {
        await refreshCsrfToken();
    } catch {
        activateStartForm();
        return;
    }

    const user = await parseJsonResponse(userResponse);
    activateAppShell(user);
}




/* login */
async function loginUser(event) {
    event.preventDefault();
    clearMessage(loginMessage);

    let response;
    try {
        showMessage(loginMessage, "Verifying credentials...", "info");
        response = await fetch(
            `${AUTH_ROUTES_PATH}/login`,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: userEmailLoginIP.value,
                    password: userPassLoginIP.value,
                }),
            }
        );
    } catch {
        showAlert("Could not reach the server. Please try again.", ERROR_MESSAGE);
        return;
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return;
    }

    updateCsrfToken(data.csrf_token);
    showAlert(data.message || `Welcome ${data.user.user_name}.`, SUCCESS_MESSAGE);
    activateAppShell(data.user);
}


/* Registration */
async function registerUser(event) {
    event.preventDefault();
    clearMessage(registerMessage);

    if (userPassIP.value !== confirmPassIP.value) {
        showAlert("Passwords do not match.", ERROR_MESSAGE);
        return;
    }

    let response;
    try {
        showMessage(registerMessage, "Creating your account...", "info");
        response = await fetch(
            `${AUTH_ROUTES_PATH}/register`,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    user_name: userNameIP.value,
                    email: userEmailIP.value,
                    password: userPassIP.value,
                }),
            }
        );
    } catch {
        showAlert("Could not reach the server. Please try again.", ERROR_MESSAGE);
        return;
    }

    const data = await parseJsonResponse(response);

    if (!response.ok) {
        showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
        return;
    }

    updateCsrfToken(data.csrf_token);
    showAlert(data.message || "Account created successfully.", SUCCESS_MESSAGE);
    activateAppShell(data.user);
}




/* logout */
async function logoutUser() {
    try {
        if (!csrfToken) {
            await refreshCsrfToken();
        }

        const response = await fetch(
            `${AUTH_ROUTES_PATH}/logout`,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "X-CSRF-Token": csrfToken,
                },
            }
        );

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            showAlert(getErrorMessage(response, data), ERROR_MESSAGE);
            return;
        }

        updateCsrfToken(null);
        showAlert(data.message || "Logged out successfully.", SUCCESS_MESSAGE);
        activateStartForm();
    } catch {
        showAlert("Could not log out. Please try again.", ERROR_MESSAGE);
    }
}


/* Wire Logic */
function bindAuthEvents() {
    visitorBtn?.addEventListener("click", () => {
        updateCsrfToken(null);
        activateAppShell();
        showAlert("Visitor session is ready.", SUCCESS_MESSAGE);
    });

    subscriberBtn?.addEventListener("click", activateLoginForm);
    LOGIN_BUTTON.addEventListener("click", activateLoginForm);
    LOGOUT_BUTTON.addEventListener("click", logoutUser);
    loginSubmitBtn.addEventListener("click", loginUser);
    registerSubmitBtn.addEventListener("click", registerUser);

    haveNoEmailBtn.addEventListener("click", () => {
        clearMessage(loginMessage);
        activateRegisterForm();
    });

    haveEmailBtn.addEventListener("click", () => {
        clearMessage(registerMessage);
        activateLoginForm();
    });

    closeFormBtns.forEach((button) => {
        button.addEventListener("click", activateStartForm);
    });
}

bindAuthEvents();
await restoreAuthentication();
