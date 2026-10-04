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

import { afterEach, describe, expect, it } from "vitest";
import { createUrlStateCodec } from "../../src/domain/urlStateCodec";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// The codec must work without navigation, rendering or persistence helpers, so a router-based replacement can use it.
describe("URL state codec", () => {
  afterEach(() => history.replaceState(null, "", "/"));

  it("never carries credentials or transient editor state into a shareable URL", () => {
    const state = createRuntimeState() as unknown as Record<string, any>;
    state.view = "global";
    state.appConfig = { ...(state.appConfig || {}), openai_api_key: "sk-private" };
    state.ragConfig = { ...(state.ragConfig || {}), prompt: "private research prompt" };
    state.comparePasteA = "private pasted corpus text";
    history.replaceState(
      null,
      "",
      "/search?api_key=raw-secret&prompt=private-prompt&draft=unsaved&workspace_hint=keep",
    );

    const codec = createUrlStateCodec({
      state,
      activeFile: () => null,
      dbSearchWhere: () => ({}),
      selectedIndex: () => -1,
    });
    const href = codec.urlFromState();
    const url = new URL(href, "https://derridai.local");

    expect(url.searchParams.get("api_key")).toBeNull();
    expect(url.searchParams.get("prompt")).toBeNull();
    expect(url.searchParams.get("draft")).toBeNull();
    expect(url.searchParams.get("workspace_hint")).toBe("keep");
    expect(href).not.toContain("sk-private");
    expect(href).not.toContain("private research prompt");
    expect(href).not.toContain("private pasted corpus text");
  });

  it("round-trips the view, file and record through a URL with only read helpers", () => {
    const state = createRuntimeState() as unknown as Record<string, any>;
    state.files = [{ id: "f1" }];
    const codec = createUrlStateCodec({
      state,
      activeFile: () =>
        state.files.find((f: { id: string }) => f.id === state.activeFileId) || null,
      dbSearchWhere: () => ({}),
      selectedIndex: () => 3,
    });
    state.view = "list";
    state.activeFileId = "f1";
    const href = codec.urlFromState();
    expect(href.startsWith("/records?")).toBe(true);
    expect(new URLSearchParams(href.split("?")[1]).get("record")).toBe("3");

    history.replaceState(null, "", href);
    state.view = "home";
    state.activeFileId = null;
    state.selected = {};
    codec.applyUrlState();
    expect(state.view).toBe("list");
    expect(state.activeFileId).toBe("f1");
    expect(state.selected.f1).toBe(3);
  });
});

describe("shared URL state codec", () => {
  afterEach(() => history.replaceState(null, "", "/"));

  it("applies a URL to the same state the runtime reads, with no runtime involved", async () => {
    const { sharedUrlStateCodec } = await import("../../src/domain/sharedUrlState");
    const { useNavigationStore } = await import("../../src/stores/workspace");
    const { createPinia, setActivePinia } = await import("pinia");
    setActivePinia(createPinia());
    const runtimeState = createRuntimeState() as unknown as Record<string, any>;

    runtimeState.files = [];
    runtimeState.activeFileId = null;
    history.replaceState(null, "", "/works");
    sharedUrlStateCodec.applyUrlState();
    expect(runtimeState.view).toBe("works");
    expect(useNavigationStore().view).toBe("works");

    runtimeState.view = "global";
    expect(sharedUrlStateCodec.urlFromState().startsWith("/search")).toBe(true);
  });
});
