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
import { toast } from "../../src/composables/notifications";
import { createModalDialogs } from "../../src/domain/modalDialogs";

vi.mock("../../src/composables/notifications", () => ({ toast: vi.fn() }));

describe("copyJsonToClipboard", () => {
  it("announces the copy through a translatable key rather than English text", async () => {
    const writeText = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const trf = vi.fn((key: string, values: Record<string, unknown>) => `${key}:${values.label}`);
    const { copyJsonToClipboard } = createModalDialogs({ state: {}, trf } as never);

    await copyJsonToClipboard({ a: 1 }, "fiche");

    expect(writeText).toHaveBeenCalledWith(JSON.stringify({ a: 1 }, null, 2));
    expect(toast).toHaveBeenCalledWith("runtime.toast.json_copied:fiche", { tone: "success" });
    vi.unstubAllGlobals();
  });
});
