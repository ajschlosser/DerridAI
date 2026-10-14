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
import { renderView } from "../../src/domain/sharedNavigation";
import { setShellRefreshHook } from "../../src/domain/sharedWorkspaceStorage";
import { state } from "../../src/domain/sharedUrlState";

afterEach(() => {
  document.body.innerHTML = "";
  setShellRefreshHook(() => {});
});

describe("renderView", () => {
  it("only refreshes the shell on native Vue routes without #main", () => {
    const refresh = vi.fn();
    setShellRefreshHook(refresh);
    const before = state.view;
    expect(renderView()).toBeNull();
    expect(refresh).toHaveBeenCalled();
    expect(state.view).toBe(before);
  });
});
