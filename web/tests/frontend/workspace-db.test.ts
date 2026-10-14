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

import { afterEach, describe, expect, it, vi } from "vitest";
import { createWorkspaceDb } from "../../src/services/workspaceDb";

describe("workspace database connection ownership", () => {
  const originalIndexedDb = globalThis.indexedDB;

  afterEach(() => {
    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      value: originalIndexedDb,
    });
  });

  it("closes and reopens the cached connection when the workspace database name changes", async () => {
    let name = "derridai-user-a";
    const closeA = vi.fn();
    const closeB = vi.fn();
    const opens: string[] = [];

    const factory = {
      open(requestedName: string) {
        opens.push(requestedName);
        const request: Record<string, unknown> = {
          result: {
            objectStoreNames: { contains: () => true },
            createObjectStore: vi.fn(),
            close: requestedName === "derridai-user-a" ? closeA : closeB,
          },
          error: null,
        };
        queueMicrotask(() => {
          (request.onsuccess as (() => void) | undefined)?.();
        });
        return request;
      },
    };

    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      value: factory as unknown as IDBFactory,
    });

    const workspaceDb = createWorkspaceDb(() => name);
    const first = await workspaceDb.open();

    name = "derridai-user-b";
    const second = await workspaceDb.open();
    await Promise.resolve();

    expect(opens).toEqual(["derridai-user-a", "derridai-user-b"]);
    expect(first).not.toBe(second);
    expect(closeA).toHaveBeenCalledTimes(1);

    workspaceDb.close();
    await Promise.resolve();
    expect(closeB).toHaveBeenCalledTimes(1);
  });
});
