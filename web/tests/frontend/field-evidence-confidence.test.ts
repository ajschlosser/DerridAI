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
import FieldEvidenceList from "../../src/components/FieldEvidenceList.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("FieldEvidenceList confidence semantics", () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const i18n = useI18nStore();
    i18n.locale = "en-US";
  });

  function render(confidence: number | null | undefined, blockIds: string[] = ["b-1"]) {
    return mount(FieldEvidenceList, {
      global: { plugins: [createPinia()] },
      props: {
        fields: ["speaker"],
        evidence: {
          speaker: { block_ids: blockIds, confidence },
        },
      },
    });
  }

  it("does not manufacture zero confidence when confidence is unavailable", () => {
    expect(render(null).text()).toContain("1 span");
    expect(render(null).text()).not.toContain("0%");
    expect(render(undefined).text()).not.toContain("0%");
  });

  it("renders an explicitly reported zero confidence as zero", () => {
    expect(render(0).text()).toContain("0%");
  });

  it("does not show an evidence score when no evidence span is bound", () => {
    const text = render(0.92, []).text();
    expect(text).toContain("No evidence yet");
    expect(text).not.toContain("92%");
  });
});
