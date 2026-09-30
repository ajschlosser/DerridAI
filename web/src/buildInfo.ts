// Copyright 2026 Aaron John Schlosser, PhD.
export const APP_VERSION = __APP_VERSION__;
export const APP_CODENAME = __APP_CODENAME__;
export const APP_GIT_COMMIT = __APP_GIT_COMMIT__;
export const COPYRIGHT_YEAR = "2026";

export function appVersionLabel(
  version = APP_VERSION,
  commit = APP_GIT_COMMIT,
  codename = APP_CODENAME,
): string {
  const cleanVersion = String(version || "").trim() || APP_VERSION;
  const cleanCodename = String(codename || "").trim();
  const cleanCommit = String(commit || "").trim();
  const release = cleanCodename ? `${cleanVersion} - ${cleanCodename}` : cleanVersion;
  return cleanCommit ? `${release} (${cleanCommit})` : release;
}
