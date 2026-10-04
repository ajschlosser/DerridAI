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

/**
 * Query parameters that must never survive into a copied/canonical workspace URL.
 *
 * Most shareable state is encoded by the view-owned URL codec. Unknown query
 * parameters are otherwise preserved so route-native extensions remain forward
 * compatible. This policy removes the classes of data that are explicitly
 * transient or credential-like without turning the router into a second list of
 * every safe workspace parameter.
 */
const NON_SHAREABLE_QUERY_KEY =
  /(^|[-_])(api[-_]?key|password|passphrase|token|secret|credential|authorization|prompt|instructions|draft|console)([-_]|$)/i;

export function isShareableQueryKey(key: string): boolean {
  return !NON_SHAREABLE_QUERY_KEY.test(String(key || ""));
}

export function sanitizeShareableQuery<T>(query: Record<string, T>): Record<string, T> {
  return Object.fromEntries(
    Object.entries(query).filter(([key]) => isShareableQueryKey(key)),
  ) as Record<string, T>;
}

export function stripNonShareableSearchParams(params: URLSearchParams): void {
  for (const key of [...params.keys()]) {
    if (!isShareableQueryKey(key)) params.delete(key);
  }
}
