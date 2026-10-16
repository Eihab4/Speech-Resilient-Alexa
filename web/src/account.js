import { ME_URL, SIGN_IN_URL, SIGN_OUT_URL, SIGN_UP_URL } from "./config.js";
import { json, send, signedIn } from "./http.js";

// Each answers { token, username, name }.
export const signUp = (username, name, password) => send(SIGN_UP_URL, json("POST", { username, name, password }));

export const signIn = (username, password) => send(SIGN_IN_URL, json("POST", { username, password }));

export const signOut = (token) => send(SIGN_OUT_URL, signedIn(token, { method: "POST" }));

export const whoAmI = (token) => send(ME_URL, signedIn(token));
