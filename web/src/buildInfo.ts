// Copyright 2026 Aaron John Schlosser, PhD.
export const APP_VERSION = __APP_VERSION__;
export const APP_GIT_COMMIT = __APP_GIT_COMMIT__;

export function appVersionLabel(version = APP_VERSION, commit = APP_GIT_COMMIT): string {
  const cleanVersion = String(version || "").trim() || APP_VERSION;
  const cleanCommit = String(commit || "").trim();
  return cleanCommit ? `${cleanVersion} (${cleanCommit})` : cleanVersion;
}
