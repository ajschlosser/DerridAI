/* Copyright 2026 Aaron John Schlosser, PhD. */

import { describe, expect, it } from "vitest";
import PdfWorkspaceView from "../../src/views/PdfWorkspaceView.vue";
import VectorStoresView from "../../src/views/VectorStoresView.vue";
import router from "../../src/router";

describe("Tools route boundaries", () => {
  it("routes PDF tools directly to the Vue-owned workspace", () => {
    const route = router.resolve("/pdf");

    expect(route.matched[0]?.components?.default).toBe(PdfWorkspaceView);
  });

  it("routes vector tools directly to the Vue-owned workspace", () => {
    const route = router.resolve("/databases");

    expect(route.matched[0]?.components?.default).toBe(VectorStoresView);
  });
});
