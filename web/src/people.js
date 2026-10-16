import { HELPERS_URL, PROFILE_URL } from "./config.js";
import { json, send, signedIn } from "./http.js";

// Every call is for the signed-in account; the server knows who from the token.

export const loadProfile = (token) => send(PROFILE_URL, signedIn(token));

export const saveProfile = (token, name, homeAddress) =>
  send(PROFILE_URL, signedIn(token, json("PUT", { name, home_address: homeAddress })));

export const listHelpers = (token) => send(HELPERS_URL, signedIn(token));

export const addHelper = (token, name) => send(HELPERS_URL, signedIn(token, json("POST", { name })));

export const removeHelper = (token, helperId) =>
  send(`${HELPERS_URL}/${encodeURIComponent(helperId)}`, signedIn(token, { method: "DELETE" }));
