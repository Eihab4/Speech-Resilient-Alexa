import { HELPERS_REFRESH_MS } from "./config.js";
import { PeopleLabel } from "./messages.js";
import { addHelper, listHelpers, loadProfile, removeHelper, saveProfile } from "./people.js";
import { readPosition } from "./position.js";

// "People who help me": done once by the family, not by voice.
export function setupPeople(section, getUserId) {
  const profileForm = section.querySelector("#profile-form");
  const nameInput = section.querySelector("#profile-name");
  const addressInput = section.querySelector("#profile-address");
  const helperForm = section.querySelector("#helper-form");
  const helperName = section.querySelector("#helper-name");
  const list = section.querySelector("#helpers");
  const status = section.querySelector("#people-status");
  const locationButton = section.querySelector("#allow-location");
  let refresh = null;

  const show = (message) => (status.textContent = message);

  function button(label, onClick) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = "secondary";
    element.textContent = label;
    element.addEventListener("click", onClick);
    return element;
  }

  function helperItem(helper) {
    const item = document.createElement("li");
    item.className = "helper";
    const name = document.createElement("strong");
    name.textContent = helper.name;
    const state = document.createElement("span");
    state.className = helper.linked ? "linked" : "waiting";
    state.textContent = helper.linked ? PeopleLabel.LINKED : PeopleLabel.WAITING;
    item.append(name, state);

    if (helper.link) {
      const hint = document.createElement("small");
      hint.textContent = PeopleLabel.sendLink(helper.name);
      const link = document.createElement("a");
      link.href = helper.link;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = helper.link;
      const copy = button(PeopleLabel.COPY, async () => {
        await navigator.clipboard.writeText(helper.link);
        copy.textContent = PeopleLabel.COPIED;
      });
      item.append(hint, link, copy);
    }
    item.append(button(PeopleLabel.REMOVE, () => run(() => removeHelper(getUserId(), helper.id).then(refreshHelpers))));
    return item;
  }

  async function run(action) {
    try {
      await action();
    } catch (error) {
      show(error.message);
    }
  }

  async function refreshHelpers() {
    clearTimeout(refresh);
    const userId = getUserId();
    if (!userId || !section.open) return;
    const { telegram, helpers } = await listHelpers(userId);
    list.replaceChildren(...helpers.map(helperItem));
    show(telegram ? "" : PeopleLabel.NO_TELEGRAM);
    // Keep checking while someone hasn't opened their link, so "linked" shows up on its own.
    if (helpers.some((helper) => !helper.linked)) refresh = setTimeout(() => run(refreshHelpers), HELPERS_REFRESH_MS);
  }

  async function loadAll() {
    const userId = getUserId();
    if (!userId || !section.open) return;
    const profile = await loadProfile(userId);
    nameInput.value = profile.name ?? "";
    addressInput.value = profile.home_address ?? "";
    await refreshHelpers();
  }

  section.addEventListener("toggle", () => (section.open ? run(loadAll) : clearTimeout(refresh)));

  profileForm.addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      await saveProfile(getUserId(), nameInput.value.trim(), addressInput.value.trim());
      show(PeopleLabel.SAVED);
    });
  });

  helperForm.addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      await addHelper(getUserId(), helperName.value.trim());
      helperName.value = "";
      await refreshHelpers();
    });
  });

  // Asked here, once, so the browser's prompt never pops up during an emergency.
  locationButton.addEventListener("click", async () => {
    show((await readPosition()) ? PeopleLabel.LOCATION_ON : PeopleLabel.LOCATION_OFF);
  });

  return { reload: () => run(loadAll) };
}
