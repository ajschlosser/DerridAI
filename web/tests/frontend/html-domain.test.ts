/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { esc, icon } from "../../src/domain/html";
import { FIELD_LABELS, TABLE_DEFAULTS, viewConfig } from "../../src/domain/runtimeConstants";

describe("legacy HTML helpers", () => {
  it("escapes markup characters", () => {
    expect(esc(`<a href="x" onclick='y'>&</a>`)).toBe(
      "&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;&lt;/a&gt;",
    );
    expect(esc(null)).toBe("");
    expect(esc(0)).toBe("0");
  });
  it("draws icons as decorative inline SVG", () => {
    expect(icon("search")).toBe(
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>',
    );
  });
  it("keeps the navigation and table tables intact", () => {
    expect(viewConfig.map((item) => item.id)).toEqual([
      "home",
      "list",
      "record",
      "works",
      "global",
      "annotations",
      "pdf",
      "compare",
      "vector",
      "rag",
      "faq",
      "responsecache",
      "providers",
      "config",
    ]);
    expect(TABLE_DEFAULTS.list).toEqual([
      "__db_status",
      "work",
      "page_start",
      "needs_review",
      "text",
    ]);
    expect(FIELD_LABELS.document_author).toBe("Document author");
  });
});
