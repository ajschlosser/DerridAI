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

const api = vi.fn();
vi.mock("../../src/domain/legacyApi", () => ({ api: (...args: unknown[]) => api(...args) }));
vi.mock("../../src/composables/notifications", () => ({ toast: vi.fn() }));

import { refreshResearcherContentPolicy } from "../../src/domain/researcherInputFilter";
import { normalizeResearcherToken } from "../../src/domain/researcherContentFilter";
import { sessionState } from "../../src/state/workspaceState";

async function digest(word: string) {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(normalizeResearcherToken(word)),
  );
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function typeInto(input: HTMLInputElement, value: string) {
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  await vi.waitFor(() => expect(api).toHaveBeenCalled());
  await new Promise((resolve) => setTimeout(resolve, 20));
}

describe("researcher input filter", () => {
  beforeEach(() => {
    api.mockReset();
    document.body.innerHTML = '<input id="q" type="text" />';
  });

  it("removes a blocked term from a researcher's text input", async () => {
    sessionState.userContext = { id: "r1", role: "researcher" } as never;
    api.mockResolvedValue({ ready: true, blocked_term_hashes: [await digest("badword")] });
    await refreshResearcherContentPolicy();
    const input = document.querySelector("#q") as HTMLInputElement;
    input.value = "keep badword this";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await vi.waitFor(() => expect(input.value).toBe("keep this"));
  });

  it("leaves an administrator's input alone", async () => {
    sessionState.userContext = { id: "a1", role: "admin" } as never;
    api.mockResolvedValue({ ready: true, blocked_term_hashes: [await digest("badword")] });
    await refreshResearcherContentPolicy();
    const input = document.querySelector("#q") as HTMLInputElement;
    await typeInto(input, "keep badword this");
    expect(input.value).toBe("keep badword this");
  });
});
