
import {
    ACTIVE_CLASS
} from './constants.js'


/* Toggle Control Menu */
const controlAreaToggle = document.querySelector(".control-area_toggle");
const controlArea = document.querySelector(".control-area");
const mainArea = document.querySelector(".main-area");

controlAreaToggle.addEventListener('click', _ => {
    controlArea.classList.toggle(ACTIVE_CLASS);
    mainArea.classList.toggle("w75");
    controlAreaToggle.setAttribute(
        "aria-expanded",
        String(controlArea.classList.contains(ACTIVE_CLASS))
    );
})
