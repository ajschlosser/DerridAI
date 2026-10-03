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
import "../../src/runtime/runtimeBridge";
import { normalizeTouchupItems, openTouchup } from "../../src/domain/touchupLauncher";
import { state } from "../../src/domain/sharedUrlState";

const file = { id: "f1", records: [{ record_id: "a" }, { record_id: "b" }] };

describe("touch-up launcher", () => {
  afterEach(() => {
    state.files = [];
    state.activeFileId = null;
    vi.restoreAllMocks();
  });

  it("keys the given items and drops those whose record is gone", () => {
    const items = normalizeTouchupItems([
      { file, index: 1 },
      { file, index: 9 },
    ]);
    expect(items).toHaveLength(1);
    expect(items[0].key).toBe("f1::1");
    expect(items[0].record.record_id).toBe("b");
  });

  it("opens nothing when there are no items and no selected record", () => {
    const dispatch = vi.spyOn(window, "dispatchEvent");
    openTouchup();
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("dispatches the open event with the items and mode", () => {
    const seen: CustomEvent[] = [];
    const listener = (event: Event) => seen.push(event as CustomEvent);
    window.addEventListener("derridai:open-touchup", listener);
    openTouchup([{ file, index: 0 }], "auto");
    window.removeEventListener("derridai:open-touchup", listener);
    expect(seen).toHaveLength(1);
    expect(seen[0].detail.initialMode).toBe("auto");
    expect(seen[0].detail.items[0].key).toBe("f1::0");
  });
});
