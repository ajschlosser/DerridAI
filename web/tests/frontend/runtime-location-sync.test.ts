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

import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { createRuntimeLocationSync } from "../../src/router/runtimeLocationSync";

const Blank = { render: () => null };
const viewFor = (path: string) => ({ "/records": "list", "/works": "works" })[path];

async function setup(started = true) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ["/", "/records", "/works"].map((path) => ({ path, component: Blank })),
  });
  await router.push("/records");
  await router.isReady();
  const sync = vi.fn();
  let view = "list";
  const link = createRuntimeLocationSync(router, {
    isStarted: () => started,
    viewForPath: viewFor,
    currentView: () => view,
    sync,
  });
  return { router, sync, link, setView: (v: string) => (view = v) };
}

describe("runtime location sync", () => {
  it("does nothing for a navigation within the view the runtime already shows", async () => {
    const { router, sync } = await setup();
    await router.push("/records?q=a");
    expect(sync).not.toHaveBeenCalled();
  });

  it("resyncs when a navigation lands on a different runtime view", async () => {
    const { router, sync } = await setup();
    await router.push("/works");
    expect(sync).toHaveBeenCalledTimes(1);
  });

  it("resyncs on browser back even when the view is unchanged", async () => {
    const { router, sync } = await setup();
    await router.push("/records?q=a");
    router.options.history.go(-1);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await router.isReady();
    expect(router.currentRoute.value.fullPath).toBe("/records");
    expect(sync).toHaveBeenCalledTimes(1);
  });

  it("stays quiet before the runtime has started and after dispose", async () => {
    const early = await setup(false);
    await early.router.push("/works");
    expect(early.sync).not.toHaveBeenCalled();

    const { router, sync, link } = await setup();
    link.dispose();
    await router.push("/works");
    expect(sync).not.toHaveBeenCalled();
  });
});
