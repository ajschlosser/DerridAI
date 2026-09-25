/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  barChart,
  lineChart,
  multiLineChart,
  pieChart,
  statList,
} from "../../src/domain/dashboardCharts";

// The snapshots were verified to be byte-identical to the output of the original legacy runtime.js
// functions before they were recorded.
const rows = Array.from({ length: 4 }, (_, i) => ({
  key: `2026-01-0${i + 1}`,
  a: i * 3,
  b: (i % 2) * 5,
}));
const series = Array.from({ length: 3 }, (_, i) => ({
  key: `<W${i}>`,
  value: (i + 1) * 1234.5,
  count: i + 2,
}));
const entries = series.map((s) => [s.key, s.value]) as Array<[string, number]>;

describe("dashboard charts", () => {
  it("draws multi-series line charts", () => {
    expect(
      multiLineChart(rows, "Runs", [{ key: "a" }, { key: "b" }], { note: "n&" }),
    ).toMatchSnapshot();
    expect(multiLineChart([], "Runs", [{ key: "a" }])).toContain("no data yet");
  });
  it("draws single-series line charts", () => {
    expect(lineChart(series, "Trend", "Legend")).toMatchSnapshot();
    expect(lineChart([], "Trend")).toContain("no data yet");
  });
  it("draws bar charts, pie charts and ranked lists", () => {
    expect(barChart(series, "Length", { valueLabel: "Words" })).toMatchSnapshot();
    expect(pieChart("Share", entries)).toMatchSnapshot();
    expect(pieChart("Share", [["a", 0]])).toContain("no records loaded");
    expect(statList("Top", entries)).toMatchSnapshot();
    expect(statList("Top", [])).toContain("No data");
  });
  it("localizes empty states through the chart i18n API", () => {
    const tr = (key: string, fallback = "") =>
      key === "dashboard.no_data_yet"
        ? "aucune donnée pour le moment"
        : key === "dashboard.no_records_loaded"
          ? "aucune fiche chargée"
          : fallback;
    expect(multiLineChart([], "Runs", [{ key: "a" }], { tr })).toContain(
      "aucune donnée pour le moment",
    );
    expect(lineChart([], "Trend", "Legend", { tr })).not.toContain("no data yet");
    expect(pieChart("Share", [["a", 0]], { tr })).toContain("aucune fiche chargée");
    expect(barChart([], "Length", { tr })).toContain("aucune donnée pour le moment");
  });
  it("escapes titles", () => {
    expect(barChart(series, "<i>x")).toContain("&lt;i&gt;x");
  });
});
