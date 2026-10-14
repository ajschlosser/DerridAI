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

const claimsApi = vi.hoisted(() => ({ setValidation: vi.fn(), similar: vi.fn() }));
vi.mock("../../src/api/claims", () => ({ claimsApi }));

import ClaimValidationPanel from "../../src/components/record/ClaimValidationPanel.vue";

function mountPanel(props: Record<string, unknown> = {}) {
  return mount(ClaimValidationPanel, {
    props: { claimId: "c1", status: "unvalidated", record: { record_id: "r1" }, ...props },
  });
}

describe("ClaimValidationPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    claimsApi.similar.mockResolvedValue({ items: [] });
  });

  it("validates the claim and sends only the audited record", async () => {
    claimsApi.setValidation.mockResolvedValue({
      claim: { claim_id: "c1", validation_status: "validated" },
      projection: { status: "indexed", error: "" },
    });
    const wrapper = mountPanel();
    await flushPromises();
    await wrapper.findAll("button")[0].trigger("click");
    await flushPromises();
    expect(claimsApi.setValidation).toHaveBeenCalledWith("c1", "validated", { record_id: "r1" });
    expect(wrapper.emitted("changed")?.[0]).toEqual(["validated"]);
    expect(wrapper.find("[role=alert]").exists()).toBe(false);
  });

  it("keeps the decision but surfaces a projection failure", async () => {
    claimsApi.setValidation.mockResolvedValue({
      claim: { claim_id: "c1", validation_status: "validated" },
      projection: { status: "failed", error: "chroma down" },
    });
    const wrapper = mountPanel();
    await flushPromises();
    await wrapper.findAll("button")[0].trigger("click");
    await flushPromises();
    expect(wrapper.get("[role=alert]").text()).toContain("chroma down");
    expect(wrapper.emitted("changed")).toBeTruthy();
  });

  it("lists similar validated claims as advisory precedent", async () => {
    claimsApi.similar.mockResolvedValue({
      items: [
        {
          claim_id: "c0",
          claim_text: "Presence is always deferred.",
          similarity: 0.87,
          validated_by: "ann",
          advisory: true,
          support: [{ record_id: "r9", semantic: { speaker: { value: "Derrida" } } }],
        },
      ],
    });
    const wrapper = mountPanel();
    await flushPromises();
    expect(wrapper.text()).toContain("Presence is always deferred.");
    expect(wrapper.text()).toContain("speaker: Derrida");
    expect(wrapper.text()).toContain("ann");
  });
});
