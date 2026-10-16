import { beforeEach, expect, test, vi } from "vitest";

import { ME_URL, SIGN_IN_URL, SIGN_OUT_URL, SIGN_UP_URL } from "../src/config.js";
import { signIn, signOut, signUp, whoAmI } from "../src/account.js";

let requests;
let respond;

beforeEach(() => {
  requests = [];
  respond = () => Response.json({ token: "t1", username: "rana_h", name: "Rana" });
  globalThis.fetch = vi.fn(async (url, init = {}) => {
    requests.push({ url, method: init.method ?? "GET", headers: init.headers ?? {}, body: init.body && JSON.parse(init.body) });
    return respond();
  });
});

test("creating an account sends the username, name and password", async () => {
  const session = await signUp("rana_h", "Rana", "secret1");

  expect(session).toEqual({ token: "t1", username: "rana_h", name: "Rana" });
  expect(requests[0]).toMatchObject({
    url: SIGN_UP_URL,
    method: "POST",
    body: { username: "rana_h", name: "Rana", password: "secret1" },
  });
});

test("signing in sends the username and password", async () => {
  await signIn("rana_h", "secret1");

  expect(requests[0]).toMatchObject({ url: SIGN_IN_URL, method: "POST", body: { username: "rana_h", password: "secret1" } });
});

test("signing out and asking who is signed in carry the token", async () => {
  await whoAmI("t1");
  respond = () => new Response(null, { status: 204 });
  await signOut("t1");

  expect(requests.map(({ url, method, headers }) => [url, method, headers.Authorization])).toEqual([
    [ME_URL, "GET", "Bearer t1"],
    [SIGN_OUT_URL, "POST", "Bearer t1"],
  ]);
});

test("a wrong password comes back as the server's message, with its status", async () => {
  respond = () => Response.json({ error: "Wrong username or password" }, { status: 401 });

  await expect(signIn("rana_h", "nope")).rejects.toMatchObject({ message: "Wrong username or password", status: 401 });
});
