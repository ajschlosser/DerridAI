/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { afterEach, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

function ensureWebStorage() {
  if (typeof globalThis.localStorage?.clear === "function") return;
  const memory = new Map<string, string>();
  const storage = {
    getItem(key: string) {
      return memory.has(key) ? memory.get(key)! : null;
    },
    setItem(key: string, value: string) {
      memory.set(String(key), String(value));
    },
    removeItem(key: string) {
      memory.delete(String(key));
    },
    clear() {
      memory.clear();
    },
    key(index: number) {
      return [...memory.keys()][index] ?? null;
    },
    get length() {
      return memory.size;
    },
  } as Storage;
  Object.defineProperty(globalThis, "localStorage", { value: storage, configurable: true });
}
ensureWebStorage();

class TestWorker {
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  constructor(..._args: unknown[]) {}
  postMessage(..._args: unknown[]) {}
  terminate() {}
  addEventListener(..._args: unknown[]) {}
  removeEventListener(..._args: unknown[]) {}
  dispatchEvent(_event: Event) {
    return true;
  }
}

// pdfjs installs its worker wrapper while DerridAI's runtime module is imported.
// Component tests do not render PDFs, but the browser Worker global must still
// exist during module evaluation.
if (!("Worker" in globalThis)) {
  Object.defineProperty(globalThis, "Worker", { value: TestWorker, configurable: true });
}

beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
  document.documentElement.lang = "en-US";
  document.documentElement.dir = "ltr";
});

afterEach(() => {
  document.body.innerHTML = "";
});
