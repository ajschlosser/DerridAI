// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import {
  clampRelationZoom,
  fitRelationBounds,
  moveRelationPoint,
  relationBoundsForPoints,
  relationGraphToScreen,
  relationScreenToGraph,
  screenDeltaToGraph,
  zoomRelationViewportAt,
} from "../../src/domain/relations/geometry";

describe("relation viewport geometry", () => {
  it("converts graph and screen coordinates symmetrically", () => {
    const viewport = { pan: { x: 40, y: -20 }, zoom: 2 };
    const graph = { x: 15, y: 25 };
    const screen = relationGraphToScreen(graph, viewport);
    expect(screen).toEqual({ x: 70, y: 30 });
    expect(relationScreenToGraph(screen, viewport)).toEqual(graph);
  });

  it("converts screen drag distance into graph distance at the current zoom", () => {
    expect(screenDeltaToGraph({ x: 30, y: -10 }, 2)).toEqual({ x: 15, y: -5 });
    expect(moveRelationPoint({ x: 100, y: 50 }, { x: 30, y: -10 }, 2)).toEqual({
      x: 115,
      y: 45,
    });
  });

  it("clamps invalid and out-of-range zoom values", () => {
    expect(clampRelationZoom(0.1)).toBe(0.45);
    expect(clampRelationZoom(10)).toBe(6);
    expect(clampRelationZoom(Number.NaN)).toBe(1);
  });

  it("keeps the graph point under a screen anchor fixed while zooming", () => {
    const initial = { pan: { x: 20, y: 10 }, zoom: 1 };
    const anchor = { x: 120, y: 60 };
    const graphBefore = relationScreenToGraph(anchor, initial);
    const next = zoomRelationViewportAt(initial, 2, anchor);
    const graphAfter = relationScreenToGraph(anchor, next);
    expect(graphAfter).toEqual(graphBefore);
    expect(next).toEqual({ pan: { x: -80, y: -40 }, zoom: 2 });
  });

  it("computes padded bounds and fits them into a viewport", () => {
    const bounds = relationBoundsForPoints(
      [
        { x: 0, y: 0 },
        { x: 200, y: 100 },
      ],
      10,
    );
    expect(bounds).toEqual({ x: -10, y: -10, width: 220, height: 120 });
    const fitted = fitRelationBounds(bounds!, { width: 500, height: 300 }, { padding: 20 });
    expect(fitted.zoom).toBeCloseTo(2.0909, 3);
    const centre = relationGraphToScreen({ x: 100, y: 50 }, fitted);
    expect(centre.x).toBeCloseTo(250);
    expect(centre.y).toBeCloseTo(150);
  });

  it("returns null bounds when no finite points are available", () => {
    expect(relationBoundsForPoints([])).toBeNull();
    expect(relationBoundsForPoints([{ x: Number.NaN, y: 2 }])).toBeNull();
  });
});
