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
import CorpusBoundarySliceDialog from "../../src/components/CorpusBoundarySliceDialog.vue";

const TEXT = "Alpha beta gamma delta epsilon.";

function mountDialog(props: Record<string, unknown> = {}) {
  return mount(CorpusBoundarySliceDialog, {
    props: { text: TEXT, canPrevious: true, canNext: true, ...props },
    global: {
      stubs: {
        UiDialog: { template: '<div><slot/><slot name="footer"/></div>' },
      },
    },
  });
}

async function select(wrapper: ReturnType<typeof mountDialog>, start: number, end: number) {
  const area = wrapper.get("textarea").element as HTMLTextAreaElement;
  area.setSelectionRange(start, end);
  await wrapper.get("textarea").trigger("mouseup");
}

describe("CorpusBoundarySliceDialog", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("splits at a caret", async () => {
    const wrapper = mountDialog();
    await select(wrapper, 11, 11);
    await wrapper.get("button.primary").trigger("click");
    expect(wrapper.emitted("split")?.[0]).toEqual([11]);
    expect(wrapper.emitted("create")).toBeUndefined();
  });

  it("creates a record from a selection and reports the join choices", async () => {
    const wrapper = mountDialog();
    await select(wrapper, 6, 16);
    await wrapper.get('input[name="slice-left"][value="merge_prior"]').setValue(true);
    await wrapper.get("button.primary").trigger("click");
    expect(wrapper.emitted("create")?.[0]).toEqual([6, 16, "merge_prior", "distinct"]);
  });

  it("refuses a selection of the whole record", async () => {
    const wrapper = mountDialog();
    await select(wrapper, 0, TEXT.length);
    expect(wrapper.get("button.primary").attributes("disabled")).toBeDefined();
  });

  it("does not offer joining a neighbour that does not exist", async () => {
    const wrapper = mountDialog({ canPrevious: false });
    await select(wrapper, 6, 16);
    expect(
      wrapper.get('input[name="slice-left"][value="merge_prior"]').attributes("disabled"),
    ).toBeDefined();
  });
});
