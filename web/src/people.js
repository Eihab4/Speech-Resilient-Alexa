import { HELPERS_URL, PROFILE_URL } from "./config.js";
import { ErrorMessage } from "./messages.js";

async function send(url, init) {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error ?? ErrorMessage.setupFailed(response.status));
  }
  return response.status === 204 ? null : response.json();
}

const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const forUser = (url, userId) => `${url}?user_id=${encodeURIComponent(userId)}`;

export const loadProfile = (userId) => send(forUser(PROFILE_URL, userId));

export const saveProfile = (userId, name, homeAddress) =>
  send(PROFILE_URL, json("PUT", { user_id: userId, name, home_address: homeAddress }));

export const listHelpers = (userId) => send(forUser(HELPERS_URL, userId));

export const addHelper = (userId, name) => send(HELPERS_URL, json("POST", { user_id: userId, name }));

export const removeHelper = (userId, helperId) =>
  send(forUser(`${HELPERS_URL}/${encodeURIComponent(helperId)}`, userId), { method: "DELETE" });
