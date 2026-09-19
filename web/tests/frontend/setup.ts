import { afterEach, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

class TestWorker {
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  constructor(..._args: unknown[]) {}
  postMessage(..._args: unknown[]) {}
  terminate() {}
  addEventListener(..._args: unknown[]) {}
  removeEventListener(..._args: unknown[]) {}
  dispatchEvent(_event: Event) { return true; }
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
