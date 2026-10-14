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
import { pauseRuntime, registerJobsPause } from "../../src/domain/jobsPause";

const stop = vi.hoisted(() => vi.fn());
vi.mock("../../src/realtime", () => ({ realtime: { stop } }));

describe("jobs pause", () => {
  afterEach(() => {
    registerJobsPause(null);
    stop.mockClear();
  });

  it("closes only the realtime socket before a workspace has registered", () => {
    pauseRuntime();
    expect(stop).toHaveBeenCalledTimes(1);
  });

  it("delegates to the registered workspace pause instead", () => {
    const pause = vi.fn();
    registerJobsPause(pause);
    pauseRuntime();
    expect(pause).toHaveBeenCalledTimes(1);
    expect(stop).not.toHaveBeenCalled();
  });
});
