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

// Browser IndexedDB persistence for the workspace (loaded files, preferences and PDF assets), plus the
// "delete everything DerridAI stored in this browser" routine. Moved from the legacy runtime; the
// database names, version and object stores must not change or existing workspaces would be lost.

export const DB_NAME = "derridai-corpus-viewer";
export const DB_VERSION = 2;

function idbRequest<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** `getName` is read at open time because a researcher's database name depends on the signed-in user. */
export function createWorkspaceDb(getName: () => string) {
  let dbPromise: Promise<IDBDatabase> | null = null;
  let dbName = "";

  function closeConnection(): void {
    const current = dbPromise;
    dbPromise = null;
    dbName = "";
    if (current) {
      void current
        .then((db) => db.close())
        .catch(() => {
          // A failed/opening connection has nothing useful left to close.
        });
    }
  }

  function open(): Promise<IDBDatabase> {
    const requestedName = getName();
    if (dbPromise && dbName === requestedName) return dbPromise;

    // A single-page session can sign out and sign in as another researcher.
    // Never carry the first user's cached IndexedDB connection into the next
    // user's workspace merely because this service module stayed mounted.
    if (dbPromise) closeConnection();

    dbName = requestedName;
    const opening = new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(requestedName, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("files"))
          db.createObjectStore("files", { keyPath: "id" });
        if (!db.objectStoreNames.contains("prefs"))
          db.createObjectStore("prefs", { keyPath: "key" });
        if (!db.objectStoreNames.contains("assets"))
          db.createObjectStore("assets", { keyPath: "key" });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    dbPromise = opening;
    void opening.catch(() => {
      if (dbPromise === opening) {
        dbPromise = null;
        dbName = "";
      }
    });
    return opening;
  }

  async function getAll(storeName: string): Promise<unknown[]> {
    const db = await open();
    const tx = db.transaction(storeName, "readonly");
    return idbRequest(tx.objectStore(storeName).getAll());
  }

  async function get(storeName: string, key: IDBValidKey): Promise<unknown> {
    const db = await open();
    const tx = db.transaction(storeName, "readonly");
    return idbRequest(tx.objectStore(storeName).get(key));
  }

  async function put(storeName: string, value: unknown): Promise<void> {
    const db = await open();
    const tx = db.transaction(storeName, "readwrite");
    await idbRequest(tx.objectStore(storeName).put(value));
  }

  async function add(storeName: string, value: unknown): Promise<void> {
    const db = await open();
    const tx = db.transaction(storeName, "readwrite");
    await idbRequest(tx.objectStore(storeName).add(value));
  }

  async function count(storeName: string): Promise<number> {
    const db = await open();
    const tx = db.transaction(storeName, "readonly");
    return idbRequest(tx.objectStore(storeName).count());
  }

  async function remove(storeName: string, key: IDBValidKey): Promise<void> {
    const db = await open();
    const tx = db.transaction(storeName, "readwrite");
    await idbRequest(tx.objectStore(storeName).delete(key));
  }

  /** Closes the cached connection without deleting the user's persisted workspace. */
  function close(): void {
    closeConnection();
  }

  /** Closes the connection and deletes the current workspace database. Callers cancel their own pending writes first. */
  async function drop(): Promise<void> {
    const requestedName = getName();
    try {
      const db = await open();
      db.close();
    } catch {
      // Best effort: the database may never have opened.
    }
    dbPromise = null;
    dbName = "";
    await new Promise<void>((resolve, reject) => {
      const request = indexedDB.deleteDatabase(requestedName);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
      request.onblocked = () =>
        reject(new Error("IndexedDB deletion is blocked by another open DerridAI tab."));
    });
  }

  return { open, getAll, get, put, add, count, remove, close, drop };
}

export function isDerridaiStorageKey(key: string | null): boolean {
  return (
    Boolean(key) &&
    (key!.startsWith("derridai.") || key!.startsWith("derridai-") || key === "derridai")
  );
}

/** Removes every DerridAI database and localStorage key from this browser. */
export async function deleteAllDerridaiBrowserState(
  dropWorkspaceDatabase: () => Promise<void>,
): Promise<void> {
  await dropWorkspaceDatabase().catch(() => {});
  if (typeof indexedDB.databases === "function") {
    const dbs = await indexedDB.databases();
    await Promise.all(
      (dbs || []).map(
        (info) =>
          new Promise<void>((resolve) => {
            const name = String(info?.name || "");
            if (!name.startsWith("derridai")) return resolve();
            const request = indexedDB.deleteDatabase(name);
            request.onsuccess = () => resolve();
            request.onerror = () => resolve();
            request.onblocked = () => resolve();
          }),
      ),
    );
  }
  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (isDerridaiStorageKey(key)) keys.push(key as string);
    }
    keys.forEach((key) => localStorage.removeItem(key));
  } catch {
    // localStorage can be blocked.
  }
}
