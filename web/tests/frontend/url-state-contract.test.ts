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
import { createNavigation } from "../../src/domain/navigation";
import { compressUrlState } from "../../src/domain/urlState";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// Shareable links outlive the builds that made them, so these pin the URL shapes the runtime reads and writes. They are
// the safety net for replacing urlFromState/applyUrlState with route-query handling.
function setup(files: Array<{ id: string }> = [{ id: "f1" }]) {
  const state = createRuntimeState() as unknown as Record<string, any>;
  state.files = files;
  state.activeFileId = null;
  const activeFile = () => files.find((file) => file.id === state.activeFileId) || null;
  const navigation = createNavigation({
    state,
    activeFile,
    canAccessPage: () => true,
    dbSearchWhere: () => ({}),
    persistPrefs: vi.fn(),
    renderView: vi.fn(),
    selectedIndex: (file: { id: string }) => state.selected[file.id] ?? 0,
    shell: vi.fn(),
  });
  return { state, navigation };
}

function visit(url: string) {
  history.replaceState(null, "", url);
}

afterEach(() => {
  visit("/");
});

describe("shareable URL state", () => {
  it("opens the view named by the path, or by a legacy ?view= parameter", () => {
    const { state, navigation } = setup();
    visit("/works");
    navigation.applyUrlState();
    expect(state.view).toBe("works");
    // A known path wins over ?view=; the parameter only applies on a path with no view of its own.
    visit("/?view=annotations");
    navigation.applyUrlState();
    expect(state.view).toBe("home");
    visit("/old-link?view=faq");
    navigation.applyUrlState();
    expect(state.view).toBe("faq");
    visit("/old-link?view=not-a-view");
    navigation.applyUrlState();
    expect(state.view).toBe("faq");
  });

  it("restores the file and record, but never substitutes another file for an unknown one", () => {
    const { state, navigation } = setup();
    visit("/records?file=f1&record=4");
    navigation.applyUrlState();
    expect(state.activeFileId).toBe("f1");
    expect(state.selected.f1).toBe(4);
    visit("/records?file=missing&record=2");
    navigation.applyUrlState();
    expect(state.activeFileId).toBeNull();
  });

  it("restores vector store, work, page, browse mode and PDF page", () => {
    const { state, navigation } = setup();
    visit("/databases?store=derrida&work=Glas&dbpage=3&browse=records&pdfpage=7");
    navigation.applyUrlState();
    expect(state.activeStore).toBe("derrida");
    expect(state.storeWork).toBe("Glas");
    expect(state.storePage).toBe(3);
    expect(state.storeBrowseMode).toBe("records");
    expect(state.pdf.page).toBe(7);
  });

  it("decodes both the raw and the compressed table state, and the unprefixed legacy form", () => {
    const { state, navigation } = setup();
    const payload = { q: "trace", p: 2, z: 25, m: "traditional" };
    const token = compressUrlState(payload);
    expect(token).toMatch(/^[rz]/);
    visit(`/search?ts=${token}`);
    navigation.applyUrlState();
    expect(state.globalSearch).toBe("trace");
    expect(state.globalPage).toBe(2);
    expect(state.pageSize).toBe(25);
  });

  it("round-trips list state through urlFromState and applyUrlState", () => {
    const first = setup();
    visit("/records");
    first.state.view = "list";
    first.state.activeFileId = "f1";
    first.state.selected.f1 = 3;
    first.state.searches.f1 = "différance";
    first.state.pages.f1 = 2;
    const href = first.navigation.urlFromState();
    expect(href.startsWith("/records?")).toBe(true);
    expect(new URL(href, "http://x").searchParams.get("file")).toBe("f1");
    expect(new URL(href, "http://x").searchParams.get("record")).toBe("3");

    const second = setup();
    visit(href);
    second.navigation.applyUrlState();
    expect(second.state.view).toBe("list");
    expect(second.state.selected.f1).toBe(3);
    expect(second.state.searches.f1).toBe("différance");
    expect(second.state.pages.f1).toBe(2);
  });

  it("keeps the sub-path the router owns for Settings and System Data", () => {
    const { state, navigation } = setup();
    state.view = "config";
    visit("/settings/services");
    expect(navigation.urlFromState().startsWith("/settings/services")).toBe(true);
    state.view = "responsecache";
    visit("/system-data/responses");
    expect(navigation.urlFromState().startsWith("/system-data/responses")).toBe(true);
  });
});
