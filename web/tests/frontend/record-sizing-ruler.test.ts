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
import CorpusRecordSizingSettings from "../../src/components/CorpusRecordSizingSettings.vue";

const policy = {
  preferred_record_chars: 1750,
  record_length_tolerance: 200,
  long_record_chars: 3500,
  absolute_record_chars: 6000,
};

describe("record sizing ruler", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("draws only the policy when no build has been made", () => {
    const wrapper = mount(CorpusRecordSizingSettings, { props: { modelValue: policy } });
    expect(wrapper.find(".observed").exists()).toBe(false);
  });

  it("plots what the last build produced on the same scale as the policy", () => {
    const wrapper = mount(CorpusRecordSizingSettings, {
      props: {
        modelValue: policy,
        observed: {
          p10_record_chars: 900,
          median_record_chars: 1800,
          p90_record_chars: 3000,
          max_record_chars: 12000,
        },
      },
    });
    expect(wrapper.find(".observed-band").exists()).toBe(true);
    // The scale reaches the ceiling (6,000); a 1,800-character median sits at 30% of it.
    const median = parseFloat((wrapper.get(".observed-median").element as HTMLElement).style.left);
    expect(median).toBeGreaterThan(29);
    expect(median).toBeLessThan(31);
    expect(wrapper.get(".observed-note").text()).toContain("12,000");
  });

  it("ignores an empty build's statistics", () => {
    const wrapper = mount(CorpusRecordSizingSettings, {
      props: { modelValue: policy, observed: { median_record_chars: 0 } },
    });
    expect(wrapper.find(".observed").exists()).toBe(false);
  });
});
