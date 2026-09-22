/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import RecordsSubsetDialog from "../../src/components/records/RecordsSubsetDialog.vue";
import { loadSubsetProfiles } from "../../src/domain/subsetProfiles";

const records = [
  { record_id: "r1", document_author: "Jacques Derrida", work: "Glas" },
  { record_id: "r2", document_author: "jacques derrida", work: "Margins" },
  { record_id: "r3", document_author: "Paul de Man", work: "Allegories" },
];
function mountDialog() {
  const wrapper = mount(RecordsSubsetDialog, {
    attachTo: document.body,
    props: {
      sources: [{ id: "active", name: "tab.jsonl", count: 3 }],
      fields: [
        { key: "document_author", label: "Document author" },
        { key: "work", label: "Work" },
      ],
      defaultName: "tab-subset.jsonl",
      recordsFor: () => records,
    },
  });
  (wrapper.vm as unknown as { open: () => void }).open();
  return wrapper;
}
const dialog = () => document.body.querySelector<HTMLElement>("[role=dialog]")!;
const status = () => dialog().querySelector("[role=status]")!.textContent!.trim();
const button = (text: string) =>
  [...dialog().querySelectorAll<HTMLButtonElement>("button")].find(
    (item) => item.textContent?.trim() === text,
  )!;

describe("RecordsSubsetDialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("counts matches live and explains case-sensitive matching", async () => {
    const wrapper = mountDialog();
    await flushPromises();
    expect(status()).toBe("2 of 3 source records match");
    const checkbox = dialog().querySelector<HTMLInputElement>("input[type=checkbox]")!;
    expect(
      document.getElementById(checkbox.getAttribute("aria-describedby")!)?.textContent,
    ).toContain("capitals are ignored");
    checkbox.click();
    await flushPromises();
    expect(status()).toBe("1 of 3 source records match");
    wrapper.unmount();
  });

  it("labels every condition control and blocks creation without a condition", async () => {
    const wrapper = mountDialog();
    await flushPromises();
    for (const control of dialog().querySelectorAll(
      ".subset-condition select, .subset-condition input",
    ))
      expect(control.getAttribute("aria-label")).toMatch(/item 1$/);
    dialog().querySelector<HTMLButtonElement>('[aria-label="Remove item 1"]')!.click();
    await flushPromises();
    expect(button("Create subset file").disabled).toBe(true);
    expect(button("Create subset file").getAttribute("aria-describedby")).toBeTruthy();
    expect(dialog().textContent).toContain("Add at least one condition.");
    wrapper.unmount();
  });

  it("saves the current filter as a named profile without a browser prompt", async () => {
    const wrapper = mountDialog();
    await flushPromises();
    button("Save current…").click();
    await flushPromises();
    const nameInput = [...dialog().querySelectorAll<HTMLInputElement>("input")].find((input) =>
      input.closest("label")?.textContent?.includes("Profile name"),
    )!;
    nameInput.value = "Derrida only";
    nameInput.dispatchEvent(new Event("input"));
    await flushPromises();
    button("Save profile").click();
    await flushPromises();
    expect(loadSubsetProfiles()).toMatchObject([
      {
        name: "Derrida only",
        caseSensitive: false,
        expression: [{ rule: { field: "document_author" } }],
      },
    ]);
    wrapper.unmount();
  });
});
