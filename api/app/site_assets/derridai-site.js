/* Copyright 2026 Aaron John Schlosser, PhD. */
(() => {
  "use strict";

  const root = document.getElementById("app");
  const publicationPackage = globalThis.__DERRIDAI_SITE_PACKAGE__;
  const sdk = globalThis.DerridAI;

  if (!root) return;
  if (!publicationPackage?.manifest || !Array.isArray(publicationPackage.chunks)) {
    root.textContent = "This DerridAI publication package is incomplete.";
    return;
  }
  if (!sdk?.createClient || !sdk?.dataSources?.inline) {
    root.textContent = "The DerridAI SDK could not be loaded.";
    return;
  }

  root.removeAttribute("role");
  root.removeAttribute("aria-live");

  const publication = publicationPackage.manifest;
  const publicationId = String(publication.publication_id || "publication");
  const localeKey = `derridai.site.locale.${publicationId}`;
  const availableLocales = Object.keys(publication.strings || {});
  const memoryStorage = new Map();
  let locale = readLocal(localeKey) || publication.locale || availableLocales[0] || "en-US";
  if (!availableLocales.includes(locale)) locale = availableLocales[0] || "en-US";
  let view = "search";
  let client = null;
  let capabilities = null;

  const style = document.createElement("style");
  style.textContent = `
    :root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light dark;
      --bg:Canvas;--fg:CanvasText;--muted:color-mix(in srgb,CanvasText 62%,transparent);--surface:color-mix(in srgb,Canvas 96%,CanvasText 4%);
      --raised:color-mix(in srgb,Canvas 92%,CanvasText 8%);--border:color-mix(in srgb,CanvasText 18%,transparent);--accent:LinkText;
      --danger:color-mix(in srgb,red 72%,CanvasText 28%);--shadow:0 12px 32px color-mix(in srgb,CanvasText 13%,transparent)}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);line-height:1.55}button,input,select,textarea{font:inherit;color:inherit}
    button{min-height:2.5rem;border:1px solid var(--border);border-radius:.55rem;background:var(--surface);padding:.45rem .8rem;cursor:pointer}
    button:hover{background:var(--raised)}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
    button.primary{background:var(--accent);color:Canvas;border-color:var(--accent)}button.danger{color:var(--danger)}button[disabled]{opacity:.55;cursor:not-allowed}
    .shell{min-height:100vh}.top{border-bottom:1px solid var(--border);background:var(--surface);position:sticky;top:0;z-index:5}
    .top-inner,.main{width:min(1180px,calc(100% - 2rem));margin:auto}.top-inner{display:flex;gap:1rem;align-items:center;padding:.8rem 0;flex-wrap:wrap}
    .brand{min-width:13rem;flex:1}.brand strong{display:block;font-size:1.05rem}.brand small,.muted,.meta{color:var(--muted)}
    nav{display:flex;gap:.4rem;flex-wrap:wrap}nav button[aria-current=page]{background:var(--raised);font-weight:700}
    .control{width:100%;min-height:2.5rem;border:1px solid var(--border);border-radius:.5rem;background:var(--bg);padding:.45rem .6rem}
    .main{padding:1.2rem 0 2.4rem}.hero{margin-bottom:1.2rem}.hero h1{margin:.15rem 0;font-size:clamp(1.45rem,3vw,2.25rem)}.hero p{max-width:70ch;color:var(--muted)}
    .panel,.card{border:1px solid var(--border);border-radius:.75rem;background:var(--surface);padding:1rem}.stack{display:grid;gap:.8rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.8rem}
    .search-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.6rem}.filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.7rem;margin-top:.8rem}
    .field{display:grid;gap:.3rem}.field>span{font-size:.8rem;font-weight:700;color:var(--muted)}.result{display:grid;gap:.5rem}
    .result-head{display:flex;gap:.7rem;justify-content:space-between;align-items:start}.score{font-variant-numeric:tabular-nums;color:var(--muted);font-size:.82rem}
    .snippet{white-space:pre-wrap}.chips{display:flex;flex-wrap:wrap;gap:.35rem}.chip{font-size:.75rem;padding:.15rem .45rem;border-radius:999px;background:var(--raised)}
    .status{min-height:1.5rem;color:var(--muted);margin:.6rem 0}.status.error{color:var(--danger)}.status.warning{font-weight:650}.empty{text-align:center;padding:2.3rem;color:var(--muted)}
    dialog{width:min(900px,calc(100% - 2rem));max-height:88vh;border:1px solid var(--border);border-radius:.9rem;background:var(--bg);color:var(--fg);box-shadow:var(--shadow);padding:0}
    dialog::backdrop{background:color-mix(in srgb,CanvasText 42%,transparent)}.dialog-head{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--border);padding:1rem;display:flex;justify-content:space-between;gap:1rem;align-items:start}
    .dialog-body{padding:1rem;display:grid;gap:1rem}.record-text{white-space:pre-wrap;font-family:Georgia,serif;font-size:1.04rem;line-height:1.7;border-block:1px solid var(--border);padding:1rem 0}
    .metadata{display:grid;grid-template-columns:minmax(9rem,auto) 1fr;gap:.35rem 1rem;font-size:.88rem}.metadata dt{font-weight:700}.metadata dd{margin:0;overflow-wrap:anywhere}
    textarea{min-height:6rem;resize:vertical}.annotation{border-left:3px solid var(--accent);padding:.7rem .9rem;background:var(--surface)}.annotation blockquote{margin:.35rem 0;font-family:Georgia,serif}
    .research-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(16rem,22rem);gap:1rem}.answer{white-space:pre-wrap;font-family:Georgia,serif;font-size:1.04rem}
    .evidence{display:grid;gap:.6rem}.evidence button{text-align:left;height:auto}.work-button{width:100%;text-align:left;height:100%;padding:1rem}.work-button h2{font-size:1.1rem}.count{font-size:1.6rem;font-weight:800}
    .footer{margin-top:3rem;border-top:1px solid var(--border);padding:1.2rem 0 2.5rem;color:var(--muted);font-size:.8rem}
    @media(max-width:760px){.research-layout{grid-template-columns:1fr}.search-row{grid-template-columns:1fr}.top{position:static}.top-inner,.main{width:min(100% - 1rem,1180px)}}
  `;
  document.head.appendChild(style);

  function readLocal(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return memoryStorage.get(key) || null;
    }
  }

  function writeLocal(key, value) {
    memoryStorage.set(key, String(value));
    try {
      localStorage.setItem(key, String(value));
    } catch {
      // Opaque file origins and privacy modes may disable localStorage.
    }
  }

  function t(key, vars = {}) {
    const dictionary = (publication.strings || {})[locale] || {};
    let value = String(dictionary[key] || key);
    for (const [name, replacement] of Object.entries(vars)) {
      value = value.replaceAll(`{${name}}`, String(replacement));
    }
    return value;
  }

  function node(tag, attrs = {}, ...children) {
    const element = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === "class") element.className = String(value);
      else if (key === "text") element.textContent = String(value);
      else if (key === "on") {
        for (const [event, handler] of Object.entries(value)) element.addEventListener(event, handler);
      } else if (key in element && !key.startsWith("aria")) {
        try {
          element[key] = value;
        } catch {
          element.setAttribute(key, String(value));
        }
      } else {
        element.setAttribute(key, value === true ? "" : String(value));
      }
    }
    for (const child of children.flat()) {
      if (child == null) continue;
      element.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return element;
  }

  function formatDate(value) {
    try {
      return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
    } catch {
      return String(value || "");
    }
  }

  function filterFields() {
    const excluded = new Set(["text", "record_id", "source_spans", "field_assertions", "updates"]);
    const declared = Array.isArray(publication.source_collection?.filter_fields)
      ? publication.source_collection.filter_fields
      : [];
    const common = [
      "document_author",
      "publication_year",
      "year",
      "language",
      "speaker",
      "position_holder",
      "stance",
      "discourse_role",
      "topics",
      "concepts",
      "persons",
    ];
    return [...new Set([...declared, ...common])]
      .map(String)
      .filter((key) => key && !excluded.has(key) && key !== "work")
      .sort((left, right) => left.localeCompare(right));
  }

  function localizedWarning(warning) {
    if (!warning) return "";
    if (warning.code === "semantic_unavailable") {
      return t("site.runtime.semantic_unavailable_keyword_fallback");
    }
    if (warning.code === "embedding_provider_unavailable") {
      return t("site.runtime.sdk_embedding_unavailable");
    }
    if (warning.code === "embedding_contract_mismatch") {
      return t("site.runtime.sdk_embedding_contract_mismatch");
    }
    if (warning.code === "embedding_dimension_mismatch") {
      return t("site.runtime.sdk_embedding_dimension_mismatch");
    }
    return String(warning.message || "");
  }

  function warningText(warnings) {
    return (warnings || []).map(localizedWarning).filter(Boolean).join(" ");
  }

  function progressListener(status) {
    return client.events.subscribe((event) => {
      if (event.type !== "load-progress") return;
      status.textContent = t("site.runtime.loading_progress", {
        stage:
          event.stage === "vectors"
            ? t("site.runtime.loading_vectors")
            : t("site.runtime.loading_records"),
        current: event.completed,
        total: event.total,
        work: event.work || "",
      });
    });
  }

  async function openRecord(record) {
    const dialog = node("dialog", { "aria-labelledby": "record-title" });
    const title = node("h2", {
      id: "record-title",
      text: record.work || record.record_id,
    });
    const close = node("button", {
      type: "button",
      text: t("site.runtime.close"),
      on: { click: () => dialog.close() },
    });
    const body = node("div", { class: "dialog-body" });
    body.append(
      node("div", { class: "meta", text: client.citations.format(record).plain }),
      node("div", {
        class: "record-text",
        text: record.text || "",
        tabindex: "0",
      }),
    );

    const metadata = node("dl", { class: "metadata" });
    for (const [key, value] of Object.entries(record).sort(([a], [b]) => a.localeCompare(b))) {
      if (["text", "field_assertions", "source_spans"].includes(key) || value == null || value === "") {
        continue;
      }
      if (typeof value === "object" && !Array.isArray(value)) continue;
      const rendered = Array.isArray(value)
        ? value.map((item) => (typeof item === "object" ? JSON.stringify(item) : String(item))).join(", ")
        : String(value);
      metadata.append(
        node("dt", { text: key.replaceAll("_", " ") }),
        node("dd", { text: rendered }),
      );
    }
    body.append(metadata);

    const quote = node("textarea", {
      class: "control",
      placeholder: t("site.runtime.quote_placeholder"),
      "aria-label": t("site.runtime.quotation"),
    });
    const note = node("textarea", {
      class: "control",
      placeholder: t("site.runtime.note_placeholder"),
      "aria-label": t("site.runtime.note"),
    });
    const tags = node("input", {
      class: "control",
      placeholder: t("site.runtime.tags_placeholder"),
      "aria-label": t("site.runtime.tags"),
    });
    const saved = node("span", { class: "status", role: "status" });
    const save = node("button", {
      class: "primary",
      type: "button",
      text: t("site.runtime.save_annotation"),
      on: {
        click: async () => {
          if (!String(quote.value).trim() && !String(note.value).trim() && !String(tags.value).trim()) {
            return;
          }
          await client.annotations.add({
            recordId: String(record.record_id),
            recordRevision:
              record.record_revision == null ? undefined : String(record.record_revision),
            work: record.work == null ? undefined : String(record.work),
            quote: quote.value,
            note: note.value,
            tags: String(tags.value)
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          });
          quote.value = "";
          note.value = "";
          tags.value = "";
          saved.textContent = t("site.runtime.annotation_saved");
        },
      },
    });
    body.append(
      node("h3", { text: t("site.runtime.add_annotation") }),
      quote,
      note,
      tags,
      save,
      saved,
    );

    dialog.append(node("div", { class: "dialog-head" }, title, close), body);
    dialog.addEventListener("close", () => dialog.remove());
    document.body.append(dialog);
    dialog.showModal();
  }

  function resultCard(item) {
    const record = item.record;
    const snippet = String(record.text || "").slice(0, 640);
    return node(
      "article",
      { class: "result card" },
      node(
        "div",
        { class: "result-head" },
        node(
          "div",
          {},
          node("strong", { text: record.work || record.record_id }),
          node("div", { class: "meta", text: client.citations.format(record).plain }),
        ),
        node("span", { class: "score", text: Number(item.score || 0).toFixed(3) }),
      ),
      node("div", { class: "snippet", text: snippet }),
      node("button", {
        type: "button",
        text: t("site.runtime.view_record"),
        on: { click: () => openRecord(record) },
      }),
    );
  }

  function searchView() {
    const panel = node("section", { class: "panel" });
    const query = node("input", {
      class: "control",
      placeholder: t("site.runtime.search_placeholder"),
      "aria-label": t("site.runtime.search"),
    });
    const submit = node("button", {
      class: "primary",
      type: "button",
      text: t("site.runtime.search"),
    });
    const mode = node(
      "select",
      { class: "control", "aria-label": t("site.runtime.search_mode") },
      node("option", { value: "keyword", text: t("site.runtime.keyword") }),
      node("option", {
        value: "semantic",
        text: t("site.runtime.semantic"),
        disabled: !capabilities.provider.embeddings,
      }),
      node("option", {
        value: "hybrid",
        text: t("site.runtime.hybrid"),
        disabled: !capabilities.provider.embeddings,
      }),
    );
    mode.value = capabilities.provider.embeddings ? "hybrid" : "keyword";
    const work = node(
      "select",
      { class: "control", "aria-label": t("site.runtime.work_filter") },
      node("option", { value: "", text: t("site.runtime.all_works") }),
      ...(publication.works || []).map((item) =>
        node("option", { value: item.work, text: item.work }),
      ),
    );
    const field = node(
      "select",
      { class: "control", "aria-label": t("site.runtime.field_filter") },
      node("option", { value: "", text: t("site.runtime.any_field") }),
      ...filterFields().map((key) =>
        node("option", { value: key, text: key.replaceAll("_", " ") }),
      ),
    );
    const value = node("input", {
      class: "control",
      placeholder: t("site.runtime.filter_value"),
      "aria-label": t("site.runtime.filter_value"),
    });
    const status = node("div", { class: "status", role: "status", "aria-live": "polite" });
    const results = node("div", { class: "stack" });

    async function run() {
      submit.disabled = true;
      status.className = "status";
      status.textContent = t("site.runtime.searching");
      results.replaceChildren();
      const stopProgress = progressListener(status);
      try {
        const filters = {};
        if (work.value) filters.work = work.value;
        if (field.value && value.value) filters[field.value] = value.value;
        const response = await client.search({
          query: query.value,
          mode: mode.value,
          filters,
          limit: 50,
        });
        const warning = warningText(response.warnings);
        status.className = warning ? "status warning" : "status";
        status.textContent = warning
          ? t("site.runtime.results_with_warning", {
              count: response.results.length,
              warning,
            })
          : t("site.runtime.results_count", { count: response.results.length });
        if (!response.results.length) {
          results.append(node("div", { class: "empty", text: t("site.runtime.no_results") }));
        } else {
          results.append(...response.results.map(resultCard));
        }
      } catch (error) {
        status.className = "status error";
        status.textContent = t("site.runtime.search_failed", {
          error: error instanceof Error ? error.message : String(error),
        });
      } finally {
        stopProgress();
        submit.disabled = false;
      }
    }

    submit.addEventListener("click", run);
    query.addEventListener("keydown", (event) => {
      if (event.key === "Enter") run();
    });

    panel.append(
      node("div", { class: "search-row" }, query, submit),
      node(
        "div",
        { class: "filters" },
        node("label", { class: "field" }, node("span", { text: t("site.runtime.search_mode") }), mode),
        node("label", { class: "field" }, node("span", { text: t("site.runtime.work_filter") }), work),
        node("label", { class: "field" }, node("span", { text: t("site.runtime.field_filter") }), field),
        node("label", { class: "field" }, node("span", { text: t("site.runtime.filter_value") }), value),
      ),
      status,
    );
    return node("div", { class: "stack" }, panel, results);
  }

  function worksView() {
    return node(
      "div",
      { class: "grid" },
      ...(publication.works || []).map((item) =>
        node(
          "button",
          {
            class: "work-button card",
            type: "button",
            on: {
              click: () => {
                view = "search";
                render().then(() => {
                  const selector = root.querySelector(
                    `[aria-label='${CSS.escape(t("site.runtime.work_filter"))}']`,
                  );
                  if (selector) selector.value = item.work;
                });
              },
            },
          },
          node("h2", { text: item.work }),
          node("div", { class: "meta", text: (item.authors || []).join(", ") }),
          node("div", { class: "count", text: Number(item.record_count || 0).toLocaleString(locale) }),
          node("div", { class: "muted", text: t("site.runtime.records") }),
        ),
      ),
    );
  }

  function researchView() {
    const question = node("textarea", {
      class: "control",
      placeholder: t("site.runtime.question_placeholder"),
      "aria-label": t("site.runtime.question"),
    });
    const ask = node("button", {
      class: "primary",
      type: "button",
      text: t("site.runtime.ask"),
    });
    const status = node("div", { class: "status", role: "status", "aria-live": "polite" });
    const answer = node("div", { class: "answer", "aria-live": "polite" });
    const evidence = node("div", { class: "evidence" });

    async function run() {
      const q = String(question.value || "").trim();
      if (!q) return;
      ask.disabled = true;
      status.className = "status";
      status.textContent = t("site.runtime.retrieving");
      answer.textContent = "";
      evidence.replaceChildren();
      const stopProgress = progressListener(status);
      try {
        const response = await client.research({
          question: q,
          retrieval: {
            mode: capabilities.provider.embeddings ? "hybrid" : "keyword",
            limit: 24,
            evidenceLimit: 10,
            mmrLambda: 0.72,
          },
        });
        for (const item of response.evidencePacket.evidence) {
          evidence.append(
            node(
              "button",
              {
                type: "button",
                on: {
                  click: async () => {
                    const record = await client.records.get(item.recordId);
                    if (record) openRecord(record);
                  },
                },
              },
              node("strong", { text: `[${item.evidenceId}] ${item.work || item.recordId}` }),
              node("small", { class: "muted", text: item.citation }),
            ),
          );
        }
        const retrievalWarning = warningText(response.retrieval.warnings);
        const generationWarning = response.warnings.some(
          (warning) => warning.code === "generation_unavailable",
        );
        if (response.answer) {
          answer.textContent = response.answer;
          status.className = retrievalWarning ? "status warning" : "status";
          status.textContent = retrievalWarning
            ? t("site.runtime.complete_with_warning", { warning: retrievalWarning })
            : t("site.runtime.complete");
        } else if (response.evidencePacket.evidence.length) {
          answer.textContent = t("site.runtime.generation_unavailable_evidence");
          status.className = "status warning";
          status.textContent = generationWarning
            ? t("site.runtime.sdk_generation_unavailable")
            : t("site.runtime.complete");
        } else {
          status.className = "status warning";
          status.textContent = t("site.runtime.no_evidence");
        }
      } catch (error) {
        status.className = "status error";
        status.textContent = t("site.runtime.research_failed", {
          error: error instanceof Error ? error.message : String(error),
        });
      } finally {
        stopProgress();
        ask.disabled = false;
      }
    }

    ask.addEventListener("click", run);
    return node(
      "div",
      { class: "research-layout" },
      node(
        "section",
        { class: "panel stack" },
        node("h2", { text: t("site.runtime.research") }),
        question,
        ask,
        status,
        answer,
      ),
      node(
        "aside",
        { class: "stack" },
        node("div", {
          class: "panel muted",
          text: capabilities.provider.generation
            ? t("site.runtime.sdk_host_generation_ready")
            : t("site.runtime.sdk_host_generation_missing"),
        }),
        node(
          "section",
          { class: "panel stack" },
          node("h3", { text: t("site.runtime.evidence") }),
          evidence,
        ),
      ),
    );
  }

  async function notesView() {
    const items = await client.annotations.list();
    if (!items.length) {
      return node("div", { class: "panel empty", text: t("site.runtime.no_annotations") });
    }
    return node(
      "div",
      { class: "stack" },
      ...items.map((item) => {
        const status = node("span", { class: "status", role: "status", "aria-live": "polite" });
        return node(
          "article",
          { class: "annotation" },
          node("strong", { text: item.work || item.record_id }),
          node("div", { class: "meta", text: formatDate(item.created_at) }),
          item.quote ? node("blockquote", { text: item.quote }) : null,
          item.note ? node("p", { text: item.note }) : null,
          node(
            "div",
            { class: "chips" },
            ...(item.tags || []).map((tag) => node("span", { class: "chip", text: tag })),
          ),
          node(
            "div",
            {},
            node("button", {
              type: "button",
              text: t("site.runtime.view_record"),
              on: {
                click: async () => {
                  try {
                    const record = await client.records.get(item.record_id);
                    if (record) openRecord(record);
                    else status.textContent = t("site.runtime.record_not_found");
                  } catch (error) {
                    status.textContent = t("site.runtime.record_load_failed", {
                      error: error instanceof Error ? error.message : String(error),
                    });
                  }
                },
              },
            }),
            node("button", {
              type: "button",
              class: "danger",
              text: t("site.runtime.delete"),
              on: {
                click: async () => {
                  await client.annotations.remove(item.id);
                  render();
                },
              },
            }),
          ),
          status,
        );
      }),
    );
  }

  function navButton(key, target) {
    return node("button", {
      type: "button",
      text: t(key),
      "aria-current": view === target ? "page" : null,
      on: {
        click: () => {
          view = target;
          render();
        },
      },
    });
  }

  async function render() {
    document.documentElement.lang = locale;
    const localeSelect = node(
      "select",
      {
        class: "control",
        "aria-label": t("site.runtime.language"),
        on: {
          change: (event) => {
            locale = event.target.value;
            writeLocal(localeKey, locale);
            render();
          },
        },
      },
      ...availableLocales.map((code) => node("option", { value: code, text: code })),
    );
    localeSelect.value = locale;

    const header = node(
      "header",
      { class: "top" },
      node(
        "div",
        { class: "top-inner" },
        node(
          "div",
          { class: "brand" },
          node("strong", { text: publication.title || t("site.runtime.site_title") }),
          node("small", { text: t("site.runtime.powered_by_sdk") }),
        ),
        node(
          "nav",
          { "aria-label": t("site.runtime.navigation") },
          navButton("site.runtime.search", "search"),
          navButton("site.runtime.works", "works"),
          navButton("site.runtime.research", "research"),
          navButton("site.runtime.annotations", "notes"),
        ),
        localeSelect,
      ),
    );

    const main = node("main", { class: "main" });
    main.append(
      node(
        "section",
        { class: "hero" },
        node("h1", { text: publication.title || t("site.runtime.site_title") }),
        publication.description ? node("p", { text: publication.description }) : null,
      ),
    );
    if (view === "search") main.append(searchView());
    else if (view === "works") main.append(worksView());
    else if (view === "research") main.append(researchView());
    else if (view === "notes") main.append(await notesView());

    const recordCount = (publication.works || []).reduce(
      (sum, item) => sum + Number(item.record_count || 0),
      0,
    );
    main.append(
      node(
        "footer",
        { class: "footer" },
        t("site.runtime.publication_summary", {
          works: (publication.works || []).length,
          records: recordCount,
          date: formatDate(publication.created_at),
        }),
      ),
    );
    root.replaceChildren(node("div", { class: "shell" }, header, main));
  }

  async function start() {
    const host = globalThis.__DERRIDAI_HOST_CAPABILITIES__ || {};
    client = await sdk.createClient({
      dataSource: sdk.dataSources.inline(publicationPackage),
      storage: host.storage,
      embeddings: host.embeddings,
      generation: host.generation,
      locale,
    });
    capabilities = await client.capabilities();
    await render();
  }

  start().catch((error) => {
    root.textContent = error instanceof Error ? error.message : String(error);
  });
})();
