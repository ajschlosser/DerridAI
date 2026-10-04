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
import { createMemoryHistory, createRouter } from "vue-router";
import { APP_ROUTES } from "../../src/router";

function routerForCompatibilityLinks() {
  return createRouter({
    history: createMemoryHistory(),
    routes: APP_ROUTES,
  });
}

describe("canonical route compatibility redirects", () => {
  it.each([
    ["/response-cache?owner=me", "/system-data/responses?owner=me"],
    ["/system-data?section=pipelines&owner=me", "/pipelines?owner=me"],
    ["/system-data?section=metadata&owner=me", "/system-data/metadata?owner=me"],
    ["/pdf?mode=explorer&file=abc", "/source-explorer?file=abc"],
    ["/pdf?file=abc", "/corpus-builder?file=abc"],
    ["/settings?section=services&tab=models", "/settings/services?tab=models"],
  ])("redirects %s to its canonical route without dropping safe query state", async (legacy, canonical) => {
    const router = routerForCompatibilityLinks();

    await router.push(legacy);

    expect(router.currentRoute.value.fullPath).toBe(canonical);
  });

  it("normalizes an unsupported System Data section to overview", async () => {
    const router = routerForCompatibilityLinks();

    await router.push("/system-data?section=not-a-workspace&owner=me");

    expect(router.currentRoute.value.fullPath).toBe("/system-data/overview?owner=me");
  });
});
