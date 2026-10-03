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

import { flushPromises, shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CorpusCaptureDialog from "../../src/components/capture/CorpusCaptureDialog.vue";
import SourceTable from "../../src/components/sources/SourceTable.vue";
import SourcesView from "../../src/views/SourcesView.vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusCaptureApi: { listCaptures: vi.fn(async () => ({ items: [] })) },
}));

async function openDialog() {
  const wrapper = shallowMount(SourcesView);
  await flushPromises();
  (wrapper.vm as unknown as { openCapture: () => void }).openCapture();
  await flushPromises();
  return wrapper;
}
const key = (wrapper: Awaited<ReturnType<typeof openDialog>>) =>
  wrapper.getComponent(SourceTable).props("refreshKey");
const settled = (status: string) => ({
  capture_id: "c1",
  author: { canonical_name: "A" },
  status,
  active_job: null,
});

describe("Sources view table refresh", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it.each(["complete", "partial", "failed", "cancelled", "interrupted"])(
    "reloads the table in place when a capture settles as %s",
    async (status) => {
      const wrapper = await openDialog();
      const before = key(wrapper);
      wrapper.getComponent(CorpusCaptureDialog).vm.$emit("changed", settled(status));
      await flushPromises();
      expect(key(wrapper)).not.toBe(before);
    },
  );

  it("does not reload while a capture is still running", async () => {
    const wrapper = await openDialog();
    const before = key(wrapper);
    wrapper
      .getComponent(CorpusCaptureDialog)
      .vm.$emit("changed", { ...settled("acquiring"), active_job: { job_id: "j" } });
    await flushPromises();
    expect(key(wrapper)).toBe(before);
  });

  it("reloads when the dialog is closed", async () => {
    const wrapper = await openDialog();
    const before = key(wrapper);
    wrapper.getComponent(CorpusCaptureDialog).vm.$emit("close");
    await flushPromises();
    expect(key(wrapper)).not.toBe(before);
  });
});
