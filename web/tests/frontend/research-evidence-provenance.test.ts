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
import { describe, expect, it } from "vitest";
import ResearchEvidenceProvenance from "../../src/components/research/ResearchEvidenceProvenance.vue";
import type { ResearchClaimProvenance, ResearchResultEvidence } from "../../src/types/research";

function render(evidence: ResearchResultEvidence, provenance?: ResearchClaimProvenance) {
  return mount(ResearchEvidenceProvenance, { props: { evidence, provenance } });
}
const rows = (wrapper: ReturnType<typeof render>) =>
  Object.fromEntries(
    wrapper
      .findAll(".research-evidence-provenance-source > dt")
      .map((dt) => [dt.text(), (dt.element.nextElementSibling as HTMLElement).textContent?.trim()]),
  );

describe("Research evidence provenance", () => {
  it("states a missing locator and revision instead of inventing them", () => {
    const wrapper = render({ evidence_id: "E1", record: { record_id: "r1", text: "x" } });
    expect(rows(wrapper)).toEqual({
      "Location in source": "Location not recorded",
      "Record revision": "Not recorded",
    });
    expect(wrapper.text()).toContain("No generated claim is bound to this passage.");
  });

  it("shows source document and unit identities only when the evidence carries them", () => {
    const wrapper = render({
      evidence_id: "E1",
      record: {
        record_id: "r1",
        source_document_id: "doc-7",
        source_spans: [{ source_unit_id: "u2" }, { source_unit_id: "u2" }, { block_id: "b1" }],
        source_unit_ids: ["u3"],
      },
    });
    expect(rows(wrapper)).toMatchObject({ "Source document": "doc-7", "Source units": "u2, u3" });
  });

  it("keeps printed and physical pages distinct and shows known source metadata only", () => {
    const wrapper = render({
      evidence_id: "E1",
      record: {
        record_id: "r1",
        work: "De la grammatologie",
        edition: "Minuit 1967",
        printed_page_start: "97",
        printed_page_end: "98",
        physical_page_start: 112,
        record_revision: 3,
      },
    });
    expect(rows(wrapper)).toEqual({
      Work: "De la grammatologie",
      Edition: "Minuit 1967",
      "Location in source": "Printed p. 97–98 · PDF p. 112",
      "Record revision": "3",
    });
  });

  it("locates audio evidence by time, never by page", () => {
    const wrapper = render({
      evidence_id: "E1",
      record: { record_id: "a1", time_start: "00:01:05", time_end: "00:01:40", page: 4 },
    });
    expect(rows(wrapper)["Location in source"]).toBe("Time 00:01:05–00:01:40");
  });

  it("lists only this marker's bindings with separate binding and claim status", () => {
    const provenance: ResearchClaimProvenance = {
      claims: [
        { claim_id: "c1", claim_text: "Supported claim", validation_status: "validated" },
        { claim_id: "c2", claim_text: "Disputed claim", validation_status: "rejected" },
        { claim_id: "c3", claim_text: "Other passage claim" },
      ],
      support_bindings: [
        {
          support_binding_id: "b1",
          claim_id: "c1",
          record_id: "r1",
          record_revision: 2,
          relation: "supports",
          citation: { evidence_marker: "E1" },
          validation_status: "stale",
        },
        {
          support_binding_id: "b2",
          claim_id: "c2",
          record_id: "r1",
          record_revision: 2,
          relation: null,
          citation: { evidence_marker: "E1" },
        },
        {
          support_binding_id: "b3",
          claim_id: "c3",
          record_id: "r1",
          citation: { evidence_marker: "E2" },
          validation_status: "validated",
        },
      ],
    };
    const wrapper = render(
      { evidence_id: "E1", record: { record_id: "r1", record_revision: 2 } },
      provenance,
    );
    const items = wrapper.findAll(".research-evidence-provenance-bindings li");
    expect(items).toHaveLength(2);
    expect(wrapper.text()).not.toContain("Other passage claim");
    expect(items[0].text()).toContain("Supported claim");
    expect(items[0].find("[data-status='stale']").text()).toBe("Stale");
    expect(items[0].find("[data-status='validated']").text()).toBe("Validated");
    expect(items[1].text()).toContain("Not stated");
    expect(items[1].find("[data-status='unvalidated']").text()).toBe("Not yet audited");
    expect(items[1].find("[data-status='rejected']").text()).toBe("Rejected");
    expect(wrapper.find(".research-evidence-provenance-warning").exists()).toBe(false);
  });

  it("flags a binding made against a different record revision", () => {
    const wrapper = render(
      { evidence_id: "E1", record: { record_id: "r1", record_revision: 4 } },
      {
        claims: [{ claim_id: "c1", claim_text: "Older claim" }],
        support_bindings: [
          {
            support_binding_id: "b1",
            claim_id: "c1",
            record_id: "r1",
            record_revision: 2,
            citation: { evidence_marker: "E1" },
          },
        ],
      },
    );
    expect(wrapper.find(".research-evidence-provenance-warning").text()).toBe(
      "Bound to revision 2; this passage is revision 4.",
    );
  });
});
