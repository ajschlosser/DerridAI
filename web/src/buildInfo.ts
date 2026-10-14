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
