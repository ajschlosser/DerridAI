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

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusModelActivity from "../../src/components/CorpusModelActivity.vue";

const activity = (over = {}) => ({
  state: "loading_model" as const,
  task: "manifest" as const,
  model: "qwen-14b",
  provider: "ollama",
  seconds: 108,
  calls_in_flight: 1,
  ...over,
});

describe("model activity line", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("says a large model is still loading, with the elapsed time", () => {
    const text = mount(CorpusModelActivity, { props: { activity: activity() } }).text();
    expect(text).toContain("Waiting for qwen-14b to load into memory");
    expect(text).toContain("1 min 48 s");
  });
  it("says what a loaded model is working on", () => {
    const text = mount(CorpusModelActivity, {
      props: { activity: activity({ state: "working", task: "segmentation", seconds: 12 }) },
    }).text();
    expect(text).toContain("qwen-14b is working on the record boundaries (12 s)");
  });
  it("falls back to plain waiting when the provider cannot say, and shows nothing when idle", () => {
    expect(
      mount(CorpusModelActivity, {
        props: { activity: activity({ state: "unknown", seconds: 5 }) },
      }).text(),
    ).toContain("Waiting for qwen-14b to answer");
    expect(
      mount(CorpusModelActivity, { props: { activity: null } })
        .find("p")
        .exists(),
    ).toBe(false);
  });
});
