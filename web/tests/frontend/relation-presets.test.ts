// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { RELATION_SURFACE_PRESETS } from "../../src/domain/relations/presets";

describe("relation surface presets", () => {
  it("defines the five normalized relation configurations", () => {
    expect(Object.values(RELATION_SURFACE_PRESETS).map((preset) => preset.id)).toEqual([
      "semantic-free",
      "semantic-network",
      "semantic-radial",
      "provenance-lanes",
      "pipeline-dag",
    ]);
  });

  it("keeps the shared interaction contract enabled for every real map", () => {
    for (const preset of Object.values(RELATION_SURFACE_PRESETS)) {
      expect(preset.panByDrag).toBe(true);
      expect(preset.draggableNodes).toBe(true);
      expect(preset.keyboardNudge).toBe(true);
      expect(preset.fitToContent).toBe(true);
      expect(preset.minZoom).toBeLessThan(1);
      expect(preset.maxZoom).toBeGreaterThan(1);
    }
  });

  it("retains distinct domain-appropriate layouts and node visuals", () => {
    expect(RELATION_SURFACE_PRESETS.semanticNetwork).toMatchObject({
      layout: "force",
      nodeVisual: "dot",
      edgeVisual: "curved",
    });
    expect(RELATION_SURFACE_PRESETS.semanticRadial.layout).toBe("radial");
    expect(RELATION_SURFACE_PRESETS.provenanceLanes).toMatchObject({
      layout: "lanes",
      nodeVisual: "card",
    });
    expect(RELATION_SURFACE_PRESETS.pipelineDag).toMatchObject({
      layout: "dag",
      edgeVisual: "directed",
    });
  });
});
