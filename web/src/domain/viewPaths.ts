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

/** The path each view lives at, and the reverse map. */
export const viewPathMap: Record<string, string> = {
  home: "/",
  list: "/records",
  record: "/record",
  works: "/works",
  global: "/search",
  annotations: "/annotations",
  semanticmap: "/semantic-map",
  pdf: "/corpus-builder",
  compare: "/compare",
  vector: "/databases",
  rag: "/rag",
  faq: "/faq",
  responsecache: "/system-data/overview",
  providers: "/providers",
  schemas: "/schemas",
  config: "/settings/workspace",
};
export const pathViewMap: Record<string, string> = {
  ...Object.fromEntries(Object.entries(viewPathMap).map(([view, path]) => [path, view])),
  "/source-explorer": "pdf",
  "/pipelines": "responsecache",
};

export function viewFromPath(path: string): string | undefined {
  if (path.startsWith("/settings/")) return "config";
  if (path.startsWith("/system-data/")) return "responsecache";
  return pathViewMap[path];
}
