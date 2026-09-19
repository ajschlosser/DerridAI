import { afterEach, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
  document.documentElement.lang = "en-US";
  document.documentElement.dir = "ltr";
});

afterEach(() => {
  document.body.innerHTML = "";
});
