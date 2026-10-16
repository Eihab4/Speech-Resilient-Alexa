import { ErrorMessage } from "./messages.js";

// A call to the server's own routes. Throws with the server's message when it refuses.
export async function send(url, init) {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.error ?? ErrorMessage.setupFailed(response.status));
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

export const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const signedIn = (token, init = {}) => ({
  ...init,
  headers: { ...init.headers, Authorization: `Bearer ${token}` },
});
