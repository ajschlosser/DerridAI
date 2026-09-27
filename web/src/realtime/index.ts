/* Copyright 2026 Aaron John Schlosser, PhD. */
// Process-wide realtime client and its reactive status for the app shell.
import { ref } from "vue";
import { RealtimeClient, type RealtimeStatus } from "./client";

/** Global job-feed poll interval used only while the socket is unavailable (docs/REALTIME.md). */
export const FALLBACK_POLL_MS = 25_000;
/** A single resource a visible view is watching, while the socket is unavailable. */
export const VIEW_FALLBACK_POLL_MS = 5_000;
/** Cadence a watching view used before realtime existed; kept only while realtime is not started. */
export const LEGACY_VIEW_POLL_MS = 1_400;

export const realtimeStatus = ref<RealtimeStatus>("idle");
export const realtimeFallback = ref(false);

export const realtime = new RealtimeClient({
  onAuthExpired: () => window.dispatchEvent(new CustomEvent("derridai-auth-expired")),
  onPermissionsChanged: () => window.dispatchEvent(new CustomEvent("derridai:permissions-changed")),
});

realtime.onStatus((status, fallback) => {
  realtimeStatus.value = status;
  realtimeFallback.value = fallback;
});

export type { RealtimeStatus };
