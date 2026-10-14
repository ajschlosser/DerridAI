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
import CorpusMetadataResolutionPanel from "../../src/components/CorpusMetadataResolutionPanel.vue";

const record = (over: Record<string, unknown> = {}) => ({
  record_id: "r1",
  text: "t",
  speaker: "Jacques Derrida",
  metadata_field_status: { speaker: { status: "human_confirmed" } },
  metadata_incomplete_fields: [],
  metadata_review_fields: [],
  ...over,
});
const mountPanel = (r = record()) =>
  mount(CorpusMetadataResolutionPanel, {
    props: { record: r as never, regionTypes: ["main_text"], discourseRoles: ["assertion"] },
    attachTo: document.body,
  });

describe("adding a detail a record does not have yet", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("offers the empty quotation fields, so a quoted speaker can be added", async () => {
    const wrapper = mountPanel();
    const add = wrapper.find("details.add-metadata");
    expect(add.exists()).toBe(true);
    expect(add.text()).toContain("Add more details");
    expect(add.text()).toMatch(/quoted speaker/i);
    // A field the record already has is not offered twice.
    expect(add.findAll("article").length).toBeGreaterThan(0);
    wrapper.unmount();
  });

  it("saves a quoted speaker as a list through the same path as any other field", async () => {
    const wrapper = mountPanel();
    const editors = wrapper.findAllComponents({ name: "CorpusMetadataFieldEditor" });
    const quoted = editors.find((e) => e.props("field") === "quoted_speaker")!;
    expect(quoted).toBeTruthy();
    quoted.vm.$emit("save", ["Emmanuel Levinas"]);
    expect(wrapper.emitted("resolve")).toEqual([["quoted_speaker", ["Emmanuel Levinas"]]]);
    wrapper.unmount();
  });

  it("hides the section when every editable field already has a value", () => {
    const full: Record<string, unknown> = {};
    const status: Record<string, unknown> = {};
    for (const f of [
      "region_type",
      "primary_text",
      "discourse_role",
      "region_author",
      "speaker",
      "position_holder",
      "target",
      "stance",
      "proposition_status",
      "claim_scope",
      "semantic_function",
      "is_direct_quote",
      "quoted_speaker",
      "quoted_author",
      "quoted_work",
      "quoted_position_holder",
      "quoted_addressee",
      "quoted_referent",
      "quotation_chain",
      "topics",
      "concepts",
      "persons",
      "works_referenced",
    ]) {
      full[f] = "x";
      status[f] = { status: "human_confirmed" };
    }
    expect(
      mountPanel(record({ ...full, metadata_field_status: status }))
        .find("details.add-metadata")
        .exists(),
    ).toBe(false);
  });
});
