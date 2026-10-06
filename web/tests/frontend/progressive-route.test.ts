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
import { createPinia } from "pinia";
import { defineComponent, h, type Component } from "vue";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import { describe, expect, it, vi } from "vitest";
import { progressiveRouteComponent } from "../../src/router/progressiveRoute";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

const Root = defineComponent({
  name: "ProgressiveRouteTestRoot",
  setup: () => () => h(RouterView),
});

const LoadedPage = defineComponent({
  name: "LoadedPage",
  setup: () => () => h("div", { "data-test": "loaded-page" }, "Loaded page"),
});

async function setup(loader: () => Promise<{ default: Component } | Component>) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { render: () => null } },
      {
        path: "/slow",
        component: progressiveRouteComponent(loader),
      },
    ],
  });
  await router.push("/");
  await router.isReady();
  const wrapper = mount(Root, {
    global: {
      plugins: [createPinia(), router],
    },
  });
  return { router, wrapper };
}

describe("progressive route components", () => {
  it("commits navigation before the destination chunk resolves", async () => {
    const pending = deferred<{ default: Component }>();
    const { router, wrapper } = await setup(() => pending.promise);

    const navigation = router.push("/slow");
    await navigation;
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/slow");
    expect(wrapper.find(".progressive-route-loading").exists()).toBe(true);
    expect(wrapper.text()).toContain("Loading page content");

    pending.resolve({ default: LoadedPage });
    await flushPromises();

    expect(wrapper.get('[data-test="loaded-page"]').text()).toBe("Loaded page");
    wrapper.unmount();
  });

  it("lets a transient page-module failure retry without leaving the destination", async () => {
    const loader = vi
      .fn<() => Promise<{ default: Component }>>()
      .mockRejectedValueOnce(new Error("temporary chunk failure"))
      .mockResolvedValueOnce({ default: LoadedPage });
    const { router, wrapper } = await setup(loader);

    await router.push("/slow");
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/slow");
    expect(wrapper.find(".progressive-route-error").exists()).toBe(true);

    const retry = wrapper
      .findAllComponents({ name: "UiButton" })
      .find((button) => button.props("label") === "Retry");
    expect(retry).toBeTruthy();
    retry!.vm.$emit("click");
    await flushPromises();

    expect(loader).toHaveBeenCalledTimes(2);
    expect(wrapper.get('[data-test="loaded-page"]').text()).toBe("Loaded page");
    wrapper.unmount();
  });
});
