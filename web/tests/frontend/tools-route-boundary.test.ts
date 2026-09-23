/* Copyright 2026 Aaron John Schlosser, PhD. */

import { describe, expect, it } from "vitest";
import PdfWorkspaceView from "../../src/views/PdfWorkspaceView.vue";
import VectorStoresView from "../../src/views/VectorStoresView.vue";
import router from "../../src/router";

async function resolvedRouteComponent(path: string): Promise<unknown> {
  const route = router.resolve(path);
  const component = route.matched[0]?.components?.default;
  expect(typeof component).toBe("function");

  const loaded = await (component as () => Promise<unknown>)();
  if (loaded && typeof loaded === "object" && "default" in loaded) {
    return (loaded as { default: unknown }).default;
  }
  return loaded;
}

describe("Tools route boundaries", () => {
  it("routes PDF tools directly to the lazy-loaded Vue-owned workspace", async () => {
    expect(await resolvedRouteComponent("/pdf")).toBe(PdfWorkspaceView);
  });

  it("routes vector tools directly to the lazy-loaded Vue-owned workspace", async () => {
    expect(await resolvedRouteComponent("/databases")).toBe(VectorStoresView);
  });
});
