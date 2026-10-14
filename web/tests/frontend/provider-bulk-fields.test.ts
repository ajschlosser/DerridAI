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

import { describe, expect, it } from "vitest";
import { applyProfileFieldValues, mergeSavedProfile } from "../../src/domain/providerBulkFields";
import type { ProviderProfile } from "../../src/api/system";

const ollama = {
  id: "o1",
  name: "Local",
  type: "ollama",
  num_ctx: 4096,
  temperature: 0,
} as ProviderProfile;
const openai = {
  id: "p1",
  name: "Cloud",
  type: "openai",
  num_predict: 512,
  temperature: 0.2,
} as ProviderProfile;

describe("provider bulk fields", () => {
  it("merges one saved profile without rewriting the others", () => {
    const next = mergeSavedProfile([ollama, openai], { ...openai, temperature: 0.7 });
    expect(next[0].temperature).toBe(0);
    expect(next[1].temperature).toBe(0.7);
  });

  it("applies shared values to every selected profile and skips type-specific fields", () => {
    const next = applyProfileFieldValues([ollama, openai], ["o1", "p1"], {
      temperature: 0.4,
      num_ctx: 8192,
      num_predict: 2048,
    });
    expect(next[0]).toMatchObject({ temperature: 0.4, num_ctx: 8192, num_predict: 2048 });
    expect(next[1]).toMatchObject({ temperature: 0.4, num_predict: 2048 });
    expect(next[1].num_ctx).toBeUndefined();
  });
});
