// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import {
  detectRecipe,
  marginBand,
  matchRegion,
  placeMargin,
  presetRegions,
  regionFromRect,
  resizeRegion,
} from "../../src/domain/documentLayoutRegions";

describe("document layout regions", () => {
  it("lets a smaller margin band win over the full-page main region", () => {
    const regions = presetRegions("margin", "left");
    const margin = matchRegion(regions, 3, [40, 80, 140, 400], 1000, 1400);
    const body = matchRegion(regions, 3, [400, 80, 900, 400], 1000, 1400);
    expect(margin?.role).toBe("margin_apparatus");
    expect(body?.role).toBe("main");
  });

  it("lets a page-only rectangle beat a repeating one", () => {
    const regions = [
      ...presetRegions("infobox"),
      {
        ...presetRegions("infobox")[1],
        id: "plate",
        applies_to: "page" as const,
        page: 4,
        x0: 0.1,
        y0: 0.1,
        x1: 0.9,
        y1: 0.9,
        role: "running_matter" as const,
      },
    ];
    const onPlate = matchRegion(regions, 4, [200, 200, 800, 800], 1000, 1400);
    const elsewhere = matchRegion(regions, 5, [700, 150, 900, 400], 1000, 1400);
    expect(onPlate?.id).toBe("plate");
    expect(elsewhere?.role).toBe("infobox");
  });

  it("treats facing pages with extra regions as a custom layout", () => {
    expect(detectRecipe("two_up", [])).toBe("two_up");
    expect(detectRecipe("two_up", presetRegions("margin"))).toBe("custom");
    expect(detectRecipe("single", [])).toBe("single");
  });

  it("flips a margin band to the other edge without changing its width", () => {
    const flipped = placeMargin(marginBand("left"), "right");
    expect(flipped.x1).toBe(1);
    expect(flipped.x1 - flipped.x0).toBeCloseTo(0.2);
  });

  it("guesses a side strip as a margin and keeps a drawn region on every page", () => {
    const region = regionFromRect({ x0: 0.02, y0: 0.1, x1: 0.18, y1: 0.9 }, 6, []);
    expect(region.role).toBe("margin_apparatus");
    expect(region.applies_to).toBe("all");
    expect(region.flow).toBe("separate");
  });

  it("does not collapse a region while it is resized from the keyboard", () => {
    const region = marginBand("left");
    const grown = resizeRegion(region, "e", 0.32, region.y1);
    expect(grown.x1).toBeCloseTo(0.32);
    expect(grown.x1 - grown.x0).toBeGreaterThan(0.03);
  });
});
