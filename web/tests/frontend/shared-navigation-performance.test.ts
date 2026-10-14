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

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

function controlAnimationFrames() {
  let nextId = 0;
  const callbacks = new Map<number, FrameRequestCallback>();
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((callback: FrameRequestCallback) => {
      const id = ++nextId;
      callbacks.set(id, callback);
      return id;
    }),
  );
  return {
    runFrame() {
      const current = [...callbacks.values()];
      callbacks.clear();
      for (const callback of current) callback(performance.now());
    },
  };
}

describe("location-change repaint scope", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lets the native destination paint before compatibility shell work", () => {
    const frames = controlAnimationFrames();

    repaintAfterLocationChange();

    expect(storage.persistPrefs).not.toHaveBeenCalled();
    expect(storage.refreshShell).not.toHaveBeenCalled();
    expect(storage.shell).not.toHaveBeenCalled();
    expect(operations.unmountOperationsPanel).toHaveBeenCalledTimes(1);
    expect(navigation.syncUrl).not.toHaveBeenCalled();

    frames.runFrame();
    expect(storage.refreshShell).not.toHaveBeenCalled();

    frames.runFrame();
    expect(storage.refreshShell).toHaveBeenCalledTimes(1);
  });

  it("coalesces rapid native route settlements to one post-paint shell refresh", () => {
    const frames = controlAnimationFrames();

    repaintAfterLocationChange();
    repaintAfterLocationChange();
    frames.runFrame();
    frames.runFrame();

    expect(storage.persistPrefs).not.toHaveBeenCalled();
    expect(storage.refreshShell).toHaveBeenCalledTimes(1);
    expect(operations.unmountOperationsPanel).toHaveBeenCalledTimes(2);
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
