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
  const themeKey = `derridai.site.theme.${publicationId}`;
  const contrastKey = `derridai.site.contrast.${publicationId}`;
  const tutorialKey = `derridai.site.tutorial.${publicationId}`;
  const providerKey = `derridai.site.provider.${publicationId}`;
  const availableLocales = Object.keys(publication.strings || {});
  const languageMetadata = Array.isArray(publication.languages) ? publication.languages : [];
  const providerProfiles = Array.isArray(publication.provider_profiles)
    ? publication.provider_profiles
    : [];
  const memoryStorage = new Map();

  let locale = readLocal(localeKey) || publication.locale || availableLocales[0] || "en-US";
  if (!availableLocales.includes(locale)) locale = availableLocales[0] || "en-US";
  let theme = readLocal(themeKey) === "dark" ? "dark" : "light";
  let highContrast = readLocal(contrastKey) === "high";
  let selectedProviderId = readLocal(providerKey) || providerProfiles[0]?.id || "";
  if (!providerProfiles.some((profile) => profile.id === selectedProviderId)) {
    selectedProviderId = providerProfiles[0]?.id || "";
  }
  let sessionApiKey = "";
  let view = "search";
  let client = null;
  let capabilities = null;

  const style = document.createElement("style");
  style.textContent = `
    :root{
      font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      color-scheme:light;
      --bg:#ffffff;--fg:#111827;--muted:#4b5563;--surface:#f8fafc;--raised:#e5e7eb;
      --border:#6b7280;--accent:#005ea8;--accent-text:#ffffff;--danger:#b42318;
      --success:#166534;--warning:#7c4a03;--shadow:0 12px 32px rgba(17,24,39,.18)
    }
    :root[data-theme="dark"]{
      color-scheme:dark;
      --bg:#111827;--fg:#f9fafb;--muted:#d1d5db;--surface:#1f2937;--raised:#374151;
      --border:#9ca3af;--accent:#8ecbff;--accent-text:#0b1725;--danger:#ffb4ab;
      --success:#9ee6b1;--warning:#ffd38a;--shadow:0 12px 32px rgba(0,0,0,.55)
    }
    :root[data-contrast="high"]{
      color-scheme:dark;
      --bg:#000000;--fg:#ffffff;--muted:#ffffff;--surface:#000000;--raised:#1a1a1a;
      --border:#ffffff;--accent:#ffdf00;--accent-text:#000000;--danger:#ff8a80;
      --success:#9cff9c;--warning:#ffe66d;--shadow:0 0 0 2px #ffffff
    }
    *{box-sizing:border-box}
    html{background:var(--bg);scroll-behavior:auto}
    body{margin:0;background:var(--bg);color:var(--fg);line-height:1.6;font-size:1rem}
    button,input,select,textarea{font:inherit;color:inherit}
    button,.control{min-height:2.75rem}
    button{border:1px solid var(--border);border-radius:.55rem;background:var(--surface);padding:.5rem .85rem;cursor:pointer}
    button:hover{background:var(--raised)}
    button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,a:focus-visible,summary:focus-visible{
      outline:3px solid var(--accent);outline-offset:3px
    }
    button.primary{background:var(--accent);color:var(--accent-text);border-color:var(--accent);font-weight:700}
    button.danger{color:var(--danger)}
    button[disabled]{opacity:.58;cursor:not-allowed}
    .skip-link{position:fixed;left:.75rem;top:.75rem;z-index:1000;transform:translateY(-180%);background:var(--accent);color:var(--accent-text);padding:.65rem .85rem;border-radius:.4rem;font-weight:700}
    .skip-link:focus{transform:none}
    .shell{min-height:100vh}
    .top{border-bottom:1px solid var(--border);background:var(--surface);position:sticky;top:0;z-index:5}
    .top-inner,.main{width:min(1180px,calc(100% - 2rem));margin:auto}
    .top-inner{display:flex;gap:.8rem;align-items:center;padding:.8rem 0;flex-wrap:wrap}
    .brand{min-width:13rem;flex:1}.brand strong{display:block;font-size:1.05rem}.brand small,.muted,.meta{color:var(--muted)}
    nav{display:flex;gap:.4rem;flex-wrap:wrap}
    nav button[aria-current="page"]{background:var(--raised);font-weight:800;border-width:2px}
    .header-controls{display:flex;gap:.45rem;align-items:end;flex-wrap:wrap}
    .compact-field{display:grid;gap:.18rem;min-width:8rem}.compact-field>span{font-size:.78rem;font-weight:800;color:var(--muted)}
    .control{width:100%;border:1px solid var(--border);border-radius:.5rem;background:var(--bg);padding:.5rem .65rem}
    .toggle{display:flex;align-items:center;gap:.45rem;min-height:2.75rem;padding:.35rem .55rem;border:1px solid var(--border);border-radius:.5rem;background:var(--bg);font-weight:700}
    .toggle input{width:1.1rem;height:1.1rem}
    .main{padding:1.2rem 0 2.4rem;scroll-margin-top:6rem}
    .hero{margin-bottom:1.2rem}.hero h1{margin:.15rem 0;font-size:clamp(1.45rem,3vw,2.25rem)}.hero p{max-width:70ch;color:var(--muted)}
    .panel,.card{border:1px solid var(--border);border-radius:.75rem;background:var(--surface);padding:1rem}
    .stack{display:grid;gap:.8rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.8rem}
    .search-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:.6rem}.filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.7rem;margin-top:.8rem}
    .field{display:grid;gap:.3rem}.field>span{font-size:.82rem;font-weight:800;color:var(--muted)}
    .result{display:grid;gap:.5rem}.result-head{display:flex;gap:.7rem;justify-content:space-between;align-items:start}
    .score{font-variant-numeric:tabular-nums;color:var(--muted);font-size:.875rem}.snippet{white-space:pre-wrap}
    .chips,.method-strip{display:flex;flex-wrap:wrap;gap:.4rem}.chip,.method-badge{font-size:.82rem;padding:.25rem .55rem;border-radius:999px;background:var(--raised);border:1px solid var(--border)}
    .method-strip{margin:.75rem 0}.method-badge[data-active="true"]{border-width:2px;font-weight:800}.method-badge[data-active="false"]{opacity:.72}
    .method-badge .state{margin-inline-start:.25rem;font-weight:700}
    .status{min-height:1.5rem;color:var(--muted);margin:.6rem 0}.status.error{color:var(--danger);font-weight:700}.status.warning{color:var(--warning);font-weight:700}.status.success{color:var(--success);font-weight:700}
    .empty{text-align:center;padding:2.3rem;color:var(--muted)}
    dialog{width:min(900px,calc(100% - 2rem));max-height:88vh;border:2px solid var(--border);border-radius:.9rem;background:var(--bg);color:var(--fg);box-shadow:var(--shadow);padding:0}
    dialog::backdrop{background:rgba(0,0,0,.65)}
    .dialog-head{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--border);padding:1rem;display:flex;justify-content:space-between;gap:1rem;align-items:start}
    .dialog-body{padding:1rem;display:grid;gap:1rem}.dialog-actions{display:flex;gap:.55rem;justify-content:flex-end;flex-wrap:wrap;padding:1rem;border-top:1px solid var(--border)}
    .record-text{white-space:pre-wrap;font-family:Georgia,serif;font-size:1.04rem;line-height:1.75;border-block:1px solid var(--border);padding:1rem 0}
    .metadata{display:grid;grid-template-columns:minmax(9rem,auto) 1fr;gap:.35rem 1rem;font-size:.9rem}.metadata dt{font-weight:800}.metadata dd{margin:0;overflow-wrap:anywhere}
    textarea{min-height:7rem;resize:vertical}.annotation{border-left:4px solid var(--accent);padding:.8rem 1rem;background:var(--surface)}.annotation blockquote{margin:.35rem 0;font-family:Georgia,serif}
    .research-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(18rem,24rem);gap:1rem}.answer{white-space:pre-wrap;font-family:Georgia,serif;font-size:1.04rem}
    .evidence{display:grid;gap:.6rem}.evidence button{text-align:left;height:auto}.work-button{width:100%;text-align:left;height:100%;padding:1rem}.work-button h2{font-size:1.1rem}.count{font-size:1.6rem;font-weight:800}
    .provider-panel{display:grid;gap:.7rem}.provider-summary{padding:.65rem;border:1px solid var(--border);border-radius:.5rem;background:var(--bg);overflow-wrap:anywhere}
    .tutorial-progress{font-weight:800;color:var(--muted)}.tutorial-copy{font-size:1.02rem;max-width:68ch}.tutorial-copy p{margin:.35rem 0 .9rem}
    .footer{margin-top:3rem;border-top:1px solid var(--border);padding:1.2rem 0 2.5rem;color:var(--muted);font-size:.875rem}
    .sr-only{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}
    @media(max-width:760px){.research-layout{grid-template-columns:1fr}.search-row{grid-template-columns:1fr}.top{position:static}.top-inner,.main{width:min(100% - 1rem,1180px)}.main{scroll-margin-top:1rem}.header-controls{width:100%}}
    @media(forced-colors:active){button,.control,.panel,.card,.method-badge,.toggle{forced-color-adjust:auto}.method-badge[data-active="true"]{outline:2px solid CanvasText}}
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

  function directionForLocale(code) {
    try {
      const script = new Intl.Locale(code).maximize().script || "";
      return new Set(["Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm", "Rohg", "Mand"]).has(script)
        ? "rtl"
        : "ltr";
    } catch {
      return "ltr";
    }
  }

  function applyAppearance() {
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.contrast = highContrast ? "high" : "normal";
    document.documentElement.lang = locale;
    document.documentElement.dir = directionForLocale(locale);
  }

  function formatDate(value) {
    try {
      return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
    } catch {
      return String(value || "");
    }
  }

  function languageLabel(code) {
    const metadata = languageMetadata.find((item) => item.code === code);
    return metadata ? `${metadata.flag || ""} ${metadata.name || code}`.trim() : code;
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

  function profileById(id) {
    return providerProfiles.find((profile) => String(profile.id) === String(id)) || null;
  }

  function providerBase(profile) {
    const raw = String(profile?.base_url || "").trim().replace(/\/$/, "");
    if (!raw) throw new Error(t("site.runtime.provider_endpoint_missing"));
    const parsed = new URL(raw);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new Error(t("site.runtime.provider_endpoint_invalid"));
    }
    return raw;
  }

  function providerHeaders(profile, apiKey) {
    const headers = { "Content-Type": "application/json" };
    if (profile?.type === "openai" && apiKey) headers.Authorization = `Bearer ${apiKey}`;
    return headers;
  }

  async function providerJson(url, init) {
    let response;
    try {
      response = await fetch(url, init);
    } catch {
      throw new Error(
        t("site.runtime.provider_browser_blocked", {
          origin: location.origin === "null" ? t("site.runtime.file_origin") : location.origin,
        }),
      );
    }
    const text = await response.text();
    let body = {};
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      body = {};
    }
    if (!response.ok) {
      throw new Error(
        String(body?.error?.message || body?.detail || text || `${response.status} ${response.statusText}`),
      );
    }
    return body;
  }

  function directEmbeddingProvider(profile, apiKey) {
    if (!profile) return undefined;
    const embeddingModel = String(publication.vector_index?.model || "").trim();
    if (!embeddingModel) return undefined;
    return {
      descriptor: () => ({
        id: profile.id,
        type: profile.type,
        model: embeddingModel,
      }),
      async embed(input, options = {}) {
        const base = providerBase(profile);
        if (profile.type === "ollama") {
          const body = await providerJson(`${base}/api/embed`, {
            method: "POST",
            headers: providerHeaders(profile, apiKey),
            body: JSON.stringify({ model: embeddingModel, input }),
            signal: options.signal,
          });
          const vectors = Array.isArray(body.embeddings) ? body.embeddings : [];
          return { vectors, provider: this.descriptor() };
        }
        const body = await providerJson(`${base}/embeddings`, {
          method: "POST",
          headers: providerHeaders(profile, apiKey),
          body: JSON.stringify({ model: embeddingModel, input }),
          signal: options.signal,
        });
        const vectors = Array.isArray(body.data)
          ? body.data.map((item) => item?.embedding).filter(Array.isArray)
          : [];
        return { vectors, provider: this.descriptor() };
      },
    };
  }

  function directGenerationProvider(profile, apiKey) {
    if (!profile) return undefined;
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    return {
      descriptor: () => ({ id: profile.id, type: profile.type, model }),
      async generate(request, options = {}) {
        const base = providerBase(profile);
        if (profile.type === "ollama") {
          const body = await providerJson(`${base}/api/chat`, {
            method: "POST",
            headers: providerHeaders(profile, apiKey),
            body: JSON.stringify({
              model,
              stream: false,
              messages: [{ role: "user", content: request.prompt }],
              options: { temperature: Number(profile.temperature ?? 0) },
            }),
            signal: options.signal,
          });
          return {
            text: String(body.message?.content || body.response || ""),
            provider: this.descriptor(),
          };
        }
        const body = await providerJson(`${base}/chat/completions`, {
          method: "POST",
          headers: providerHeaders(profile, apiKey),
          body: JSON.stringify({
            model,
            temperature: Number(profile.temperature ?? 0),
            messages: [{ role: "user", content: request.prompt }],
          }),
          signal: options.signal,
        });
        return {
          text: String(body.choices?.[0]?.message?.content || ""),
          provider: this.descriptor(),
        };
      },
    };
  }

  async function testProvider(profile, apiKey) {
    const base = providerBase(profile);
    const endpoint = profile.type === "ollama" ? `${base}/api/tags` : `${base}/models`;
    try {
      const body = await providerJson(endpoint, {
        method: "GET",
        headers: profile.type === "openai" && apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
        cache: "no-store",
      });
      const names = profile.type === "ollama"
        ? (body.models || []).flatMap((item) => [item?.name, item?.model]).filter(Boolean)
        : (body.data || []).map((item) => item?.id).filter(Boolean);
      const required = String(profile.model || "");
      if (required && names.length && !names.includes(required)) {
        return { ok: false, message: t("site.runtime.provider_model_missing", { model: required }) };
      }
      return { ok: true, message: t("site.runtime.provider_ready") };
    } catch (error) {
      return {
        ok: false,
        message: t("site.runtime.provider_test_failed", {
          error: error instanceof Error ? error.message : String(error),
        }),
      };
    }
  }

  async function rebuildClient() {
    const host = globalThis.__DERRIDAI_HOST_CAPABILITIES__ || {};
    const profile = profileById(selectedProviderId);
    const embeddings = profile
      ? directEmbeddingProvider(profile, sessionApiKey)
      : host.embeddings;
    const generation = profile
      ? directGenerationProvider(profile, sessionApiKey)
      : host.generation;
    client = await sdk.createClient({
      dataSource: sdk.dataSources.inline(publicationPackage),
      storage: host.storage,
      embeddings,
      generation,
      locale,
    });
    capabilities = await client.capabilities();
  }

  function methodBadge(labelKey, active) {
    return node(
      "span",
      { class: "method-badge", "data-active": active ? "true" : "false" },
      node("span", { text: t(labelKey) }),
      node("span", {
        class: "state",
        text: active ? t("site.runtime.method_on") : t("site.runtime.method_off"),
      }),
    );
  }

  function methodStrip(state) {
    const strip = node(
      "div",
      {
        class: "method-strip",
        role: "group",
        "aria-label": t("site.runtime.method_disclosure"),
      },
      methodBadge("site.runtime.method_text", Boolean(state.text)),
      methodBadge("site.runtime.method_vector", Boolean(state.vector)),
      methodBadge("site.runtime.method_llm", Boolean(state.llm)),
    );
    strip.update = (next) => {
      strip.replaceChildren(
        methodBadge("site.runtime.method_text", Boolean(next.text)),
        methodBadge("site.runtime.method_vector", Boolean(next.vector)),
        methodBadge("site.runtime.method_llm", Boolean(next.llm)),
      );
    };
    return strip;
  }

  function progressListener(status) {
    return client.events.subscribe((event) => {
      if (event.type === "embedding-start") {
        status.textContent = t("site.runtime.activity_vector_embedding");
        return;
      }
      if (event.type === "generation-start") {
        status.textContent = t("site.runtime.activity_llm_generation");
        return;
      }
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
    const dialog = node("dialog", {
      "aria-labelledby": "record-title",
      "aria-describedby": "record-citation",
    });
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
      node("div", {
        id: "record-citation",
        class: "meta",
        text: client.citations.format(record).plain,
      }),
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
    const saved = node("span", { class: "status", role: "status", "aria-live": "polite" });
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
          saved.className = "status success";
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
    close.focus();
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
    const panel = node("section", {
      class: "panel",
      "aria-labelledby": "search-heading",
    });
    const heading = node("h2", { id: "search-heading", text: t("site.runtime.search") });
    const query = node("input", {
      class: "control",
      type: "search",
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
    const methods = methodStrip({
      text: mode.value !== "semantic",
      vector: mode.value !== "keyword",
      llm: false,
    });
    mode.addEventListener("change", () => {
      methods.update({
        text: mode.value !== "semantic",
        vector: mode.value !== "keyword",
        llm: false,
      });
    });

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
    const results = node("div", { class: "stack", "aria-live": "polite" });

    async function run() {
      submit.disabled = true;
      status.className = "status";
      status.textContent =
        mode.value === "keyword"
          ? t("site.runtime.activity_text_search")
          : mode.value === "semantic"
            ? t("site.runtime.activity_vector_search")
            : t("site.runtime.activity_hybrid_search");
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
        methods.update({
          text: response.modeUsed !== "semantic",
          vector: response.modeUsed !== "keyword",
          llm: false,
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
      heading,
      methods,
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
      "section",
      { class: "grid", "aria-label": t("site.runtime.works") },
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

  function providerPanel() {
    const panel = node("section", {
      class: "panel provider-panel",
      "aria-labelledby": "provider-heading",
    });
    panel.append(node("h3", { id: "provider-heading", text: t("site.runtime.provider_settings") }));

    if (!providerProfiles.length) {
      panel.append(
        node("p", { class: "muted", text: t("site.runtime.no_exported_providers") }),
      );
      return panel;
    }

    const select = node(
      "select",
      { class: "control", "aria-label": t("site.runtime.provider_profile") },
      node("option", { value: "", text: t("site.runtime.provider_none") }),
      ...providerProfiles.map((profile) =>
        node("option", {
          value: profile.id,
          text: `${profile.name || profile.id} · ${profile.type === "openai" ? "OpenAI-compatible" : "Ollama"}`,
        }),
      ),
    );
    select.value = selectedProviderId;
    const key = node("input", {
      class: "control",
      type: "password",
      autocomplete: "off",
      value: sessionApiKey,
      placeholder: t("site.runtime.api_key_session"),
      "aria-label": t("site.runtime.api_key"),
      "aria-describedby": "provider-key-help",
    });
    const summary = node("div", { class: "provider-summary" });
    const status = node("div", { class: "status", role: "status", "aria-live": "polite" });

    function refreshSummary() {
      const profile = profileById(select.value);
      summary.replaceChildren(
        node("strong", {
          text: profile ? String(profile.name || profile.id) : t("site.runtime.provider_none"),
        }),
        node("div", {
          class: "meta",
          text: profile
            ? t("site.runtime.provider_summary", {
                type: profile.type === "openai" ? "OpenAI-compatible" : "Ollama",
                model: profile.model || t("site.runtime.not_configured"),
                endpoint: profile.base_url || t("site.runtime.not_configured"),
              })
            : t("site.runtime.provider_none_help"),
        }),
      );
    }
    refreshSummary();
    select.addEventListener("change", refreshSummary);

    const apply = node("button", {
      class: "primary",
      type: "button",
      text: t("site.runtime.apply_provider"),
      on: {
        click: async () => {
          selectedProviderId = select.value;
          sessionApiKey = key.value;
          writeLocal(providerKey, selectedProviderId);
          status.className = "status";
          status.textContent = t("site.runtime.provider_applying");
          try {
            await rebuildClient();
            status.className = "status success";
            status.textContent = t("site.runtime.provider_applied");
            await render();
          } catch (error) {
            status.className = "status error";
            status.textContent = t("site.runtime.provider_apply_failed", {
              error: error instanceof Error ? error.message : String(error),
            });
          }
        },
      },
    });

    const test = node("button", {
      type: "button",
      text: t("site.runtime.test_provider"),
      on: {
        click: async () => {
          const profile = profileById(select.value);
          if (!profile) {
            status.className = "status warning";
            status.textContent = t("site.runtime.provider_select_required");
            return;
          }
          status.className = "status";
          status.textContent = t("site.runtime.testing_provider");
          const result = await testProvider(profile, key.value);
          status.className = result.ok ? "status success" : "status error";
          status.textContent = result.message;
        },
      },
    });

    panel.append(
      node("label", { class: "field" }, node("span", { text: t("site.runtime.provider_profile") }), select),
      summary,
      node("label", { class: "field" }, node("span", { text: t("site.runtime.api_key") }), key),
      node("small", {
        id: "provider-key-help",
        class: "muted",
        text: t("site.runtime.api_key_help"),
      }),
      node("div", { class: "chips" }, apply, test),
      status,
    );
    return panel;
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
    const methods = methodStrip({
      text: true,
      vector: Boolean(capabilities.provider.embeddings),
      llm: Boolean(capabilities.provider.generation),
    });
    const status = node("div", { class: "status", role: "status", "aria-live": "polite" });
    const answer = node("div", { class: "answer", "aria-live": "polite" });
    const evidence = node("div", { class: "evidence" });

    async function run() {
      const q = String(question.value || "").trim();
      if (!q) return;
      ask.disabled = true;
      methods.update({
        text: true,
        vector: Boolean(capabilities.provider.embeddings),
        llm: Boolean(capabilities.provider.generation),
      });
      status.className = "status";
      status.textContent = capabilities.provider.embeddings
        ? t("site.runtime.activity_research_hybrid")
        : t("site.runtime.activity_research_text");
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
        methods.update({
          text: response.retrieval.modeUsed !== "semantic",
          vector: response.retrieval.modeUsed !== "keyword",
          llm: Boolean(response.generation),
        });
        const retrievalWarning = warningText(response.retrieval.warnings);
        const generationWarning = response.warnings.some(
          (warning) => warning.code === "generation_unavailable",
        );
        if (response.answer) {
          answer.textContent = response.answer;
          status.className = retrievalWarning ? "status warning" : "status success";
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
        { class: "panel stack", "aria-labelledby": "research-heading" },
        node("h2", { id: "research-heading", text: t("site.runtime.research") }),
        methods,
        question,
        ask,
        status,
        answer,
      ),
      node(
        "aside",
        { class: "stack", "aria-label": t("site.runtime.research_tools") },
        providerPanel(),
        node(
          "section",
          { class: "panel stack", "aria-labelledby": "evidence-heading" },
          node("h3", { id: "evidence-heading", text: t("site.runtime.evidence") }),
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
      "section",
      { class: "stack", "aria-label": t("site.runtime.annotations") },
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
            { class: "chips" },
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

  function tutorialSteps() {
    return [
      {
        title: t("site.runtime.tutorial_welcome_title"),
        body: t("site.runtime.tutorial_welcome_body"),
      },
      {
        title: t("site.runtime.tutorial_search_title"),
        body: t("site.runtime.tutorial_search_body"),
      },
      {
        title: t("site.runtime.tutorial_methods_title"),
        body: t("site.runtime.tutorial_methods_body"),
      },
      {
        title: t("site.runtime.tutorial_research_title"),
        body: t("site.runtime.tutorial_research_body"),
      },
      {
        title: t("site.runtime.tutorial_accessibility_title"),
        body: t("site.runtime.tutorial_accessibility_body"),
      },
    ];
  }

  function openTutorial() {
    const steps = tutorialSteps();
    let index = 0;
    const dialog = node("dialog", {
      "aria-labelledby": "tutorial-title",
      "aria-describedby": "tutorial-body",
    });
    const title = node("h2", { id: "tutorial-title" });
    const progress = node("div", { class: "tutorial-progress" });
    const body = node("div", { id: "tutorial-body", class: "tutorial-copy" });
    const previous = node("button", { type: "button", text: t("site.runtime.previous") });
    const next = node("button", { class: "primary", type: "button" });
    const skip = node("button", {
      type: "button",
      text: t("site.runtime.skip_tutorial"),
      on: {
        click: () => {
          writeLocal(tutorialKey, "skipped");
          dialog.close();
        },
      },
    });

    function paint() {
      const step = steps[index];
      title.textContent = step.title;
      progress.textContent = t("site.runtime.tutorial_progress", {
        current: index + 1,
        total: steps.length,
      });
      body.replaceChildren(node("p", { text: step.body }));
      previous.disabled = index === 0;
      next.textContent =
        index === steps.length - 1 ? t("site.runtime.finish") : t("site.runtime.next");
    }

    previous.addEventListener("click", () => {
      if (index > 0) index -= 1;
      paint();
      next.focus();
    });
    next.addEventListener("click", () => {
      if (index === steps.length - 1) {
        writeLocal(tutorialKey, "done");
        dialog.close();
        return;
      }
      index += 1;
      paint();
      next.focus();
    });

    dialog.append(
      node("div", { class: "dialog-head" }, title, progress),
      node("div", { class: "dialog-body" }, body),
      node("div", { class: "dialog-actions" }, skip, previous, next),
    );
    dialog.addEventListener("close", () => dialog.remove());
    document.body.append(dialog);
    paint();
    dialog.showModal();
    next.focus();
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

  function headerControls() {
    const languageSelect = node(
      "select",
      {
        class: "control",
        "aria-label": t("site.runtime.language"),
        on: {
          change: async (event) => {
            locale = event.target.value;
            writeLocal(localeKey, locale);
            await rebuildClient();
            await render();
          },
        },
      },
      ...availableLocales.map((code) =>
        node("option", { value: code, text: languageLabel(code) }),
      ),
    );
    languageSelect.value = locale;

    const themeSelect = node(
      "select",
      {
        class: "control",
        "aria-label": t("site.runtime.theme"),
        on: {
          change: (event) => {
            theme = event.target.value === "dark" ? "dark" : "light";
            writeLocal(themeKey, theme);
            applyAppearance();
          },
        },
      },
      node("option", { value: "light", text: t("site.runtime.theme_light") }),
      node("option", { value: "dark", text: t("site.runtime.theme_dark") }),
    );
    themeSelect.value = theme;

    const contrast = node(
      "label",
      { class: "toggle" },
      node("input", {
        type: "checkbox",
        checked: highContrast,
        on: {
          change: (event) => {
            highContrast = Boolean(event.target.checked);
            writeLocal(contrastKey, highContrast ? "high" : "normal");
            applyAppearance();
          },
        },
      }),
      node("span", { text: t("site.runtime.high_contrast") }),
    );

    return node(
      "div",
      { class: "header-controls", role: "group", "aria-label": t("site.runtime.display_controls") },
      node("label", { class: "compact-field" }, node("span", { text: t("site.runtime.language") }), languageSelect),
      node("label", { class: "compact-field" }, node("span", { text: t("site.runtime.theme") }), themeSelect),
      contrast,
      node("button", {
        type: "button",
        text: t("site.runtime.tutorial"),
        on: { click: openTutorial },
      }),
    );
  }

  async function render() {
    applyAppearance();

    const skip = node("a", {
      class: "skip-link",
      href: "#site-main",
      text: t("site.runtime.skip_to_content"),
    });

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
        headerControls(),
      ),
    );

    const main = node("main", { id: "site-main", class: "main", tabindex: "-1" });
    main.append(
      node(
        "section",
        { class: "hero", "aria-labelledby": "site-title" },
        node("h1", {
          id: "site-title",
          text: publication.title || t("site.runtime.site_title"),
        }),
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
    root.replaceChildren(node("div", { class: "shell" }, skip, header, main));
  }

  async function start() {
    applyAppearance();
    await rebuildClient();
    await render();
    if (!readLocal(tutorialKey)) {
      window.setTimeout(() => openTutorial(), 0);
    }
  }

  start().catch((error) => {
    root.textContent = error instanceof Error ? error.message : String(error);
  });
})();
