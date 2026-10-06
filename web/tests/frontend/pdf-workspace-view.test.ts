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
import { defineComponent, onActivated, onDeactivated, onMounted, onUnmounted } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";
import PdfWorkspaceView from "../../src/views/PdfWorkspaceView.vue";

function trackedComponent(name: string, counters: Record<string, number>) {
  return defineComponent({
    name,
    setup() {
      onMounted(() => counters.mounted++);
      onUnmounted(() => counters.unmounted++);
      onActivated(() => counters.activated++);
      onDeactivated(() => counters.deactivated++);
    },
    template: `<div data-tracked="${name}" />`,
  });
}

async function mountWorkspace() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/corpus-builder",
        name: "corpus-builder",
        component: { template: "<div />" },
        meta: { pdfMode: "builder" },
      },
      {
        path: "/source-explorer",
        name: "source-explorer",
        component: { template: "<div />" },
        meta: { pdfMode: "explorer" },
      },
    ],
  });
  await router.push({
    name: "corpus-builder",
    query: { workspace: "review", build: "b1", queue: "metadata", record: "r1" },
  });
  await router.isReady();

  const builder = { mounted: 0, unmounted: 0, activated: 0, deactivated: 0 };
  const explorer = { mounted: 0, unmounted: 0, activated: 0, deactivated: 0 };
  const wrapper = mount(PdfWorkspaceView, {
    global: {
      plugins: [pinia, router],
      stubs: {
        PdfCorpusBuilder: trackedComponent("PdfCorpusBuilder", builder),
        PdfExplorerSurface: trackedComponent("PdfExplorerSurface", explorer),
      },
    },
  });
  await flushPromises();
  return { wrapper, router, builder, explorer };
}

describe("PDF workspace sibling navigation", () => {
  it(
    "keeps Builder mounted while visiting Source Explorer and restores each route snapshot",
    async () => {
    const { wrapper, router, builder, explorer } = await mountWorkspace();
    const tabs = () => wrapper.findAll(".pdf-mode-tabs button");

    expect(builder.mounted).toBe(1);
    expect(builder.unmounted).toBe(0);

    await tabs()[1].trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("source-explorer");
    expect(router.currentRoute.value.query).toEqual({});
    expect(builder.unmounted).toBe(0);
    expect(builder.deactivated).toBe(1);
    expect(explorer.mounted).toBe(1);

    await router.replace({
      name: "source-explorer",
      query: { file: "f1", record: "7", pdfpage: "3" },
    });
    await flushPromises();

    await tabs()[0].trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("corpus-builder");
    expect(router.currentRoute.value.query).toEqual({
      workspace: "review",
      build: "b1",
      queue: "metadata",
      record: "r1",
    });
    expect(builder.mounted).toBe(1);
    expect(builder.unmounted).toBe(0);
    expect(builder.activated).toBeGreaterThanOrEqual(2);

    await tabs()[1].trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query).toEqual({
      file: "f1",
      record: "7",
      pdfpage: "3",
    });

      wrapper.unmount();
    },
  );
});
