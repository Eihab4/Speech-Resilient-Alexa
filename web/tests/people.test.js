import { beforeEach, expect, test, vi } from "vitest";

import { HELPERS_URL, PROFILE_URL } from "../src/config.js";
import { addHelper, listHelpers, loadProfile, removeHelper, saveProfile } from "../src/people.js";

let requests;
let respond;

beforeEach(() => {
  requests = [];
  respond = () => Response.json({ ok: true });
  globalThis.fetch = vi.fn(async (url, init = {}) => {
    requests.push({ url, method: init.method ?? "GET", body: init.body && JSON.parse(init.body) });
    return respond();
  });
});

test("the profile is read and saved for one person", async () => {
  await loadProfile("demo user");
  await saveProfile("demo user", "Ahmed", "12 Tahrir St");

  expect(requests).toEqual([
    { url: `${PROFILE_URL}?user_id=demo%20user`, method: "GET", body: undefined },
    { url: PROFILE_URL, method: "PUT", body: { user_id: "demo user", name: "Ahmed", home_address: "12 Tahrir St" } },
  ]);
});

test("helpers are listed, added and removed for one person", async () => {
  await listHelpers("u1");
  await addHelper("u1", "Sara");
  respond = () => new Response(null, { status: 204 });
  const removed = await removeHelper("u1", "h_1");

  expect(requests.map(({ url, method }) => `${method} ${url}`)).toEqual([
    `GET ${HELPERS_URL}?user_id=u1`,
    `POST ${HELPERS_URL}`,
    `DELETE ${HELPERS_URL}/h_1?user_id=u1`,
  ]);
  expect(requests[1].body).toEqual({ user_id: "u1", name: "Sara" });
  expect(removed).toBeNull();
});

test("the server's own error message is shown when it refuses", async () => {
  respond = () => Response.json({ error: "name is required" }, { status: 400 });

  await expect(addHelper("u1", "")).rejects.toThrow("name is required");
});

test("a refusal without a message still says what happened", async () => {
  respond = () => new Response("oops", { status: 502 });

  await expect(listHelpers("u1")).rejects.toThrow("502");
});
