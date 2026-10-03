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
