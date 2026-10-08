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

import { describe, expect, it, vi } from "vitest";
import {
  migrateLegacyAdminWorkspace,
  workspaceDbMigrationKeys,
} from "../../src/domain/workspaceDbMigration";

class MemoryWorkspaceDb {
  stores = {
    files: new Map<IDBValidKey, unknown>(),
    prefs: new Map<IDBValidKey, unknown>(),
    assets: new Map<IDBValidKey, unknown>(),
  };
  dropped = false;
  closed = false;
  failDrop = false;

  private store(name: string) {
    return this.stores[name as keyof typeof this.stores];
  }

  private key(storeName: string, value: unknown): IDBValidKey {
    const record = value as { id?: IDBValidKey; key?: IDBValidKey };
    return storeName === "files" ? (record.id as IDBValidKey) : (record.key as IDBValidKey);
  }

  async getAll(storeName: string) {
    return [...this.store(storeName).values()];
  }

  async get(storeName: string, key: IDBValidKey) {
    return this.store(storeName).get(key);
  }

  async put(storeName: string, value: unknown) {
    this.store(storeName).set(this.key(storeName, value), structuredClone(value));
  }

  async add(storeName: string, value: unknown) {
    const key = this.key(storeName, value);
    if (this.store(storeName).has(key)) throw new DOMException("duplicate", "ConstraintError");
    this.store(storeName).set(key, structuredClone(value));
  }

  async count(storeName: string) {
    return this.store(storeName).size;
  }

  async remove(storeName: string, key: IDBValidKey) {
    this.store(storeName).delete(key);
  }

  close() {
    this.closed = true;
  }

  async drop() {
    if (this.failDrop) throw new Error("blocked");
    this.dropped = true;
    for (const store of Object.values(this.stores)) store.clear();
  }
}

describe("legacy administrator workspace migration", () => {
  it("migrates the unscoped admin workspace exactly once into the account database", async () => {
    const current = new MemoryWorkspaceDb();
    const legacy = new MemoryWorkspaceDb();
    await legacy.put("files", { id: "f1", name: "private.jsonl", records: [{ text: "secret" }] });
    await legacy.put("prefs", { key: "workspace", view: "list" });
    await legacy.put("assets", { key: "pdf", bytes: [1, 2, 3] });

    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 7, role: "admin" },
        currentDb: current,
        legacyDb: legacy,
      }),
    ).resolves.toBe(true);

    expect(await current.get("files", "f1")).toMatchObject({ name: "private.jsonl" });
    expect(await current.get("prefs", "workspace")).toMatchObject({ view: "list" });
    expect(await current.get("assets", "pdf")).toMatchObject({ bytes: [1, 2, 3] });
    expect(await current.get("prefs", workspaceDbMigrationKeys.legacyClaim)).toBeUndefined();
    expect(await current.get("prefs", workspaceDbMigrationKeys.migrationMarker)).toBeUndefined();
    expect(legacy.dropped).toBe(true);
  });

  it("never copies a claimed legacy workspace into a different administrator account", async () => {
    const first = new MemoryWorkspaceDb();
    const second = new MemoryWorkspaceDb();
    const legacy = new MemoryWorkspaceDb();
    await legacy.put("prefs", { key: "workspace", view: "record" });
    await legacy.put("prefs", {
      key: workspaceDbMigrationKeys.legacyClaim,
      owner: "admin:1",
    });

    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 2, role: "admin" },
        currentDb: second,
        legacyDb: legacy,
      }),
    ).resolves.toBe(false);

    expect(await second.count("prefs")).toBe(0);
    expect(legacy.dropped).toBe(false);

    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 1, role: "admin" },
        currentDb: first,
        legacyDb: legacy,
      }),
    ).resolves.toBe(true);
    expect(await first.get("prefs", "workspace")).toMatchObject({ view: "record" });
  });

  it("does not overwrite an account database that already owns workspace data", async () => {
    const current = new MemoryWorkspaceDb();
    const legacy = new MemoryWorkspaceDb();
    await current.put("prefs", { key: "workspace", view: "works" });
    await legacy.put("prefs", { key: "workspace", view: "record" });

    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 1, role: "admin" },
        currentDb: current,
        legacyDb: legacy,
      }),
    ).resolves.toBe(false);

    expect(await current.get("prefs", "workspace")).toMatchObject({ view: "works" });
    expect(await legacy.get("prefs", workspaceDbMigrationKeys.legacyClaim)).toBeUndefined();
  });

  it("keeps the claim and resumable marker if legacy cleanup is blocked", async () => {
    const current = new MemoryWorkspaceDb();
    const legacy = new MemoryWorkspaceDb();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    legacy.failDrop = true;
    await legacy.put("files", { id: "f1", records: [] });

    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 1, role: "admin" },
        currentDb: current,
        legacyDb: legacy,
      }),
    ).resolves.toBe(true);

    expect(await current.get("prefs", workspaceDbMigrationKeys.migrationMarker)).toMatchObject({
      owner: "admin:1",
    });
    expect(await legacy.get("prefs", workspaceDbMigrationKeys.legacyClaim)).toMatchObject({
      owner: "admin:1",
    });

    legacy.failDrop = false;
    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 1, role: "admin" },
        currentDb: current,
        legacyDb: legacy,
      }),
    ).resolves.toBe(true);

    expect(legacy.dropped).toBe(true);
    expect(await current.get("prefs", workspaceDbMigrationKeys.migrationMarker)).toBeUndefined();
    warn.mockRestore();
  });

  it("does nothing for non-admin accounts", async () => {
    const current = new MemoryWorkspaceDb();
    const legacy = new MemoryWorkspaceDb();
    await legacy.put("prefs", { key: "workspace", view: "record" });

    await expect(
      migrateLegacyAdminWorkspace({
        user: { id: 9, role: "researcher" },
        currentDb: current,
        legacyDb: legacy,
      }),
    ).resolves.toBe(false);

    expect(await current.count("prefs")).toBe(0);
    expect(legacy.closed).toBe(false);
    expect(legacy.dropped).toBe(false);
  });
});
