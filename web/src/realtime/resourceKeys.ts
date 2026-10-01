/* Copyright 2026 Aaron John Schlosser, PhD. */
// The closed list of server data resources a page can follow for invalidation. It must equal
// `DATA_RESOURCES` in api/app/realtime/resources.py (tests/test_realtime_resources.py reads this file). Add a key here and there before using it.
export const DATA_RESOURCES = [
  "users",
  "roles",
  "vector_collections",
  "metadata_exemplars",
  "response_library",
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
