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

const calls = vi.hoisted(() => ({ persistLayoutPreferences: vi.fn(), refreshShell: vi.fn() }));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => calls);
vi.mock("../../src/domain/sharedUrlState", () => ({ state: { sidebarCollapsed: false } }));

import { state } from "../../src/domain/sharedUrlState";
import { toggleSidebar } from "../../src/domain/sidebarToggle";

describe("toggleSidebar", () => {
  it("flips the flag, persists it and refreshes the shell", () => {
    toggleSidebar();
    expect((state as { sidebarCollapsed: boolean }).sidebarCollapsed).toBe(true);
    toggleSidebar();
    expect((state as { sidebarCollapsed: boolean }).sidebarCollapsed).toBe(false);
    expect(calls.persistLayoutPreferences).toHaveBeenCalledTimes(2);
    expect(calls.refreshShell).toHaveBeenCalledTimes(2);
  });
});
