

const APP_ROUTES_ROOT_PATH = "http://localhost:8000/api/v1";

export const AUTH_ROUTES_PATH = `${APP_ROUTES_ROOT_PATH}/auth`;
export const DATA_ROUTES_PATH = `${APP_ROUTES_ROOT_PATH}/data`;

export const BAD_REQUEST_ERROR = 400;
export const INTERNAL_SERVER_ERROR = 500;

export const SUCCESS_MESSAGE = "success";
export const ERROR_MESSAGE = "error";

export const WELCOME_MESSAGE_CONTAINER = document.querySelector('.welcome-message');
export const ALERTS_CONTAINER = document.querySelector('.alerts');

export const START_FORM = document.querySelector(".start-form");
export const LOGIN_FORM = document.querySelector(".login-form");
export const REGISTER_FORM = document.querySelector(".register-form");
export const APP_SHELL = document.querySelector(".app-shell");

export const USER_PROFILE_LOGO = document.querySelector(".user-profile .logo");
export const LOGIN_BUTTON = document.getElementById("login");
export const LOGOUT_BUTTON = document.getElementById("logout");
