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

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const claimsApi = vi.hoisted(() => ({
  get: vi.fn(),
  setValidation: vi.fn(),
}));
vi.mock("../../src/api/claims", () => ({ claimsApi }));

import ResearchClaimReviewPanel from "../../src/components/research/ResearchClaimReviewPanel.vue";
import type { ResearchClaimProvenance } from "../../src/types/research";

function supportedProvenance(): ResearchClaimProvenance {
  return {
    claims: [
      {
        claim_id: "c1",
        claim_text: "Hospitality exceeds the conditions that regulate it.",
        validation_status: "unvalidated",
      },
    ],
    support_bindings: [
      {
        support_binding_id: "s1",
        claim_id: "c1",
        record_id: "r1",
        record_revision: 2,
        relation: "supports",
        validation_status: "unvalidated",
        citation: { inline: "(Derrida, 25)", evidence_marker: "E1" },
      },
    ],
  };
}

describe("ResearchClaimReviewPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    claimsApi.get.mockResolvedValue({
      claim: {
        claim_id: "c1",
        claim_text: "Hospitality exceeds the conditions that regulate it.",
        validation_status: "unvalidated",
      },
    });
  });

  it("validates a supported claim without leaving the Research answer", async () => {
    claimsApi.setValidation.mockResolvedValue({
      claim: {
        claim_id: "c1",
        claim_text: "Hospitality exceeds the conditions that regulate it.",
        validation_status: "validated",
        validated_by: "ann",
      },
      projection: { status: "indexed", error: "" },
    });

    const wrapper = mount(ResearchClaimReviewPanel, {
      props: {
        provenance: supportedProvenance(),
        evidence: [{ evidence_id: "E1", record: { record_id: "r1", record_revision: 2 } }],
      },
    });
    await flushPromises();

    const validate = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Validate claim"));
    expect(validate).toBeTruthy();
    await validate!.trigger("click");
    await flushPromises();

    expect(claimsApi.setValidation).toHaveBeenCalledWith("c1", "validated", {
      record_id: "r1",
      record_revision: 2,
    });
    expect(wrapper.text()).toContain("Validated");
    expect(wrapper.text()).toContain("ann");
  });

  it("opens the bound evidence from the claim card", async () => {
    const wrapper = mount(ResearchClaimReviewPanel, {
      props: {
        provenance: supportedProvenance(),
        evidence: [{ evidence_id: "E1", record: { record_id: "r1" } }],
        refreshAuthoritative: false,
      },
    });

    await wrapper.get(".research-claim-evidence-link").trigger("click");
    expect(wrapper.emitted("evidence")?.[0]).toEqual([0]);
  });

  it("blocks validation when the claim has no usable support binding", async () => {
    const wrapper = mount(ResearchClaimReviewPanel, {
      props: {
        provenance: {
          claims: [
            {
              claim_id: "c1",
              claim_text: "Unsupported claim.",
              validation_status: "unvalidated",
            },
          ],
          support_bindings: [],
        },
        refreshAuthoritative: false,
      },
    });

    const validate = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Validate claim"));
    expect(validate?.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("No usable support binding");
    expect(claimsApi.setValidation).not.toHaveBeenCalled();
  });

  it("refreshes stale retained-run status from the authoritative claim row", async () => {
    claimsApi.get.mockResolvedValue({
      claim: {
        claim_id: "c1",
        claim_text: "Hospitality exceeds the conditions that regulate it.",
        validation_status: "validated",
        validated_by: "reviewer",
      },
    });

    const wrapper = mount(ResearchClaimReviewPanel, {
      props: { provenance: supportedProvenance() },
    });
    await flushPromises();

    expect(claimsApi.get).toHaveBeenCalledWith("c1");
    expect(wrapper.text()).toContain("Validated");
    expect(wrapper.text()).toContain("reviewer");
  });
});
