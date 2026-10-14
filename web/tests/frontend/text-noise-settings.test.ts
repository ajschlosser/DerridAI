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
import CorpusTextNoiseSettings from "../../src/components/CorpusTextNoiseSettings.vue";

describe("text noise settings", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("exposes the threshold on a labelled range and emits a new copy", async () => {
    const wrapper = mount(CorpusTextNoiseSettings, {
      props: { threshold: 45, llmAssist: false, mediaKind: "pdf" },
    });
    expect(wrapper.text()).toContain("Source illegibility");
    const slider = wrapper.get('input[type="range"]');
    expect(slider.attributes("aria-valuenow")).toBe("45");
    await slider.setValue("60");
    expect(wrapper.emitted("update:threshold")?.[0]).toEqual([60]);
  });

  it("explains and hides the PDF-only LLM second opinion for other media", () => {
    const wrapper = mount(CorpusTextNoiseSettings, {
      props: { threshold: 45, llmAssist: false, mediaKind: "audio" },
    });
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("currently available only for PDF page extraction");
  });

  it("LLM assist is off until switched on", async () => {
    const wrapper = mount(CorpusTextNoiseSettings, {
      props: { threshold: 45, llmAssist: false, mediaKind: "pdf" },
    });
    const box = wrapper.get('input[type="checkbox"]');
    expect((box.element as HTMLInputElement).checked).toBe(false);
    await box.setValue(true);
    expect(wrapper.emitted("update:llmAssist")?.[0]).toEqual([true]);
  });
});
