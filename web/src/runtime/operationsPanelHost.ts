// Copyright 2026 Aaron John Schlosser, PhD.
// Mounts the Vue Operations panel into a placeholder that the legacy Home dashboard renders.
// The dashboard replaces its HTML wholesale, so each mount first tears down the previous one.
import { createApp, type App } from "vue";
import { getActivePinia } from "pinia";
import OperationsPanel from "../components/OperationsPanel.vue";
import type { OperationsBridge } from "../domain/operationsPanel";

let app: App | null = null;

export function unmountOperationsPanel(): void {
  app?.unmount();
  app = null;
}

export function mountOperationsPanel(host: Element | null, bridge: OperationsBridge): void {
  unmountOperationsPanel();
  if (!host) return;
  const next = createApp(OperationsPanel, { bridge });
  const pinia = getActivePinia();
  if (pinia) next.use(pinia);
  next.mount(host);
  app = next;
}
