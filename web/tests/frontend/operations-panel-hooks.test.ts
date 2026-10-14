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
  mountOperationsPanelHost,
  openJobResults,
  registerOperationsPanelHooks,
} from "../../src/domain/operationsPanelHooks";

describe("operations panel hooks", () => {
  afterEach(() => registerOperationsPanelHooks(null));

  it("does nothing before the runtime registers them", () => {
    expect(() => openJobResults("j1")).not.toThrow();
    expect(() => mountOperationsPanelHost()).not.toThrow();
  });

  it("forwards to the registered functions", () => {
    const hooks = { mountOperationsPanelHost: vi.fn(), openJobResults: vi.fn() };
    registerOperationsPanelHooks(hooks);
    openJobResults("j1");
    mountOperationsPanelHost();
    expect(hooks.openJobResults).toHaveBeenCalledWith("j1");
    expect(hooks.mountOperationsPanelHost).toHaveBeenCalledOnce();
  });
});
