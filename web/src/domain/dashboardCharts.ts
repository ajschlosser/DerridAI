/* Copyright 2026 Aaron John Schlosser, PhD. */
import { esc } from "./html";

type Row = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Series = { key: string; label?: string; [extra: string]: any }; // eslint-disable-line @typescript-eslint/no-explicit-any

// SVG/HTML chart renderers for the dashboard, moved verbatim from the legacy runtime.

export function multiLineChart(
  rows: Row[],
  title: string,
  seriesDefs: Series[],
  { note = "" }: { note?: string } = {},
): string {
  if (!rows.length || !seriesDefs.length)
    return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  const width = 540,
    height = 185,
    left = 46,
    right = 14,
    top = 18,
    bottom = 28;
  const values = rows.flatMap((row) => seriesDefs.map((series) => Number(row[series.key]) || 0));
  const maxValue = Math.max(0, ...values);
  const scaleMax = Math.max(1, maxValue);
  const plotWidth = width - left - right,
    plotHeight = height - top - bottom;
  const xFor = (index: number) =>
    rows.length === 1 ? left + plotWidth / 2 : left + (index / (rows.length - 1)) * plotWidth;
  const yFor = (value: unknown) => top + plotHeight - (Number(value || 0) / scaleMax) * plotHeight;
  const grades = [0, 0.25, 0.5, 0.75, 1]
    .map((fraction) => {
      const value = Math.round(scaleMax * fraction);
      const y = top + plotHeight - fraction * plotHeight;
      return `<g class="chart-grade"><line x1="${left}" x2="${width - right}" y1="${y}" y2="${y}"/><text x="${left - 7}" y="${y + 3}" text-anchor="end">${value}</text></g>`;
    })
    .join("");
  const paths = seriesDefs
    .map((series, seriesIndex) => {
      const points = rows.map((row, index) => ({
        x: xFor(index),
        y: yFor(row[series.key]),
        value: Number(row[series.key]) || 0,
        key: row.key,
      }));
      const d = points
        .map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`)
        .join(" ");
      return `<path class="chart-line chart-series-${seriesIndex}" d="${d}"/>${points.map((point) => `<circle class="chart-dot chart-series-${seriesIndex}" data-chart-tip="${esc(`${series.label} · ${point.key}: ${point.value.toLocaleString()}`)}" cx="${point.x}" cy="${point.y}" r="3"><title>${esc(series.label)} · ${esc(point.key)}: ${point.value.toLocaleString()}</title></circle>`).join("")}`;
    })
    .join("");
  const mid = rows[Math.floor((rows.length - 1) / 2)]?.key || "";
  return `<div class="dash-chart multi-line-chart">
    <div class="dash-chart-head"><div><div class="dash-chart-title">${esc(title)}</div>${note ? `<div class="dash-chart-note">${esc(note)}</div>` : ""}</div><div class="chart-legend multi-chart-legend">${seriesDefs.map((series, index) => `<span title="${esc(series.label)}"><i class="chart-series-${index}"></i>${esc(series.short_label || series.label)}</span>`).join("")}</div></div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}">
      ${grades}
      <path class="chart-axis" d="M${left},${top + plotHeight} H${width - right}"/>
      ${paths}
    </svg>
    <div class="dash-chart-foot"><span>${esc(rows[0]?.key || "")}</span><span>${esc(mid)}</span><span>${esc(rows[rows.length - 1]?.key || "")}</span></div>
  </div>`;
}

export function lineChart(series: Row[], title: string, legendLabel: string = title): string {
  if (!series.length) return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  const width = 540,
    height = 185,
    left = 46,
    right = 14,
    top = 18,
    bottom = 28;
  const maxValue = Math.max(0, ...series.map((item) => Number(item.value) || 0));
  const scaleMax = Math.max(1, maxValue);
  const plotWidth = width - left - right,
    plotHeight = height - top - bottom;
  const points = series.map((item, index) => {
    const x =
      series.length === 1 ? left + plotWidth / 2 : left + (index / (series.length - 1)) * plotWidth;
    const y = top + plotHeight - (Number(item.value || 0) / scaleMax) * plotHeight;
    return { x, y, ...item } as { x: number; y: number; key: string; value: number };
  });
  const path = points
    .map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`)
    .join(" ");
  const grades = [0, 0.25, 0.5, 0.75, 1]
    .map((fraction) => {
      const value = Math.round(scaleMax * fraction);
      const y = top + plotHeight - fraction * plotHeight;
      return `<g class="chart-grade"><line x1="${left}" x2="${width - right}" y1="${y}" y2="${y}"/><text x="${left - 7}" y="${y + 3}" text-anchor="end">${value}</text></g>`;
    })
    .join("");
  const mid = series[Math.floor((series.length - 1) / 2)]?.key || "";
  return `<div class="dash-chart">
    <div class="dash-chart-head"><div class="dash-chart-title">${esc(title)}</div><div class="chart-legend"><i></i><span>${esc(legendLabel)}</span></div></div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}">
      ${grades}
      <path class="chart-axis" d="M${left},${top + plotHeight} H${width - right}"/>
      <path class="chart-line" d="${path}"/>
      ${points.map((point) => `<circle class="chart-dot" data-chart-tip="${esc(`${legendLabel} · ${point.key}: ${Number(point.value || 0).toLocaleString()}`)}" cx="${point.x}" cy="${point.y}" r="3"><title>${esc(point.key)}: ${Number(point.value || 0).toLocaleString()}</title></circle>`).join("")}
    </svg>
    <div class="dash-chart-foot"><span>${esc(series[0]?.key || "")}</span><span>${esc(mid)}</span><span>${esc(series[series.length - 1]?.key || "")}</span></div>
  </div>`;
}

export function pieChart(title: string, entries: Array<[string, number]>): string {
  const total = entries.reduce((sum, [, value]) => sum + Number(value || 0), 0);
  if (!total) return `<div class="dash-chart-empty">${esc(title)} · no records loaded</div>`;
  const cx = 90,
    cy = 90,
    r = 64,
    circ = 2 * Math.PI * r;
  let offset = 0;
  const slices = entries
    .map(([name, value], index) => {
      const fraction = Number(value || 0) / total;
      const dash = fraction * circ;
      const gap = Math.max(0, circ - dash);
      const current = offset;
      offset += dash;
      return `<circle class="pie-slice pie-series-${index % 10}" data-chart-tip="${esc(`${name} · ${Number(value).toLocaleString()} records · ${(fraction * 100).toFixed(1)}%`)}" cx="${cx}" cy="${cy}" r="${r}" pathLength="${circ}" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-current}" transform="rotate(-90 ${cx} ${cy})"><title>${esc(name)}: ${Number(value).toLocaleString()} (${(fraction * 100).toFixed(1)}%)</title></circle>`;
    })
    .join("");
  return `<div class="dash-chart pie-chart"><div class="dash-chart-head"><div class="dash-chart-title">${esc(title)}</div></div><div class="pie-layout"><svg viewBox="0 0 180 180" role="img" aria-label="${esc(title)}"><circle class="pie-track" cx="${cx}" cy="${cy}" r="${r}"/>${slices}<text class="pie-total" x="${cx}" y="${cy - 2}" text-anchor="middle">${total.toLocaleString()}</text><text class="pie-total-label" x="${cx}" y="${cy + 15}" text-anchor="middle">records</text></svg><div class="pie-legend">${entries.map(([name, value], index) => `<div title="${esc(name)}"><i class="pie-series-${index % 10}"></i><span>${esc(name)}</span><b>${((Number(value) / total) * 100).toFixed(1)}%</b><small>${Number(value).toLocaleString()}</small></div>`).join("")}</div></div></div>`;
}

export function barChart(
  series: Row[],
  title: string,
  { valueLabel = "Average characters" }: { valueLabel?: string } = {},
): string {
  if (!series.length) return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  const max = Math.max(1, ...series.map((item) => Number(item.value) || 0));
  return `<section class="dash-chart dash-bar-chart"><div class="dash-chart-head"><div class="dash-chart-title">${esc(title)}</div><div class="chart-legend"><i></i><span>${esc(valueLabel)}</span></div></div><div class="dash-bars">${series
    .map((item) => {
      const pct = Math.max(2, Math.round((Number(item.value || 0) / max) * 100));
      return `<div class="dash-bar-row" data-chart-tip="${esc(`${item.key} · ${Number(item.value || 0).toLocaleString()} ${valueLabel.toLowerCase()} · ${Number(item.count || 0).toLocaleString()} records`)}"><div class="dash-bar-label" title="${esc(item.key)}"><b>${esc(item.key)}</b><span>${Number(item.count || 0).toLocaleString()} records</span></div><div class="dash-bar-track"><i style="width:${pct}%"></i></div><strong>${Number(item.value || 0).toLocaleString()}</strong></div>`;
    })
    .join("")}</div></section>`;
}

export function statList(title: string, items: Array<[string, number]>): string {
  return `<section class="card dash-ranking"><div class="cardhead"><b>${esc(title)}</b></div><div>${items.map(([value, count], index) => `<button class="rank-row" type="button" data-dashboard-search="${esc(value)}" title="Search the corpus for ${esc(value)}"><span>${index + 1}</span><b>${esc(value)}</b><strong>${count.toLocaleString()}</strong></button>`).join("") || '<div class="note" style="padding:12px">No data</div>'}</div></section>`;
}
