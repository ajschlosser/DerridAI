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
import { defineComponent, ref } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it, vi } from "vitest";
import { useCorpusWorkspaceNavigation } from "../../src/features/corpus-builder/composables/useCorpusWorkspaceNavigation";

async function harness(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/corpus-builder", name: "corpus-builder", component: { template: "<div />" } }],
  });
  await router.push({ name: "corpus-builder", query });
  await router.isReady();

  const currentBuild = ref({
    build_id: "build-1",
    record_count: 4,
    status: "awaiting_review",
  } as never);
  const hasRecordTopology = ref(true);
  const reviewReady = ref(true);
  const component = defineComponent({
    setup() {
      return useCorpusWorkspaceNavigation({
        currentBuild,
        hasRecordTopology,
        reviewReady,
      });
    },
    template: "<div />",
  });
  const wrapper = mount(component, { global: { plugins: [router] } });
  return { wrapper, router };
}

describe("Corpus Builder workspace navigation history", () => {
  it("pushes deliberate workspace navigation by default", async () => {
    const { wrapper, router } = await harness({ workspace: "build", build: "build-1" });
    const push = vi.spyOn(router, "push");
    const replace = vi.spyOn(router, "replace");

    await (wrapper.vm as unknown as { switchWorkspace: (workspace: string) => Promise<void> })
      .switchWorkspace("review");

    expect(push).toHaveBeenCalledTimes(1);
    expect(replace).not.toHaveBeenCalled();
    expect(router.currentRoute.value.query.workspace).toBe("review");
    wrapper.unmount();
  });

  it("replaces automatic workflow transitions and clears review-only route state", async () => {
    const { wrapper, router } = await harness({
      workspace: "review",
      build: "build-1",
      queue: "metadata",
      record: "record-3",
    });
    const push = vi.spyOn(router, "push");
    const replace = vi.spyOn(router, "replace");

    await (
      wrapper.vm as unknown as {
        switchWorkspace: (workspace: string, navigation: "push" | "replace") => Promise<void>;
      }
    ).switchWorkspace("publish", "replace");

    expect(replace).toHaveBeenCalledTimes(1);
    expect(push).not.toHaveBeenCalled();
    expect(router.currentRoute.value.query).toMatchObject({
      workspace: "publish",
      build: "build-1",
    });
    expect(router.currentRoute.value.query.queue).toBeUndefined();
    expect(router.currentRoute.value.query.record).toBeUndefined();
    wrapper.unmount();
  });
});
