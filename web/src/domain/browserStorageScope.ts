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

import { sessionState } from "../state/workspaceState";

export type BrowserStorageUser =
  | { id?: string | number | null; role?: string | null }
  | null
  | undefined;

export function browserStorageAccountScope(user: BrowserStorageUser): string {
  if (user?.id == null || String(user.id) === "") return "";
  return `${String(user.role || "user")}:${String(user.id)}`;
}

/**
 * Names user-authored browser-local state by the authenticated account.
 *
 * Pure display preferences can intentionally keep their global keys. Queries,
 * drafts, corpus guidance, saved filters, and similar user-authored content
 * should use this helper so another account in the same browser profile cannot
 * inherit them.
 */
export function accountScopedBrowserStorageKey(
  baseKey: string,
  user: BrowserStorageUser,
): string {
  const scope = browserStorageAccountScope(user);
  return scope ? `${baseKey}.${scope}` : baseKey;
}

/** Account-scoped key using the runtime's currently bound authenticated user. */
export function currentAccountScopedBrowserStorageKey(baseKey: string): string {
  return accountScopedBrowserStorageKey(baseKey, sessionState.userContext);
}
