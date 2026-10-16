// The signed-in account, kept by this browser so the person signs in once: typing is hard for the people this is
// for, so the family signs in for them and the page stays signed in until someone signs out.

const KEY = "speech-resilient-alexa.session";

export function loadSession(storage = globalThis.localStorage) {
  try {
    const session = JSON.parse(storage.getItem(KEY));
    return session?.token && session?.username ? session : null;
  } catch {
    return null;
  }
}

export function saveSession(session, storage = globalThis.localStorage) {
  try {
    storage.setItem(KEY, JSON.stringify(session));
  } catch {
    // Not kept (private window, blocked storage): the person signs in again next time.
  }
  return session;
}

export function forgetSession(storage = globalThis.localStorage) {
  try {
    storage.removeItem(KEY);
  } catch {
    // Nothing was kept.
  }
}
