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

import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { createRuntimeUrlSyncHook } from "../../src/router/runtimeUrlSync";

const view = { template: "<div />" };

async function makeRouter(guard?: () => boolean) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: view },
      { path: "/a", component: view },
      { path: "/blocked", component: view },
    ],
  });
  router.beforeEach((to) => (to.path === "/blocked" && guard ? guard() : true));
  await router.push("/");
  return router;
}

describe("runtime URL sync hook", () => {
  afterEach(() => vi.restoreAllMocks());

  it("pushes or replaces the target and does not resync on success", async () => {
    const router = await makeRouter();
    const resync = vi.fn();
    const hook = createRuntimeUrlSyncHook(router, resync);
    hook("/a?x=1");
    await router.isReady();
    await new Promise((r) => setTimeout(r, 0));
    expect(router.currentRoute.value.fullPath).toBe("/a?x=1");
    hook("/", { replace: true });
    await new Promise((r) => setTimeout(r, 0));
    expect(router.currentRoute.value.fullPath).toBe("/");
    expect(resync).not.toHaveBeenCalled();
  });

  it("does nothing when the router is already at the target", async () => {
    const router = await makeRouter();
    const push = vi.spyOn(router, "push");
    createRuntimeUrlSyncHook(router, vi.fn())("/");
    expect(push).not.toHaveBeenCalled();
  });

  it("resyncs the runtime when a guard aborts the navigation", async () => {
    const router = await makeRouter(() => false);
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const resync = vi.fn();
    createRuntimeUrlSyncHook(router, resync)("/blocked");
    await new Promise((r) => setTimeout(r, 0));
    expect(resync).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.fullPath).toBe("/");
  });

  it("resyncs when the navigation throws", async () => {
    const router = await makeRouter(() => {
      throw new Error("boom");
    });
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const resync = vi.fn();
    createRuntimeUrlSyncHook(router, resync)("/blocked");
    await new Promise((r) => setTimeout(r, 0));
    expect(resync).toHaveBeenCalledTimes(1);
  });
});
