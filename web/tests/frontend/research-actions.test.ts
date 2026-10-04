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
import {
  cancelResearchJob,
  registerResearchActions,
  startResearchRun,
} from "../../src/domain/researchActions";

describe("researchActions facade", () => {
  afterEach(() => registerResearchActions(null));

  it("forwards arguments and results to the registered implementation", async () => {
    const cancel = vi.fn().mockResolvedValue({ id: "j1", status: "cancelling" });
    registerResearchActions({ cancelResearchJob: cancel });
    await expect(cancelResearchJob("j1")).resolves.toEqual({ id: "j1", status: "cancelling" });
    expect(cancel).toHaveBeenCalledWith("j1");
  });

  it("fails loudly when called before registration", () => {
    expect(() => startResearchRun({})).toThrow(/not ready/);
  });
});
