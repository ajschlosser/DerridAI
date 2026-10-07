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

const storage = vi.hoisted(() => ({
  persistPrefs: vi.fn(),
  refreshShell: vi.fn(),
  shell: vi.fn(),
}));
const operations = vi.hoisted(() => ({ unmountOperationsPanel: vi.fn() }));
const navigation = vi.hoisted(() => ({ syncUrl: vi.fn() }));

vi.mock("../../src/state/workspaceState", () => ({
  sessionState: { userContext: null },
}));
vi.mock("../../src/domain/pageAccess", () => ({
  canAccessView: () => true,
}));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => storage);
vi.mock("../../src/domain/operationsPanelHost", () => operations);
vi.mock("../../src/domain/sharedUrlState", () => ({
  state: { view: "home" },
  activeFile: vi.fn(),
  dbSearchWhere: vi.fn(),
  selectedIndex: vi.fn(),
  sharedUrlStateCodec: {},
}));
vi.mock("../../src/domain/navigation", () => ({
  createNavigation: () => ({
    getUrlSyncHook: vi.fn(),
    navSnapshot: vi.fn(),
    setUrlSyncHook: vi.fn(),
    currentTableUrlState: vi.fn(),
    applyCompressedTableUrlState: vi.fn(),
    urlFromState: vi.fn(),
    syncUrl: navigation.syncUrl,
    applyUrlState: vi.fn(),
    navigateTo: vi.fn(),
  }),
}));

import { repaintAfterLocationChange } from "../../src/domain/sharedNavigation";

describe("location-change repaint scope", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("refreshes native Vue chrome exactly once", () => {
    repaintAfterLocationChange();

    expect(storage.persistPrefs).toHaveBeenCalledTimes(1);
    expect(storage.refreshShell).toHaveBeenCalledTimes(1);
    expect(storage.shell).not.toHaveBeenCalled();
    expect(operations.unmountOperationsPanel).toHaveBeenCalledTimes(1);
    expect(navigation.syncUrl).not.toHaveBeenCalled();
  });

  it("refreshes a legacy surface exactly once before compatibility rendering", () => {
    document.body.innerHTML = '<main id="main"></main>';

    repaintAfterLocationChange();

    expect(storage.persistPrefs).toHaveBeenCalledTimes(1);
    expect(storage.refreshShell).toHaveBeenCalledTimes(1);
    expect(storage.shell).not.toHaveBeenCalled();
    expect(navigation.syncUrl).toHaveBeenCalledTimes(1);
  });
});
