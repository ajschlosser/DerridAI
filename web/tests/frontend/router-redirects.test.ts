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

import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter, type RouteRecordRaw } from "vue-router";
import { APP_ROUTES } from "../../src/router";

const StubView = { template: "<div />" };

function testRouter() {
  const routes = APP_ROUTES.map((route) =>
    route.redirect ? route : ({ ...route, component: StubView } as RouteRecordRaw),
  );
  return createRouter({ history: createMemoryHistory(), routes });
}

describe("legacy route compatibility", () => {
  it.each([
    ["/pdf?mode=explorer&file=f1&api_key=sk-private", "source-explorer", { file: "f1" }],
    ["/pdf?file=f2&password=private", "corpus-builder", { file: "f2" }],
    ["/response-cache?store=responses&token=private", "system-data-responses", { store: "responses" }],
    ["/system-data?section=pipelines&work=Glas&secret=private", "pipelines", { work: "Glas" }],
    ["/system-data/pipelines?work=Margins&credential=private", "pipelines", { work: "Margins" }],
    ["/settings?section=providers&tab=models&draft=private", "settings-section", { tab: "models" }],
  ])("redirects %s to its canonical route without unsafe query state", async (source, name, query) => {
    const router = testRouter();

    await router.push(source);

    expect(router.currentRoute.value.name).toBe(name);
    expect(router.currentRoute.value.query).toEqual(query);
    expect(router.currentRoute.value.fullPath).not.toMatch(
      /api_key|password|token|secret|credential|draft|private/i,
    );
  });
});
