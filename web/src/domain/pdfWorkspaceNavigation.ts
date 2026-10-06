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
 * Corpus Builder and Source Explorer share one legacy runtime view, but they do
 * not share route-state semantics. In particular, `record` is a stable Record
 * id in Builder and a browser-local record index in Explorer. Copying an entire
 * query string across the boundary makes one workspace interpret the other's
 * state and is a common source of "jumpy" navigation.
 *
 * Keep these allow-lists deliberately small. Add a key only when both its
 * owner and restoration semantics are clear.
 */
import type { LocationQueryRaw } from "vue-router";

const BUILDER_QUERY_KEYS = new Set(["workspace", "build", "queue", "record", "sources"]);
const EXPLORER_QUERY_KEYS = new Set(["file", "record", "pdfpage", "ts"]);

export type PdfWorkspaceDestination = "builder" | "explorer";

export function queryForPdfWorkspace(
  destination: PdfWorkspaceDestination,
  query: Record<string, unknown>,
): LocationQueryRaw {
  const allowed = destination === "builder" ? BUILDER_QUERY_KEYS : EXPLORER_QUERY_KEYS;
  return Object.fromEntries(
    Object.entries(query).filter(([key, value]) => allowed.has(key) && value !== undefined),
  ) as LocationQueryRaw;
}

/**
 * Sanitize a query while crossing the Builder/Explorer boundary. `record`
 * intentionally belongs to both routes but means different things, so it must
 * never cross even though each workspace may preserve it within its own URL.
 */
export function queryForPdfWorkspaceTransition(
  source: PdfWorkspaceDestination,
  destination: PdfWorkspaceDestination,
  query: Record<string, unknown>,
): LocationQueryRaw {
  if (source === destination) return queryForPdfWorkspace(destination, query);
  const crossing = { ...query };
  delete crossing.record;
  return queryForPdfWorkspace(destination, crossing);
}
