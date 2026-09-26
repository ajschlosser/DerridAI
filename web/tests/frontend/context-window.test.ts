import { describe, expect, it } from "vitest";
import { fitContext } from "../../src/features/corpus-builder/domain/contextWindow";

const rec = (id: string, chars: number) => ({ id, text: "x".repeat(chars) });
const ids = (items: { id: string }[]) => items.map((item) => item.id);

describe("fitContext", () => {
  const before = [rec("b3", 100), rec("b2", 100), rec("b1", 100)];
  const after = [rec("a1", 100), rec("a2", 100), rec("a3", 100)];

  it("shows the nearest neighbours in document order when the record is small", () => {
    const fit = fitContext(before, after, 200, 1000);
    expect(ids(fit.before)).toEqual(["b3", "b2", "b1"]);
    expect(ids(fit.after)).toEqual(["a1", "a2", "a3"]);
  });

  it("drops the farthest neighbours first as the record grows", () => {
    const fit = fitContext(before, after, 800, 1000);
    expect(ids(fit.before)).toEqual([]);
    expect(ids(fit.after)).toEqual(["a1", "a2"]);
  });

  it("shows no neighbours when the record fills the window", () => {
    expect(fitContext(before, after, 1000, 1000)).toEqual({ before: [], after: [] });
    expect(fitContext(before, after, 5000, 1000)).toEqual({ before: [], after: [] });
  });

  it("gives records above the record the smaller share and passes their leftover on", () => {
    const only = fitContext([], after, 200, 1000);
    expect(ids(only.after)).toEqual(["a1", "a2", "a3"]);
    // 400 left: 160 for the records above (one fits), the other 300 for those below (all three fit).
    const both = fitContext(before, after, 200, 600);
    expect(ids(both.before)).toEqual(["b1"]);
    expect(ids(both.after)).toEqual(["a1", "a2", "a3"]);
  });

  it("charges each neighbour its fixed overhead and never shows a partial neighbour", () => {
    expect(ids(fitContext(before, [], 0, 1000, { beforeShare: 1, overhead: 300 }).before)).toEqual([
      "b2",
      "b1",
    ]);
    expect(fitContext([rec("b1", 500)], [], 0, 400, { beforeShare: 1 }).before).toEqual([]);
  });
});
