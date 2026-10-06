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
import PdfWorkspaceView from "../../src/views/PdfWorkspaceView.vue";
import VectorStoresView from "../../src/views/VectorStoresView.vue";
import router from "../../src/router";
import { progressiveRouteLoaderFor } from "../../src/router/progressiveRoute";

async function resolvedRouteComponent(path: string): Promise<unknown> {
  const route = router.resolve(path);
  const component = route.matched[0]?.components?.default;
  expect(typeof component).toBe("object");

  const loader = progressiveRouteLoaderFor(component);
  expect(loader).toBeTypeOf("function");
  const loaded = await loader!();
  if (loaded && typeof loaded === "object" && "default" in loaded) {
    return (loaded as { default: unknown }).default;
  }
  return loaded;
}

describe("Tools route boundaries", () => {
  it("routes PDF tools through the progressive Vue-owned workspace", async () => {
    expect(await resolvedRouteComponent("/corpus-builder")).toBe(PdfWorkspaceView);
  });

  it("routes vector tools through the progressive Vue-owned workspace", async () => {
    expect(await resolvedRouteComponent("/databases")).toBe(VectorStoresView);
  });
});
