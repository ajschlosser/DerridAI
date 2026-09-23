/* Copyright 2026 Aaron John Schlosser, PhD. */
import { esc, icon } from "./html";
import { recordPayload } from "./recordPayloads";
import { snippet } from "./recordFormatting";
import { commonWorkValue } from "./workMetadata";
import { fullCitation, inlineCitation } from "./citations";
import { lineChart } from "./dashboardCharts";

// HTML/data presenters for records, works and dashboard insight panels. Moved verbatim from the legacy runtime;
// translation and the record helpers that still live in the runtime are passed in as dependencies.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  tr: (key: string, fallback?: string) => string;
  trf: (key: string, fallback: string, values?: Record<string, unknown>) => string;
  pages: (record: Loose) => string;
  recordDbStatus: (file: Loose, index: number, record: Loose) => Loose;
  allAnnotations: () => Loose[];
  compareSearchIndex: () => Loose[];
  label: (key: string) => string;
  display: (value: unknown) => string;
}

export function createRecordPresenters(deps: Deps) {
  const { tr, trf, pages, recordDbStatus, allAnnotations, compareSearchIndex, label, display } =
    deps;
  function uniqueWorkValues(rows: Loose[], field: string) {
    const values = new Map();
    for (const row of rows || []) {
      const value = row.record?.[field] ?? null;
      let token;
      try {
        token = JSON.stringify(value);
      } catch {
        token = String(value);
      }
      if (!values.has(token)) values.set(token, { value, count: 0, files: new Set(), records: [] });
      const entry = values.get(token);
      entry.count++;
      entry.files.add(row.file?.name || tr("works.unknown_source", "Unknown source"));
      if (entry.records.length < 3)
        entry.records.push(String(row.record?.record_id || row.index + 1));
    }
    return [...values.values()].sort(
      (a, b) =>
        b.count - a.count || String(display(a.value)).localeCompare(String(display(b.value))),
    );
  }
  function normalizedRecordAnnotation(item: Loose, index = 0, { removable = false } = {}) {
    return {
      id: item?.id || item?.shared_annotation_id || `annotation-${index}`,
      field: String(item?.field || "text"),
      quote: String(item?.quote || ""),
      note: String(item?.note || ""),
      tags: Array.isArray(item?.tags) ? item.tags.map(String) : [],
      author: String(
        item?.initiated_by || item?.author || tr("annotations.unknown_author", "Unknown author"),
      ),
      created_at: item?.created_at || null,
      removable: Boolean(removable),
      shared_annotation_id: item?.shared_annotation_id || null,
    };
  }
  function workInsightPieHtml(metric: Loose) {
    const total = metric.values.reduce(
      (sum: number, item: Loose) => sum + Number(item.value || 0),
      0,
    );
    if (!total)
      return `<p class="note">${esc(tr("works.no_indexed_values", "No populated metadata values yet."))}</p>`;
    const colors = [
      "var(--chart-1)",
      "var(--chart-2)",
      "var(--chart-3)",
      "var(--chart-4)",
      "var(--chart-5)",
      "var(--chart-6)",
    ];
    let cursor = 0;
    const stops = metric.values
      .map((item: Loose, index: number) => {
        const start = cursor;
        cursor += (Number(item.value || 0) / total) * 100;
        return `${colors[index % colors.length]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
      })
      .join(",");
    const legend = metric.values
      .map((item: Loose, index: number) => {
        const pct = (Number(item.value || 0) / total) * 100;
        return `<li>${item.other ? `<span class="work-insight-pie-label" aria-label="${esc(item.key)}"><i style="background:${colors[index % colors.length]}"></i><span>${esc(item.key)}</span></span>` : `<button type="button" data-work-insight-field="${esc(metric.field)}" data-work-insight-value="${esc(item.key)}"><i style="background:${colors[index % colors.length]}"></i><span>${esc(item.key)}</span></button>`}<b>${pct.toFixed(pct >= 10 ? 0 : 1)}%</b></li>`;
      })
      .join("");
    return `<div class="work-insight-pie-layout"><div class="work-insight-pie" style="background:conic-gradient(${stops})" role="img" aria-label="${esc(metric.title)}"></div><ol class="work-insight-pie-legend">${legend}</ol></div>`;
  }
  function flattenedMetricValues(value: unknown): string[] {
    if (Array.isArray(value)) return value.flatMap(flattenedMetricValues);
    if (value === undefined || value === null || value === "") return [];
    if (typeof value === "object") return Object.values(value).flatMap(flattenedMetricValues);
    return [String(value).trim()].filter(Boolean);
  }
  function topRecordFieldShare(rows: Loose[], field: string, limit = 5) {
    const counts = new Map();
    for (const row of rows || []) {
      const record = row.record || row;
      const value = record[field] ?? record.indexing?.[field] ?? record.metadata?.[field];
      for (const item of flattenedMetricValues(value))
        counts.set(item, (counts.get(item) || 0) + 1);
    }
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const top: Loose[] = sorted.slice(0, limit).map(([key, value]) => ({ key, value }));
    const other = sorted.slice(limit).reduce((sum, [, value]) => sum + Number(value || 0), 0);
    if (other) top.push({ key: tr("works.other_values", "Other"), value: other, other: true });
    return top;
  }
  function topRecordFieldValues(rows: Loose[], field: string, limit = 5) {
    const counts = new Map();
    for (const row of rows || []) {
      const record = row.record || row;
      const value = record[field] ?? record.indexing?.[field] ?? record.metadata?.[field];
      for (const item of flattenedMetricValues(value))
        counts.set(item, (counts.get(item) || 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, limit)
      .map(([key, value]) => ({ key, value }));
  }
  function workInsightMetrics(rows: Loose[], work: string) {
    return [
      {
        id: "persons",
        field: "persons",
        title: tr("dashboard.top_persons_work", "Top 5 persons mentioned in the work"),
        type: "bars",
        values: topRecordFieldValues(rows, "persons"),
      },
      {
        id: "concepts",
        field: "concepts",
        title: tr("dashboard.top_concepts_work", "Top 5 concepts mentioned in the work"),
        type: "bars",
        values: topRecordFieldValues(rows, "concepts"),
      },
      {
        id: "topics",
        field: "topics",
        title: tr("dashboard.top_topics_work", "Top 5 topics in the work"),
        type: "bars",
        values: topRecordFieldValues(rows, "topics"),
      },
      {
        id: "targets",
        field: "target",
        title: tr("dashboard.top_discourse_targets_work", "Top 5 discourse targets in the work"),
        type: "bars",
        values: topRecordFieldValues(rows, "target"),
      },
      {
        id: "roles",
        field: "discourse_role",
        title: tr(
          "dashboard.discourse_roles_share_work",
          "Top discourse roles as percentage of recorded roles",
        ),
        type: "pie",
        values: topRecordFieldShare(rows, "discourse_role"),
        valueLabel: tr("works.role_occurrences", "role occurrences"),
      },
    ].map((metric) => ({
      ...metric,
      work,
      format: (value: unknown) => Number(value).toLocaleString(),
    }));
  }
  function mixedWorkValueButton(rows: Loose[], field: string, { compact = false } = {}) {
    const count = uniqueWorkValues(rows, field).length;
    return `<button type="button" class="mixed-value-inspect ${compact ? "compact" : ""}" data-inspect-mixed-field="${esc(field)}" aria-label="${esc(trf("works.inspect_mixed_aria", "Inspect {count} unique values for {field}", { count, field: label(field) }))}"><span>${esc(tr("works.mixed", "Mixed"))}</span><b>${count}</b><small>${esc(tr("works.unique_values", "values"))}</small></button>`;
  }
  function workMetadataControl(field: string, rows: Loose[]) {
    const { mixed, value } = commonWorkValue(rows, field);
    const exemplar = rows
      .map((row) => row.record[field])
      .find((value) => value !== undefined && value !== null);
    const current = mixed ? "" : value;
    let control;
    if (typeof exemplar === "boolean" || field === "document_is_translation") {
      control = `<select class="control work-meta-value" data-work-meta-value="${esc(field)}"><option value="" ${mixed || current == null ? "selected" : ""}>${esc(mixed ? tr("works.mixed_leave_unchanged", "Mixed / leave unchanged") : tr("works.unset", "Unset"))}</option><option value="true" ${current === true ? "selected" : ""}>true</option><option value="false" ${current === false ? "selected" : ""}>false</option></select>`;
    } else if (Array.isArray(exemplar) || (exemplar && typeof exemplar === "object")) {
      control = `<textarea class="work-meta-value work-meta-json" data-work-meta-value="${esc(field)}" placeholder='${esc(mixed ? tr("works.mixed_values_json", "Mixed values — enter JSON to replace") : tr("works.json_value", "JSON value"))}'>${mixed ? "" : esc(JSON.stringify(current ?? [], null, 2))}</textarea>`;
    } else if (typeof exemplar === "number" || ["year", "publication_year"].includes(field)) {
      control = `<input class="control work-meta-value" data-work-meta-value="${esc(field)}" type="number" value="${mixed ? "" : esc(current ?? "")}" placeholder="${mixed ? esc(tr("works.mixed_values", "Mixed values")) : ""}">`;
    } else if (field === "full_citation" || field === "edition") {
      control = `<textarea class="work-meta-value" data-work-meta-value="${esc(field)}" placeholder="${mixed ? esc(tr("works.mixed_values", "Mixed values")) : ""}">${mixed ? "" : esc(current ?? "")}</textarea>`;
    } else {
      control = `<input class="control work-meta-value" data-work-meta-value="${esc(field)}" value="${mixed ? "" : esc(current ?? "")}" placeholder="${mixed ? esc(tr("works.mixed_values", "Mixed values")) : ""}">`;
    }
    return `<div class="work-meta-row"><label class="work-meta-apply"><input type="checkbox" data-work-meta-apply="${esc(field)}"><span>${esc(tr("ui.apply", "Apply"))}</span></label><div class="work-meta-field"><b>${esc(label(field))}</b>${mixed ? mixedWorkValueButton(rows, field, { compact: true }) : ""}</div>${control}</div>`;
  }
  function workInsightsPanelHtml(rows: Loose[], work: string) {
    const metrics = workInsightMetrics(rows, work);
    return `<section class="work-insights-panel" aria-label="${esc(tr("works.work_insights", "Work insights"))}"><div class="work-insights-heading"><div><span class="section-label">${esc(tr("works.work_insights", "Work insights"))}</span><h2>${esc(tr("works.indexed_patterns", "Metadata patterns in this work"))}</h2></div><p>${esc(tr("works.work_insights_help", "Counts come from populated metadata on the loaded records, not from the vector index. Empty cards mean this work has no usable values for that field yet."))}</p></div><div class="work-insights-grid">${metrics.map((metric) => `<article class="work-insight-card ${metric.type === "pie" ? "work-insight-card-pie" : ""}"><h3>${esc(metric.title)}</h3>${metric.type === "pie" ? workInsightPieHtml(metric) : `<ol>${metric.values.map((item) => `<li><button type="button" data-work-insight-field="${esc(metric.field)}" data-work-insight-value="${esc(item.key)}"><span>${esc(item.key)}</span><b>${Number(item.value).toLocaleString()}</b></button></li>`).join("") || `<li class="note">${esc(tr("works.no_indexed_values", "No populated metadata values yet."))}</li>`}</ol>`}</article>`).join("")}</div></section>`;
  }
  function dashboardPieChart(
    series: Loose[],
    title: string,
    { valueLabel = tr("dynamic.records", "records"), searchField = "" } = {},
  ) {
    const total = series.reduce((sum: number, item: Loose) => sum + Number(item.value || 0), 0);
    if (!total)
      return `<div class="dash-chart-empty">${esc(title)} · ${esc(tr("dashboard.no_data_yet", "no data yet"))}</div>`;
    let cursor = 0;
    const colors = [
      "var(--chart-1)",
      "var(--chart-2)",
      "var(--chart-3)",
      "var(--chart-4)",
      "var(--chart-5)",
      "var(--chart-6)",
      "var(--chart-7)",
      "var(--chart-8)",
    ];
    const stops = series
      .map((item: Loose, index: number) => {
        const start = cursor;
        cursor += (Number(item.value || 0) / total) * 100;
        return `${colors[index % colors.length]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
      })
      .join(",");
    return `<div class="dashboard-pie-layout"><div class="dashboard-pie" style="background:conic-gradient(${stops})" role="img" aria-label="${esc(title)}"></div><div class="dashboard-pie-legend">${series
      .map((item: Loose, index: number) => {
        const pct = (Number(item.value || 0) / total) * 100;
        const other =
          Boolean(item.other) || item.key === tr("dashboard.other_works", "Other works");
        const action = searchField
          ? `data-dashboard-search-field="${esc(searchField)}" data-dashboard-search-value="${esc(item.key)}"`
          : `data-dashboard-work="${esc(item.key)}"`;
        return `<button type="button" ${other ? "disabled" : action}><i style="background:${colors[index % colors.length]}"></i><span title="${esc(item.key)}">${esc(item.key)}</span><b>${pct.toFixed(pct >= 10 ? 0 : 1)}%</b><small>${Number(item.value || 0).toLocaleString()} ${esc(valueLabel)}</small></button>`;
      })
      .join("")}</div></div>`;
  }
  function pieShareSeries(items: Loose[], valueField: string, limit = 7) {
    const sorted = [...items]
      .map((item) => ({ key: item.work, value: Number(item[valueField] || 0) }))
      .filter((item) => item.value > 0)
      .sort((a, b) => b.value - a.value);
    const top = sorted.slice(0, limit),
      other = sorted.slice(limit).reduce((sum: number, item: Loose) => sum + item.value, 0);
    if (other) top.push({ key: tr("dashboard.other_works", "Other works"), value: other });
    return top;
  }
  function dashboardMetricBody(metric: Loose) {
    if (metric.type === "pie")
      return dashboardPieChart(metric.values, metric.title, {
        valueLabel: metric.valueLabel,
        searchField: metric.field || "",
      });
    if (metric.type === "line")
      return lineChart(metric.values, metric.title, metric.valueLabel || metric.title, { tr, trf });
    const ranking = metric.values,
      maxRank = Math.max(1, ...ranking.map((item: Loose) => Number(item.value) || 0));
    return `<div class="dashboard-average-list">${ranking.map((item: Loose) => `<button class="dashboard-average-row" ${metric.field ? `data-dashboard-search-field="${esc(metric.field)}" data-dashboard-search-value="${esc(item.key)}"` : `data-dashboard-work="${esc(item.key)}"`}><span>${esc(item.key)}</span><i><em style="width:${Math.max(4, Math.round((Number(item.value) / maxRank) * 100))}%"></em></i><b>${esc(metric.format(item.value))}</b></button>`).join("") || `<div class="note">${esc(metric.field ? tr("works.no_indexed_values", "No populated metadata values yet.") : tr("research.no_works", "No works loaded yet."))}</div>`}</div>`;
  }
  function worksBiblioValue(rows: Loose[], field: string) {
    const value = commonWorkValue(rows, field);
    return {
      field_label: label(field),
      mixed: Boolean(value.mixed),
      value: value.mixed
        ? ""
        : value.value == null || value.value === ""
          ? ""
          : String(value.value),
      unique_count: value.mixed ? uniqueWorkValues(rows, field).length : 0,
    };
  }
  function emptyWorksBiblio() {
    return { field_label: "", value: "", mixed: false, unique_count: 0 };
  }
  function describeResearcherWork(item: Loose, { selected = false } = {}) {
    const fields = [
      "document_author",
      "publisher",
      "publication_year",
      "edition",
      "translator",
      "publication_place",
      "isbn",
      "document_language",
      "original_language",
    ];
    return {
      work: String(item.work || ""),
      count: Number(item.count || 0),
      review: 0,
      annotations: selected
        ? allAnnotations().filter(
            (annotation) => String(annotation.work || "") === String(item.work),
          ).length
        : 0,
      files: [],
      authors: [],
      years: [],
      cover: String(item?.cover_url || ""),
      citation: String(item.full_citation || ""),
      year_label: "",
      subtitle: [item.document_author, item.publication_year || item.year, item.publisher]
        .filter(Boolean)
        .join(" · "),
      publisher: emptyWorksBiblio(),
      translator: emptyWorksBiblio(),
      metadata: selected
        ? fields
            .filter((field) => item[field])
            .map((field) => ({
              field,
              field_label: label(field),
              mixed: false,
              value: String(display(item[field])),
              unique_count: 0,
            }))
        : [],
      status: { kind: "", label: "" },
      insights: [],
    };
  }
  function pager(pg: Loose, total: number, prefix: string) {
    const range = total
      ? trf("ui.pager_range", "{start}–{end} of {total}", {
          start: pg.start + 1,
          end: pg.end,
          total,
        })
      : tr("ui.pager_no_results", "0 results");
    return `<div class="pagebar"><span>${esc(range)}</span><div class="inline">
  <button class="btn small" data-page="${prefix}:first" ${pg.page <= 1 ? "disabled" : ""}>${esc(tr("runtime.first", "First"))}</button>
  <button class="btn small" data-page="${prefix}:prev" ${pg.page <= 1 ? "disabled" : ""}>${esc(tr("ui.previous", "Previous"))}</button>
  <span>${esc(trf("dynamic.page_of_pages", "Page {page} / {pages}", { page: pg.page, pages: pg.pages }))}</span>
  <button class="btn small" data-page="${prefix}:next" ${pg.page >= pg.pages ? "disabled" : ""}>${esc(tr("ui.next", "Next"))}</button>
  <button class="btn small" data-page="${prefix}:last" ${pg.page >= pg.pages ? "disabled" : ""}>${esc(tr("runtime.last", "Last"))}</button></div></div>`;
  }
  function ragEvidencePreview(item: Loose, index: number) {
    const record = item.record || {};
    const metadata = [
      [label("record_id"), record.record_id],
      [label("work"), record.work],
      [tr("runtime.pages", "Pages"), pages(record)],
      [label("document_author"), record.document_author],
      [label("speaker"), record.speaker],
      [label("position_holder"), record.position_holder],
      [label("stance"), record.stance],
      [label("target"), record.target],
      [label("discourse_role"), record.discourse_role],
      [label("proposition_status"), record.proposition_status],
      [label("quoted_speaker"), record.quoted_speaker],
      [label("quoted_author"), record.quoted_author],
      [label("quoted_work"), record.quoted_work],
      [label("topics"), record.topics],
      [label("concepts"), record.concepts],
      [label("persons"), record.persons],
    ].filter(([, value]) => value !== undefined && value !== null && display(value) !== "—");
    const untitled = record.record_id || trf("dashboard.record_n", "Record {n}", { n: index + 1 });
    const copyLabel = record._researcher_text_policy
      ? tr("research.copy_summarized_record", "Copy summarized record")
      : tr("research.copy_record", "Copy record");
    return `<details class="rag-evidence-card" ${index < 3 ? "open" : ""}>
    <summary><span class="rag-evidence-id">[[${esc(item.evidence_id || `E${index}`)}]]</span><span class="rag-evidence-title"><b>${esc(untitled)}</b><small>${esc(record.work || item.collection || "")} · ${esc(item.inline_citation || pages(record))}</small></span><span class="rag-evidence-score">${item.rerank_score == null ? "" : Number(item.rerank_score).toFixed(3)}</span></summary>
    <div class="rag-evidence-body">
      <div class="rag-evidence-meta">${metadata.map(([name, value]) => `<div><span>${esc(name)}</span><b>${esc(display(value))}</b></div>`).join("")}</div>
      <div class="rag-evidence-source"><span>${esc(tr("research.collection", "Collection"))}</span><b>${esc(item.collection || "")}</b><span>${esc(tr("runtime.full_citation", "Full citation"))}</span><b>${esc(item.full_citation || "")}</b></div>
      ${record._researcher_text_policy ? `<div class="info researcher-evidence-policy">${esc(trf("research.evidence_policy", "Researcher view · Edmundson extractive summary · {count} source characters · topics, concepts, and persons used as bonus terms.", { count: Number(record._researcher_text_policy.source_chars || 0).toLocaleString() }))}</div>` : ""}
      <div class="tools"><button class="btn tiny" data-copy-rag-record="${index}">${icon("copy")}${esc(copyLabel)}</button></div>
      <pre>${esc(record.text || "")}</pre>
    </div>
  </details>`;
  }
  function storeCellHtml(record: Loose, key: string) {
    if (key === "_chroma_id")
      return `<td class="chroma-id-col"><div class="scroll-cell id" title="${esc(record._chroma_id || "")}">${esc(record._chroma_id || "")}</div></td>`;
    if (key === "page_start") return `<td>${esc(pages(record))}</td>`;
    if (key === "needs_review")
      return `<td>${record.needs_review ? `<span class="review">${esc(tr("runtime.review", "Review"))}</span>` : "—"}</td>`;
    if (key === "text") return `<td class="textcell">${esc(snippet(record.text, "", 240))}</td>`;
    if (key === "inline_citation")
      return `<td><div class="scroll-cell">${esc(inlineCitation(record))}</div></td>`;
    if (key === "full_citation")
      return `<td><div class="scroll-cell" title="${esc(fullCitation(record))}">${esc(fullCitation(record))}</div></td>`;
    const value = record[key];
    if (metadataSearchable(key, value))
      return `<td><button class="table-metadata-link scroll-cell" type="button" data-meta-search-field="${esc(key)}" data-meta-search-value="${esc(Array.isArray(value) ? value[0] : value)}" data-meta-search-contains="${Array.isArray(value)}" title="${esc(display(value))}">${esc(display(value))}</button></td>`;
    return `<td><div class="scroll-cell ${key === "record_id" ? "id" : ""}" title="${esc(display(value))}">${esc(display(value))}</div></td>`;
  }
  function recordsListCell(row: Loose, key: string, query: string) {
    const record = row.record;
    if (key === "__db_status") {
      const info = recordDbStatus(row.file, row.index, record);
      return {
        key,
        kind: "status",
        text: info.label,
        title: info.title || "",
        status_kind: info.kind,
      };
    }
    if (key === "page_start") return { key, kind: "pages", text: pages(record), title: "" };
    if (key === "needs_review")
      return {
        key,
        kind: "review",
        text: record.needs_review ? "yes" : "no",
        title: "",
      };
    if (key === "text") return { key, kind: "text", text: snippet(record.text, query), title: "" };
    if (key === "inline_citation")
      return { key, kind: "plain", text: inlineCitation(record), title: "" };
    if (key === "full_citation")
      return { key, kind: "plain", text: fullCitation(record), title: "" };
    if (key === "record_id") return { key, kind: "id", text: display(record[key]), title: "" };
    const value = record[key];
    return {
      key,
      kind: metadataSearchable(key, value) ? "metadata" : "plain",
      text: display(value),
      title: "",
      meta_value: Array.isArray(value) ? String(value[0] ?? "") : String(value ?? ""),
      meta_contains: Array.isArray(value),
    };
  }
  function metadataSearchable(field: string, value: unknown) {
    return (
      value !== undefined &&
      value !== null &&
      String(value).trim() !== "" &&
      !["text", "record_id", "inline_citation", "full_citation", "page_start", "page_end"].includes(
        field,
      )
    );
  }
  function searchRecordOptions(query: string, limit = 18) {
    const terms = String(query || "")
      .trim()
      .toLocaleLowerCase()
      .split(/\s+/)
      .filter(Boolean);
    const matches = [];
    for (const option of compareSearchIndex()) {
      if (terms.length && !terms.every((term) => option.search.includes(term))) continue;
      matches.push({ value: option.value, label: option.label });
      if (matches.length >= limit) break;
    }
    return matches;
  }
  function recordOptionLabel(file: Loose, record: Loose, index: number) {
    return `${file.name} · ${record.record_id || index + 1} · ${record.work || ""}`;
  }
  function ragGradeEvidencePayload(evidence = []) {
    return (Array.isArray(evidence) ? evidence : [])
      .slice(0, 40)
      .map((item: Loose, index: number) => ({
        evidence_id: item?.evidence_id || `E${index}`,
        inline_citation: item?.inline_citation || "",
        full_citation: item?.full_citation || "",
        collection: item?.collection || null,
        record: recordPayload(item?.record || {}, { fields: ["record_id", "work", "text"] }),
      }));
  }
  return {
    uniqueWorkValues,
    normalizedRecordAnnotation,
    workInsightPieHtml,
    flattenedMetricValues,
    topRecordFieldShare,
    topRecordFieldValues,
    workInsightMetrics,
    mixedWorkValueButton,
    workMetadataControl,
    workInsightsPanelHtml,
    dashboardPieChart,
    pieShareSeries,
    dashboardMetricBody,
    worksBiblioValue,
    emptyWorksBiblio,
    describeResearcherWork,
    pager,
    ragEvidencePreview,
    storeCellHtml,
    recordsListCell,
    metadataSearchable,
    searchRecordOptions,
    recordOptionLabel,
    ragGradeEvidencePayload,
  };
}