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
import { beforeEach, describe, expect, it } from "vitest";
import UiTableColumnsDialog from "../../src/components/ui/UiTableColumnsDialog.vue";
import type { ColumnWidths } from "../../src/domain/tableColumnWidths";

const available = [
  { key: "work", label: "Work" },
  { key: "text", label: "Text" },
  { key: "speaker", label: "Speaker" },
];

function mountDialog(props: { modelValue: string[]; widths?: ColumnWidths | null }) {
  const state = { keys: props.modelValue, widths: props.widths ?? null };
  const wrapper = mount(UiTableColumnsDialog, {
    attachTo: document.body,
    props: {
      available,
      ...props,
      "onUpdate:modelValue": (keys: string[]) => {
        state.keys = keys;
        void wrapper.setProps({ modelValue: keys });
      },
      "onUpdate:widths": (widths: ColumnWidths) => {
        state.widths = widths;
        void wrapper.setProps({ widths });
      },
    },
  });
  (wrapper.vm as unknown as { open: () => void }).open();
  return { wrapper, state };
}
const q = <T extends Element = HTMLElement>(selector: string) =>
  document.body.querySelector<T>(selector)!;
const qa = <T extends Element = HTMLElement>(selector: string) => [
  ...document.body.querySelectorAll<T>(selector),
];

describe("UiTableColumnsDialog", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("adds a hidden field and reorders the shown columns", async () => {
    const { wrapper, state } = mountDialog({ modelValue: ["work", "text"] });
    await flushPromises();
    q<HTMLButtonElement>(".ui-columns-add").click();
    await flushPromises();
    expect(state.keys).toEqual(["work", "text", "speaker"]);
    q<HTMLButtonElement>('[aria-label="Move Speaker up"]').click();
    await flushPromises();
    expect(state.keys).toEqual(["work", "speaker", "text"]);
    wrapper.unmount();
  });

  it("keeps at least one column and offers no width controls unless widths are given", async () => {
    const { wrapper } = mountDialog({ modelValue: ["work"] });
    await flushPromises();
    expect(q<HTMLButtonElement>('[aria-label="Hide Work"]').disabled).toBe(true);
    expect(qa("input[type=number]")).toHaveLength(0);
    wrapper.unmount();
  });

  it("sizes one column and rebalances the others proportionally", async () => {
    const { wrapper, state } = mountDialog({
      modelValue: ["work", "text", "speaker"],
      widths: { work: 20, text: 60, speaker: 20 },
    });
    await flushPromises();
    const inputs = qa<HTMLInputElement>("input[type=number]");
    expect(inputs.map((input) => input.value)).toEqual(["20", "60", "20"]);
    expect(inputs[1].closest("label")?.textContent).toContain("Width of Text");
    inputs[1].value = "40";
    inputs[1].dispatchEvent(new Event("change"));
    await flushPromises();
    expect(state.widths).toEqual({ work: 30, text: 40, speaker: 30 });
    wrapper.unmount();
  });

  it("gives a newly shown column its share and keeps the total at 100", async () => {
    const { wrapper, state } = mountDialog({
      modelValue: ["work", "text"],
      widths: { work: 25, text: 75 },
    });
    await flushPromises();
    q<HTMLButtonElement>(".ui-columns-add").click();
    await flushPromises();
    const widths = state.widths!;
    expect(Object.keys(widths)).toEqual(["work", "text", "speaker"]);
    expect(Object.values(widths).reduce((a, b) => a + b, 0)).toBeCloseTo(100, 5);
    expect(widths.text / widths.work).toBeCloseTo(3, 1);
    wrapper.unmount();
  });
});
