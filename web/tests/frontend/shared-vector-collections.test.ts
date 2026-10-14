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

import { beforeEach, describe, expect, it, vi } from "vitest";

const h = vi.hoisted(() => ({ canUse: vi.fn(), openUpsertQueue: vi.fn(), toast: vi.fn() }));
vi.mock("../../src/composables/notifications", () => ({
  toast: (...a: unknown[]) => h.toast(...a),
}));
vi.mock("../../src/domain/sharedSession", () => ({ canUse: (...a: unknown[]) => h.canUse(...a) }));
vi.mock("../../src/domain/sharedRecordDialogs", () => ({
  recordDialogs: { openUpsertQueue: () => h.openUpsertQueue() },
}));

import { triggerUpsertQueue } from "../../src/domain/sharedVectorCollections";

describe("triggerUpsertQueue", () => {
  beforeEach(() => Object.values(h).forEach((m) => m.mockReset()));

  it("opens the queue only for accounts that can manage the corpus", () => {
    h.canUse.mockReturnValue(true);
    triggerUpsertQueue();
    expect(h.openUpsertQueue).toHaveBeenCalled();
  });

  it("warns instead when the account cannot manage databases", () => {
    h.canUse.mockReturnValue(false);
    triggerUpsertQueue();
    expect(h.openUpsertQueue).not.toHaveBeenCalled();
    expect(h.toast).toHaveBeenCalledWith(expect.any(String), { tone: "warning" });
  });
});
