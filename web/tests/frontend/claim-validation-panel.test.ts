// Copyright 2026 Aaron John Schlosser, PhD.
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
