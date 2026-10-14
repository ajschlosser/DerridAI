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

const h = vi.hoisted(() => ({
  api: vi.fn(),
  refreshStores: vi.fn(async () => undefined),
  shell: vi.fn(),
  renderView: vi.fn(),
  warm: vi.fn(async (..._a: unknown[]) => undefined),
  refreshProviderStatuses: vi.fn(async () => undefined),
}));
vi.mock("../../src/domain/legacyApi", () => ({ api: (...a: unknown[]) => h.api(...a) }));
vi.mock("../../src/domain/sharedStores", () => ({ refreshStores: () => h.refreshStores() }));
vi.mock("../../src/domain/storeWorks", () => ({ refreshStoreWorks: vi.fn() }));
vi.mock("../../src/domain/sharedNavigation", () => ({ renderView: () => h.renderView() }));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({
  persistPrefs: vi.fn(),
  shell: () => h.shell(),
}));
vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  warmupProviderProfile: (...a: unknown[]) => h.warm(...a),
  providerProfilesService: {
    defaultProviderProfile: () => ({ type: "ollama" }),
    ensureProviderProfiles: vi.fn(),
    refreshProviderStatuses: () => h.refreshProviderStatuses(),
  },
}));
vi.mock("../../src/domain/shellSnapshot", () => ({ systemCardHtml: () => "<b>card</b>" }));

import { checkHealth, warmupConfiguredLlm } from "../../src/domain/sharedAppLifecycle";
import { state } from "../../src/domain/sharedUrlState";

describe("shared app lifecycle", () => {
  beforeEach(() => {
    Object.values(h).forEach((m) => m.mockClear());
    document.body.innerHTML = '<div class="system-card"></div>';
    state.appConfig.default_provider_profile = "p1";
  });

  it("warms the configured default provider profile", async () => {
    await warmupConfiguredLlm();
    expect(h.warm).toHaveBeenCalledWith("p1");
  });

  it("records an unreachable API as an unavailable service and still refreshes the card", async () => {
    h.api.mockRejectedValueOnce(new Error("down"));
    await checkHealth();
    expect(state.health).toEqual({ ok: false, error: "down" });
    expect(state.llmStatus).toMatchObject({ available: false, error: "down", provider: "ollama" });
    expect(document.querySelector(".system-card")!.innerHTML).toBe("<b>card</b>");
    expect(h.refreshStores).not.toHaveBeenCalled();
  });

  it("refreshes stores and repaints when Chroma is available", async () => {
    h.api.mockResolvedValueOnce({ ok: true, chroma: { available: true } });
    await checkHealth();
    expect(h.refreshStores).toHaveBeenCalled();
    expect(h.shell).toHaveBeenCalled();
    expect(h.renderView).toHaveBeenCalled();
  });
});
