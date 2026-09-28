/* Copyright 2026 Aaron John Schlosser, PhD. */
// Process-wide realtime client and its reactive status for the app shell.
import { ref } from "vue";
import { ApiError, apiRequest } from "../api/http";
import { RealtimeClient, type RealtimeStatus } from "./client";

/** Global job-feed poll interval used only while the socket is unavailable (docs/REALTIME.md). */
export const FALLBACK_POLL_MS = 25_000;
/** A single resource a visible view is watching, while the socket is unavailable. */
export const VIEW_FALLBACK_POLL_MS = 5_000;
/** Cadence a watching view used before realtime existed; kept only while realtime is not started. */
export const LEGACY_VIEW_POLL_MS = 1_400;

export const realtimeStatus = ref<RealtimeStatus>("idle");
export const realtimeFallback = ref(false);

/**
 * The socket said "unauthenticated". Confirm over REST before ending the session: a proxy that
 * does not forward cookies on WebSocket upgrades must degrade to polling, not log people out.
 */
async function confirmSessionExpired(): Promise<void> {
  try {
    await apiRequest("/api/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401)
      window.dispatchEvent(new CustomEvent("derridai-auth-expired"));
  }
}

export const realtime = new RealtimeClient({
  onAuthExpired: () => void confirmSessionExpired(),
  onPermissionsChanged: () => window.dispatchEvent(new CustomEvent("derridai:permissions-changed")),
});

realtime.onStatus((status, fallback) => {
  realtimeStatus.value = status;
  realtimeFallback.value = fallback;
});

export type { RealtimeStatus };
