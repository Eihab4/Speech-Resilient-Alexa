import { beforeEach, expect, test, vi } from "vitest";

import { HELPERS_URL, PROFILE_URL } from "../src/config.js";
import { addHelper, listHelpers, loadProfile, removeHelper, saveProfile } from "../src/people.js";

let requests;
let respond;

beforeEach(() => {
  requests = [];
  respond = () => Response.json({ ok: true });
  globalThis.fetch = vi.fn(async (url, init = {}) => {
    requests.push({
      url,
      method: init.method ?? "GET",
      token: init.headers?.Authorization,
      body: init.body && JSON.parse(init.body),
    });
    return respond();
  });
});

test("the profile is read and saved for the signed-in account", async () => {
  await loadProfile("t1");
  await saveProfile("t1", "Rana", "12 Tahrir St");

  expect(requests).toEqual([
    { url: PROFILE_URL, method: "GET", token: "Bearer t1", body: undefined },
    { url: PROFILE_URL, method: "PUT", token: "Bearer t1", body: { name: "Rana", home_address: "12 Tahrir St" } },
  ]);
});

test("helpers are listed, added and removed for the signed-in account", async () => {
  await listHelpers("t1");
  await addHelper("t1", "Sara");
  respond = () => new Response(null, { status: 204 });
  const removed = await removeHelper("t1", "h_1");

  expect(requests.map(({ url, method, token }) => `${method} ${url} ${token}`)).toEqual([
    `GET ${HELPERS_URL} Bearer t1`,
    `POST ${HELPERS_URL} Bearer t1`,
    `DELETE ${HELPERS_URL}/h_1 Bearer t1`,
  ]);
  expect(requests[1].body).toEqual({ name: "Sara" });
  expect(removed).toBeNull();
});

test("the server's own error message is shown when it refuses", async () => {
  respond = () => Response.json({ error: "name is required" }, { status: 400 });

  await expect(addHelper("t1", "")).rejects.toThrow("name is required");
});

test("a refusal without a message still says what happened", async () => {
  respond = () => new Response("oops", { status: 502 });

  await expect(listHelpers("t1")).rejects.toThrow("502");
});
