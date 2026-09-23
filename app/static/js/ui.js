import {
    ACTIVE_CLASS,
} from "./constants.js";


const modalToggles = [
    {
        button: document.querySelector(".user-profile-toggle"),
        modal: document.querySelector(".user-profile-modal"),
    },
    {
        button: document.querySelector(".chats-toggle"),
        modal: document.querySelector(".chats-modal"),
    },
    {
        button: document.querySelector(".chat-settings-toggle"),
        modal: document.querySelector(".chat-settings-modal"),
    },
];

const modals = modalToggles
    .map(({ modal }) => modal)
    .filter(Boolean);




/* Modal State */
function setButtonState(button, isActive) {
    if (!button) {
        return;
    }

    button.classList.toggle(ACTIVE_CLASS, isActive);
    button.setAttribute("aria-expanded", String(isActive));
}




function closeModal(modalToClose) {
    if (!modalToClose) {
        return;
    }

    modalToClose.classList.remove(ACTIVE_CLASS);

    const modalEntry = modalToggles.find(({ modal }) => modal === modalToClose);
    setButtonState(modalEntry?.button, false);
}




function closeOtherModals(activeModal) {
    modals.forEach((modal) => {
        if (modal !== activeModal) {
            closeModal(modal);
        }
    });
}




function toggleModal(modal, button) {
    if (!modal) {
        return;
    }

    const shouldOpen = !modal.classList.contains(ACTIVE_CLASS);
    closeOtherModals(modal);
    modal.classList.toggle(ACTIVE_CLASS, shouldOpen);
    setButtonState(button, shouldOpen);
}




function closeAllModals() {
    modals.forEach(closeModal);
}




/* Wire Modal Controls */
function bindModalToggles() {
    modalToggles.forEach(({ button, modal }) => {
        button?.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleModal(modal, button);
        });
    });
}




function bindModalCloseButtons() {
    document.querySelectorAll(".app-modal .modal-close").forEach((button) => {
        button.addEventListener("click", () => {
            closeModal(button.closest(".app-modal"));
        });
    });
}




function bindGlobalCloseEvents() {
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeAllModals();
        }
    });

    document.addEventListener("click", (event) => {
        const clickedModal = event.target.closest(".app-modal");
        const clickedToggle = event.target.closest(".rail-button, .header-icon-button");

        if (!clickedModal && !clickedToggle) {
            closeAllModals();
        }
    });
}




function bindUiEvents() {
    bindModalToggles();
    bindModalCloseButtons();
    bindGlobalCloseEvents();
}

bindUiEvents();
