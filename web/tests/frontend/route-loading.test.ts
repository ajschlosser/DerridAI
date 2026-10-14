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
import { flushPromises } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { createRouteLoading } from "../../src/router/routeLoading";
const Blank = { render: () => null };
function deferred() {
  let resolve!: (value: typeof Blank) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<typeof Blank>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
async function setup() {
  const a = deferred(),
    b = deferred();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: Blank },
      { path: "/a", name: "a", component: () => a.promise },
      { path: "/b", component: () => b.promise },
    ],
  });
  await router.push("/");
  const state = createRouteLoading(router);
  return { router, state, a, b };
}
afterEach(() => vi.useRealTimers());
describe("route module feedback", () => {
  it("delays feedback without delaying navigation or replacing the current route", async () => {
    const { router, state, a } = await setup();
    vi.useFakeTimers();
    const navigation = router.push("/a");
    await flushPromises();
    expect(state.visible.value).toBe(false);
    expect(router.currentRoute.value.path).toBe("/");
    vi.advanceTimersByTime(180);
    expect(state.visible.value).toBe(true);
    a.resolve(Blank);
    await navigation;
    expect(state.visible.value).toBe(false);
    expect(router.currentRoute.value.path).toBe("/a");
    state.dispose();
  });
  it("does not flash a status for a fast navigation or same-page filter changes", async () => {
    const { router, state, a } = await setup();
    vi.useFakeTimers();
    a.resolve(Blank);
    await router.push("/a");
    vi.advanceTimersByTime(200);
    expect(state.visible.value).toBe(false);
    await router.push("/a?q=term");
    expect(state.destination.value).toBeNull();
    state.dispose();
  });
  it("keeps the replacement navigation pending when an older navigation settles", async () => {
    const { router, state, a, b } = await setup();
    vi.useFakeTimers();
    const first = router.push("/a");
    await flushPromises();
    const second = router.push("/b");
    await flushPromises();
    a.resolve(Blank);
    await first;
    vi.advanceTimersByTime(180);
    expect(state.destination.value?.path).toBe("/b");
    expect(state.visible.value).toBe(true);
    b.resolve(Blank);
    await second;
    expect(state.visible.value).toBe(false);
    state.dispose();
  });
  it("exposes failed chunks for retry while retaining the current page", async () => {
    const { router, state, a } = await setup();
    const first = router.push("/a");
    await flushPromises();
    a.reject(new Error("chunk unavailable"));
    await expect(first).rejects.toThrow("chunk unavailable");
    expect(router.currentRoute.value.path).toBe("/");
    expect(state.failed.value?.path).toBe("/a");
    router.addRoute({ path: "/a", component: Blank, name: "a" });
    await state.retry();
    expect(router.currentRoute.value.path).toBe("/a");
    expect(state.failed.value).toBeNull();
    state.dispose();
  });
  it("removes hooks and timers on disposal", async () => {
    const { router, state, a } = await setup();
    vi.useFakeTimers();
    const navigation = router.push("/a");
    await flushPromises();
    state.dispose();
    vi.advanceTimersByTime(200);
    expect(state.visible.value).toBe(false);
    a.resolve(Blank);
    await navigation;
    expect(state.failed.value).toBeNull();
  });
});
