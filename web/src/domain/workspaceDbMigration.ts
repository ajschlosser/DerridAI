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

type WorkspaceDbLike = {
  getAll: (storeName: string) => Promise<unknown[]>;
  get: (storeName: string, key: IDBValidKey) => Promise<unknown>;
  put: (storeName: string, value: unknown) => Promise<void>;
  add: (storeName: string, value: unknown) => Promise<void>;
  count: (storeName: string) => Promise<number>;
  remove: (storeName: string, key: IDBValidKey) => Promise<void>;
  close: () => void;
  drop: () => Promise<void>;
};

const LEGACY_CLAIM_KEY = "__legacy_admin_workspace_claim__";
const MIGRATION_MARKER_KEY = "__legacy_admin_workspace_migration__";
const STORES = ["files", "prefs", "assets"] as const;

function accountKey(user: { id?: string | number; role?: string } | null): string {
  if (!user?.id) return "";
  return `${String(user.role || "user")}:${String(user.id)}`;
}

function ownerOf(record: unknown): string {
  return record && typeof record === "object" && "owner" in record
    ? String((record as { owner?: unknown }).owner || "")
    : "";
}

async function hasCurrentWorkspaceData(db: WorkspaceDbLike): Promise<boolean> {
  for (const store of STORES) {
    if ((await db.count(store)) > 0) return true;
  }
  return false;
}

/**
 * Claims and migrates the pre-account-scoped administrator database.
 *
 * The legacy default IndexedDB database had no owner identity, so migration can
 * only assign it to one administrator. An atomic add() claim prevents two
 * administrators opening the upgraded application at the same time from both
 * copying the same browser-local corpus and credentials. Failed copies are
 * resumable because the per-user destination records an in-progress marker and
 * IndexedDB puts are idempotent by key.
 */
export async function migrateLegacyAdminWorkspace({
  user,
  currentDb,
  legacyDb,
}: {
  user: { id?: string | number; role?: string } | null;
  currentDb: WorkspaceDbLike;
  legacyDb: WorkspaceDbLike;
}): Promise<boolean> {
  if (!user?.id || user.role !== "admin") return false;

  const owner = accountKey(user);
  const currentMarker = await currentDb.get("prefs", MIGRATION_MARKER_KEY);
  const resuming = ownerOf(currentMarker) === owner;

  if (!resuming && (await hasCurrentWorkspaceData(currentDb))) return false;

  let claim = await legacyDb.get("prefs", LEGACY_CLAIM_KEY);
  if (!claim) {
    try {
      await legacyDb.add("prefs", {
        key: LEGACY_CLAIM_KEY,
        owner,
        claimed_at: new Date().toISOString(),
      });
      claim = { owner };
    } catch {
      // Another tab/account may have claimed the legacy database between the
      // read and add. Re-read instead of treating a uniqueness error as failure.
      claim = await legacyDb.get("prefs", LEGACY_CLAIM_KEY);
    }
  }
  if (ownerOf(claim) !== owner) {
    legacyDb.close();
    return false;
  }

  const legacyCounts = await Promise.all(STORES.map((store) => legacyDb.count(store)));
  // The claim itself makes prefs non-empty. If there is no actual legacy
  // workspace data, release the claim and leave the empty database alone.
  const hasLegacyData =
    legacyCounts[0] > 0 ||
    legacyCounts[2] > 0 ||
    legacyCounts[1] > 1;
  if (!hasLegacyData) {
    await legacyDb.remove("prefs", LEGACY_CLAIM_KEY).catch(() => undefined);
    legacyDb.close();
    return false;
  }

  await currentDb.put("prefs", {
    key: MIGRATION_MARKER_KEY,
    owner,
    started_at: new Date().toISOString(),
  });

  for (const store of STORES) {
    const rows = await legacyDb.getAll(store);
    for (const row of rows) {
      if (
        store === "prefs" &&
        row &&
        typeof row === "object" &&
        "key" in row &&
        String((row as { key?: unknown }).key || "") === LEGACY_CLAIM_KEY
      )
        continue;
      await currentDb.put(store, row);
    }
  }

  // Remove the shared copy only after every destination write succeeded. If
  // deletion is blocked by another tab, keep both the source claim and the
  // destination marker so the same account can retry cleanup on its next
  // startup without blocking use of the already-complete migrated workspace.
  try {
    await legacyDb.drop();
    await currentDb.remove("prefs", MIGRATION_MARKER_KEY);
  } catch (error) {
    legacyDb.close();
    console.warn("Could not remove the claimed legacy admin workspace", error);
  }
  return true;
}

export const workspaceDbMigrationKeys = {
  legacyClaim: LEGACY_CLAIM_KEY,
  migrationMarker: MIGRATION_MARKER_KEY,
};
