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

import { defineComponent } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useAuthStore } from "../../src/stores/auth";
import { useLegacyThreadImport } from "../../src/features/research/useLegacyThreadImport";

const api = vi.hoisted(() => ({ importLegacy: vi.fn() }));
vi.mock("../../src/api/researchThreads", () => ({ researchThreadsApi: api }));
let wrapper: ReturnType<typeof mount>;
let state: ReturnType<typeof useLegacyThreadImport>;
beforeEach(() => {
  vi.useFakeTimers();
  setActivePinia(createPinia());
  useAuthStore().user = { id: 1, role: "admin", capabilities: [] } as never;
  api.importLegacy.mockReset();
});
afterEach(() => {
  wrapper?.unmount();
  vi.useRealTimers();
});
function start() {
  wrapper = mount(
    defineComponent({
      setup() {
        state = useLegacyThreadImport();
        return () => null;
      },
    }),
  );
}

it("automatically imports bounded batches and refreshes the Library", async () => {
  api.importLegacy
    .mockResolvedValueOnce({ created: 200, next_offset: 200, has_more: true })
    .mockResolvedValueOnce({ created: 1, next_offset: 201, has_more: false });
  start();
  expect(api.importLegacy).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(750);
  await flushPromises();
  expect(api.importLegacy.mock.calls).toEqual([[0]]);
  await vi.advanceTimersByTimeAsync(750);
  await flushPromises();
  expect(api.importLegacy.mock.calls).toEqual([[0], [200]]);
  expect(state.refreshKey.value).toBe(2);
  expect(state.busy.value).toBe(false);
  expect(state.hasMore.value).toBe(false);
});

it("keeps migration failure local and retries the same batch", async () => {
  api.importLegacy.mockRejectedValueOnce(new Error("Cache unavailable"));
  start();
  await vi.advanceTimersByTimeAsync(750);
  await flushPromises();
  expect(state.error.value).toBe("Cache unavailable");
  expect(state.refreshKey.value).toBe(0);
  api.importLegacy.mockResolvedValueOnce({ created: 1, next_offset: 1, has_more: false });
  await state.retry();
  expect(api.importLegacy.mock.calls).toEqual([[0], [0]]);
  expect(state.error.value).toBe("");
});

it("ignores old-account completions and stops their next batch", async () => {
  let resolve!: (value: unknown) => void;
  api.importLegacy
    .mockReturnValueOnce(
      new Promise((yes) => {
        resolve = yes;
      }),
    )
    .mockResolvedValueOnce({ created: 0, next_offset: 0, has_more: false });
  start();
  await vi.advanceTimersByTimeAsync(750);
  expect(api.importLegacy.mock.calls).toEqual([[0]]);
  useAuthStore().user = { id: 2, role: "admin", capabilities: [] } as never;
  await flushPromises();
  await vi.advanceTimersByTimeAsync(750);
  await flushPromises();
  resolve({ created: 200, next_offset: 200, has_more: true });
  await flushPromises();
  expect(api.importLegacy.mock.calls).toEqual([[0], [0]]);
  expect(state.refreshKey.value).toBe(1);
  expect(state.hasMore.value).toBe(false);
});
