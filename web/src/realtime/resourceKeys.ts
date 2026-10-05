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

// The closed list of server data resources a page can follow for invalidation. It must equal
// `DATA_RESOURCES` in api/app/realtime/resources.py (tests/test_realtime_resources.py reads this file). Add a key here and there before using it.
export const DATA_RESOURCES = [
  "users",
  "roles",
  "pipelines",
  "pipeline_runs",
  "pipeline_benchmarks",
  "vector_collections",
  "metadata_exemplars",
  "response_library",
  "research_threads",
  "corpus_records",
] as const;
export type DataResource = (typeof DATA_RESOURCES)[number];

/** Every server-state query key is `["data", <resource>, ...detail]`; see useDataQuery. */
export type DataQueryKey = readonly ["data", DataResource, ...unknown[]];

export function dataKey(resource: DataResource, ...detail: unknown[]): DataQueryKey {
  return ["data", resource, ...detail];
}

export function dataTopic(resource: DataResource): string {
  return `data:${resource}`;
}

export function isDataResource(value: unknown): value is DataResource {
  return typeof value === "string" && (DATA_RESOURCES as readonly string[]).includes(value);
}
