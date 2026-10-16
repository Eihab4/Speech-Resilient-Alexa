import { signIn, signOut, signUp, whoAmI } from "./account.js";
import { PersonLabel } from "./messages.js";
import { forgetSession, loadSession, saveSession } from "./session.js";

// The sign-in and create-account forms, and who is signed in. The page tells this what to do around it:
// greet the person once they are in, and clear itself when they leave.
export function setupSignIn({ onSignedIn, onSignedOut }) {
  const account = document.querySelector("#account");
  const signInForm = document.querySelector("#sign-in-form");
  const signUpForm = document.querySelector("#sign-up-form");
  const accountError = document.querySelector("#account-error");
  const signedIn = document.querySelector("#signed-in");
  const personName = document.querySelector("#person-name");
  let session = loadSession();

  function show() {
    account.hidden = Boolean(session);
    signedIn.hidden = !session;
    personName.textContent = session ? PersonLabel.hello(session.name) : "";
  }

  function showForm(form) {
    signInForm.hidden = form !== signInForm;
    signUpForm.hidden = form !== signUpForm;
    accountError.textContent = "";
    form.querySelector("input").focus();
  }

  async function enter(start, form) {
    accountError.textContent = "";
    try {
      session = saveSession(await start());
    } catch (error) {
      accountError.textContent = error.message;
      return;
    }
    form.reset();
    show();
    onSignedIn(session);
  }

  function leave() {
    forgetSession();
    session = null;
    onSignedOut();
    show();
    showForm(signInForm);
  }

  const field = (form, name) => form.querySelector(`[id$="-${name}"]`).value;

  signInForm.addEventListener("submit", (event) => {
    event.preventDefault();
    enter(() => signIn(field(signInForm, "username").trim(), field(signInForm, "password")), signInForm);
  });

  signUpForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const username = field(signUpForm, "username").trim();
    enter(() => signUp(username, field(signUpForm, "name").trim(), field(signUpForm, "password")), signUpForm);
  });

  document.querySelector("#show-sign-up").addEventListener("click", () => showForm(signUpForm));
  document.querySelector("#show-sign-in").addEventListener("click", () => showForm(signInForm));

  document.querySelector("#sign-out").addEventListener("click", () => {
    const token = session?.token;
    leave();
    if (token) signOut(token).catch(() => {});
  });

  // A kept session may have been signed out elsewhere; check it, and keep the name up to date.
  async function checkSession() {
    if (!session) return;
    try {
      const me = await whoAmI(session.token);
      session = saveSession({ ...session, name: me.name });
      show();
    } catch (error) {
      if (error.status === 401) leave();
    }
  }

  show();
  checkSession();

  return {
    get session() {
      return session;
    },
  };
}
