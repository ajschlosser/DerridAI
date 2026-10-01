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
  const legacyProviderKey = `derridai.site.provider.${publicationId}`;
  const embeddingSelectionKey = `derridai.site.provider.embedding.${publicationId}`;
  const generationSelectionKey = `derridai.site.provider.generation.${publicationId}`;
  const providersKey = `derridai.site.providers.${publicationId}`;
  const availableLocales = Object.keys(publication.strings || {});
  const languageMetadata = Array.isArray(publication.languages) ? publication.languages : [];
  const memoryStorage = new Map();

  let locale = readLocal(localeKey) || publication.locale || availableLocales[0] || "en-US";
  if (!availableLocales.includes(locale)) locale = availableLocales[0] || "en-US";
  let theme = readLocal(themeKey) === "dark" ? "dark" : "light";
  let highContrast = readLocal(contrastKey) === "high";
  const PROVIDER_ENGINES = ["ollama", "openai", "transformers"];
  // Suggestions only: small ONNX models that run in the browser. The reader chooses and may type any model id.
  const TRANSFORMERS_SUGGESTIONS = [
    { id: "Xenova/all-MiniLM-L6-v2", note: "site.runtime.transformers_model_english_small" },
    { id: "Xenova/multilingual-e5-small", note: "site.runtime.transformers_model_multilingual_small" },
  ];

  // Providers are configured by the reader in this browser; nothing about them is part of the publication.
  // Profiles saved by earlier versions had a single `type` (ollama|openai) and served Research generation.
  function normalizeProfile(raw) {
    if (!raw || typeof raw !== "object" || !raw.id || !raw.name || !raw.model) return null;
    const engine = raw.engine || raw.type;
    if (!PROVIDER_ENGINES.includes(engine)) return null;
    const role = raw.role === "embedding" || raw.role === "generation" ? raw.role : "generation";
    if (engine === "transformers" && role !== "embedding") return null;
    if (engine !== "transformers" && !raw.base_url) return null;
    return {
      id: String(raw.id),
      name: String(raw.name),
      role,
      engine,
      base_url: String(raw.base_url || ""),
      model: String(raw.model),
      model_source: raw.model_source === "local" ? "local" : "hub",
      query_prefix: String(raw.query_prefix || ""),
      document_prefix: String(raw.document_prefix || ""),
      temperature: Number(raw.temperature ?? 0),
      remember_key: Boolean(raw.remember_key ?? raw.api_key),
      api_key: String(raw.api_key || ""),
    };
  }

  function loadProviderProfiles() {
    try {
      const value = JSON.parse(readLocal(providersKey) || "[]");
      return Array.isArray(value) ? value.map(normalizeProfile).filter(Boolean) : [];
    } catch {
      return [];
    }
  }

  let providerProfiles = loadProviderProfiles();
  const sessionApiKeys = new Map();
  providerProfiles.forEach((profile) => {
    if (profile.remember_key && profile.api_key) sessionApiKeys.set(profile.id, profile.api_key);
  });
  function profileOfRole(id, role) {
    return providerProfiles.find((profile) => profile.id === id && profile.role === role)
      ? id
      : "";
  }
  let selectedEmbeddingId = profileOfRole(readLocal(embeddingSelectionKey) || "", "embedding");
  let selectedGenerationId = profileOfRole(
    readLocal(generationSelectionKey) || readLocal(legacyProviderKey) || "",
    "generation",
  );
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
      --success:#166534;--warning:#7c4a03;--mark-bg:#fde68a;--mark-fg:#111827;--shadow:0 12px 32px rgba(17,24,39,.18)
    }
    :root[data-theme="dark"]{
      color-scheme:dark;
      --bg:#111827;--fg:#f9fafb;--muted:#d1d5db;--surface:#1f2937;--raised:#374151;
      --border:#9ca3af;--accent:#8ecbff;--accent-text:#0b1725;--danger:#ffb4ab;
      --success:#9ee6b1;--warning:#ffd38a;--mark-bg:#facc15;--mark-fg:#111827;--shadow:0 12px 32px rgba(0,0,0,.55)
    }
    :root[data-contrast="high"]{
      color-scheme:dark;
      --bg:#000000;--fg:#ffffff;--muted:#ffffff;--surface:#000000;--raised:#1a1a1a;
      --border:#ffffff;--accent:#ffdf00;--accent-text:#000000;--danger:#ff8a80;
      --success:#9cff9c;--warning:#ffe66d;--mark-bg:#ffdf00;--mark-fg:#000000;--shadow:0 0 0 2px #ffffff
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
    mark{background:var(--mark-bg);color:var(--mark-fg);border-radius:.2em;padding:0 .12em;font-weight:700;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:.15em}
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
    .evidence{display:grid;gap:.6rem}.evidence button{text-align:left;height:auto}.work-button{width:100%;text-align:left;height:100%;padding:1rem}.work-title{display:block;font-size:1.1rem;font-weight:800}.count{font-size:1.6rem;font-weight:800}
    .provider-panel{display:grid;gap:.7rem}.provider-form{display:grid;gap:.7rem;padding-top:.8rem;border-top:1px solid var(--border)}.provider-summary{padding:.65rem;border:1px solid var(--border);border-radius:.5rem;background:var(--bg);overflow-wrap:anywhere}
    .provider-command{display:block;margin-top:.5rem;overflow:auto;padding:.5rem;border:1px solid var(--border);border-radius:.4rem;background:var(--raised);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem;white-space:pre}
    .tutorial-progress{font-weight:800;color:var(--muted)}.tutorial-copy{font-size:1.02rem;max-width:68ch}.tutorial-copy p{margin:.35rem 0 .9rem}
    [data-tour]{scroll-margin:6rem 0 1rem}
    dialog.tour{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;border:0;border-radius:0;background:transparent;box-shadow:none;overflow:hidden}
    dialog.tour::backdrop{background:transparent}
    dialog.tour.tour-centered{background:rgba(0,0,0,.72)}
    .tour-spot{position:fixed;border-radius:.65rem;outline:3px solid var(--accent);box-shadow:0 0 0 200vmax rgba(0,0,0,.72);pointer-events:none}
    .tour-centered .tour-spot{display:none}
    @media(prefers-reduced-motion:no-preference){.tour-spot{transition:left .2s,top .2s,width .2s,height .2s}}
    .tour-card{position:fixed;width:min(26rem,calc(100% - 1rem));max-height:calc(100% - 1rem);overflow:auto;background:var(--bg);color:var(--fg);border:2px solid var(--border);border-radius:.9rem;box-shadow:var(--shadow)}
    .tour-centered .tour-card{top:50%;left:50%;transform:translate(-50%,-50%)}
    .tour-dock .tour-card{left:.5rem;right:.5rem;bottom:.5rem;top:auto;width:auto}
    .tour-dock-top .tour-card{left:.5rem;right:.5rem;top:.5rem;bottom:auto;width:auto}
    .tour-card .dialog-head{position:static;flex-direction:column;gap:.15rem}.tour-card h2{margin:0;font-size:1.15rem}
    .tour-bar{height:.3rem;background:var(--raised)}.tour-bar span{display:block;height:100%;background:var(--accent)}
    .tour-hint{padding-block:0;font-size:.875rem}
    .tutorial-progress{font-weight:800;color:var(--muted);font-size:.875rem}.tutorial-copy{margin:0;font-size:1.02rem}
    .footer{margin-top:3rem;border-top:1px solid var(--border);padding:1.2rem 0 2.5rem;color:var(--muted);font-size:.875rem}
    [hidden]{display:none!important}progress{width:100%;height:1rem;accent-color:var(--accent)}
    .sr-only{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}
    @media(max-width:760px){.research-layout{grid-template-columns:1fr}.search-row{grid-template-columns:1fr}.top{position:static}.top-inner,.main{width:min(100% - 1rem,1180px)}.main{scroll-margin-top:1rem}.header-controls{width:100%}}
    @media(forced-colors:active){.tour-spot{outline:4px solid Highlight}mark{background:Mark;color:MarkText;forced-color-adjust:none}button,.control,.panel,.card,.method-badge,.toggle{forced-color-adjust:auto}.method-badge[data-active="true"]{outline:2px solid CanvasText}}
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

  function saveProviderProfiles() {
    // A key is written to this browser only when the reader chose to remember it for that provider.
    writeLocal(
      providersKey,
      JSON.stringify(
        providerProfiles.map((profile) => ({
          ...profile,
          api_key: profile.remember_key ? sessionApiKeys.get(profile.id) || "" : "",
        })),
      ),
    );
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
    document.title = publication.title || t("site.runtime.site_title");
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
    if (warning.code === "local_index_required") {
      return t("site.runtime.local_index_required", {
        indexed: warning.details?.indexed ?? 0,
        total: warning.details?.total ?? 0,
      });
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

  function providerError(message, code, status = 0) {
    const error = new Error(message);
    error.code = code;
    error.status = status;
    return error;
  }

  function isLoopbackHost(hostname) {
    return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(
      String(hostname || "").toLocaleLowerCase(),
    );
  }

  function providerBase(profile) {
    const raw = String(profile?.base_url || "").trim().replace(/\/$/, "");
    if (!raw) {
      throw providerError(
        t("site.runtime.provider_endpoint_missing"),
        "invalid_endpoint",
      );
    }
    let parsed;
    try {
      parsed = new URL(raw);
    } catch {
      throw providerError(
        t("site.runtime.provider_endpoint_invalid"),
        "invalid_endpoint",
      );
    }
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw providerError(
        t("site.runtime.provider_endpoint_invalid"),
        "invalid_endpoint",
      );
    }
    if (
      location.protocol === "https:" &&
      parsed.protocol === "http:" &&
      !isLoopbackHost(parsed.hostname)
    ) {
      throw providerError(
        t("site.runtime.provider_mixed_content", { endpoint: parsed.origin }),
        "mixed_content",
      );
    }
    return raw;
  }

  function providerHeaders(profile, apiKey) {
    const headers = { "Content-Type": "application/json" };
    if (profile?.engine === "openai" && apiKey) headers.Authorization = `Bearer ${apiKey}`;
    return headers;
  }

  async function providerJson(url, init) {
    let response;
    try {
      response = await fetch(url, init);
    } catch {
      throw providerError(
        t("site.runtime.provider_browser_blocked", {
          endpoint: url,
          origin: location.origin === "null" ? t("site.runtime.file_origin") : location.origin,
        }),
        "network",
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
      const code =
        response.status === 401 || response.status === 403
          ? "authentication"
          : response.status === 404
            ? "not_found"
            : "provider_error";
      throw providerError(
        String(
          body?.error?.message ||
            body?.detail ||
            text ||
            `${response.status} ${response.statusText}`,
        ),
        code,
        response.status,
      );
    }
    return body;
  }

  async function noCorsReachabilityProbe(url) {
    try {
      await fetch(url, { method: "GET", mode: "no-cors", cache: "no-store" });
      return true;
    } catch {
      return false;
    }
  }

  function embeddingVariant(profile) {
    return [
      profile.query_prefix ? `query-prefix=${profile.query_prefix}` : "",
      profile.document_prefix ? `document-prefix=${profile.document_prefix}` : "",
    ]
      .filter(Boolean)
      .join(";");
  }

  function prefixed(profile, input, purpose) {
    const prefix = purpose === "query" ? profile.query_prefix : profile.document_prefix;
    return prefix ? input.map((text) => `${prefix}${text}`) : input;
  }

  function embeddingFailure() {
    return providerError(t("site.runtime.embedding_failed"), "embedding_failed");
  }

  function directEmbeddingProvider(profile, apiKey) {
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    return {
      descriptor: () => ({
        id: profile.id,
        type: profile.engine,
        model,
        variant: embeddingVariant(profile),
      }),
      async embed(input, options = {}) {
        const base = providerBase(profile);
        const texts = prefixed(profile, input, options.purpose);
        let vectors;
        if (profile.engine === "ollama") {
          const body = await providerJson(`${base}/api/embed`, {
            method: "POST",
            headers: providerHeaders(profile, apiKey),
            body: JSON.stringify({ model, input: texts }),
            signal: options.signal,
          });
          vectors = Array.isArray(body.embeddings) ? body.embeddings : [];
        } else {
          const body = await providerJson(`${base}/embeddings`, {
            method: "POST",
            headers: providerHeaders(profile, apiKey),
            body: JSON.stringify({ model, input: texts }),
            signal: options.signal,
          });
          vectors = Array.isArray(body.data)
            ? [...body.data]
                .sort((a, b) => Number(a?.index ?? 0) - Number(b?.index ?? 0))
                .map((item) => item?.embedding)
            : [];
        }
        if (vectors.length !== texts.length || !vectors.every(Array.isArray)) {
          throw embeddingFailure();
        }
        return { vectors, provider: this.descriptor() };
      },
    };
  }

  function base64Bytes(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }

  async function gunzip(bytes) {
    if (typeof DecompressionStream !== "function") {
      throw providerError(t("site.runtime.transformers_unsupported_browser"), "unsupported");
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  function blobUrl(bytes, type) {
    return URL.createObjectURL(new Blob([bytes], { type }));
  }

  // Transformers.js is optional: it is present only when the site was exported with it, either embedded in the
  // site script ("inline") or served next to it by the deployment ("files").
  let transformersRuntime = null;
  let modelProgressListener = null;
  function loadTransformersRuntime() {
    if (transformersRuntime) return transformersRuntime;
    transformersRuntime = (async () => {
      const delivery = publication.features?.transformers_runtime;
      if (!delivery) {
        throw providerError(t("site.runtime.transformers_not_included"), "runtime_missing");
      }
      let engineUrl;
      let wasmPaths;
      if (delivery === "inline") {
        const bundle = globalThis.__DERRIDAI_TRANSFORMERS_RUNTIME__;
        if (!bundle) {
          throw providerError(t("site.runtime.transformers_not_included"), "runtime_missing");
        }
        engineUrl = blobUrl(base64Bytes(bundle.engine_b64), "text/javascript");
        wasmPaths = {
          mjs: blobUrl(base64Bytes(bundle.wasm_factory_b64), "text/javascript"),
          wasm: blobUrl(await gunzip(base64Bytes(bundle.wasm_gzip_b64)), "application/wasm"),
        };
      } else {
        const base = new URL("./vendor/transformers/", location.href).href;
        engineUrl = `${base}transformers.min.js`;
        wasmPaths = {
          mjs: `${base}ort-wasm-simd-threaded.mjs`,
          wasm: `${base}ort-wasm-simd-threaded.wasm`,
        };
      }
      const runtime = await import(engineUrl);
      runtime.env.useWasmCache = false;
      runtime.env.backends.onnx.wasm.wasmPaths = wasmPaths;
      // Single-threaded WebAssembly needs no SharedArrayBuffer or cross-origin isolation headers.
      runtime.env.backends.onnx.wasm.numThreads = 1;
      return runtime;
    })();
    transformersRuntime.catch(() => {
      transformersRuntime = null;
    });
    return transformersRuntime;
  }

  function modelFilesBase(profile) {
    const raw =
      String(profile.base_url || "").trim() || String(publication.features?.transformers_local_models || "");
    if (!raw) throw providerError(t("site.runtime.transformers_local_missing"), "invalid_endpoint");
    return new URL(raw.endsWith("/") ? raw : `${raw}/`, location.href).href;
  }

  const transformersExtractors = new Map();
  function transformersExtractor(profile) {
    const key = `${profile.model}|${profile.model_source}|${profile.base_url}`;
    if (!transformersExtractors.has(key)) {
      const loading = (async () => {
        const runtime = await loadTransformersRuntime();
        if (profile.model_source === "local") {
          // Served model files are read like a hub mirror: <base>/<model>/<file>.
          runtime.env.allowRemoteModels = true;
          runtime.env.allowLocalModels = false;
          runtime.env.remoteHost = modelFilesBase(profile);
          runtime.env.remotePathTemplate = "{model}/";
        } else {
          runtime.env.allowRemoteModels = true;
          runtime.env.allowLocalModels = false;
          runtime.env.remoteHost = "https://huggingface.co/";
          runtime.env.remotePathTemplate = "{model}/resolve/{revision}/";
        }
        return runtime.pipeline("feature-extraction", profile.model, {
          device: "wasm",
          progress_callback: (progress) => modelProgressListener?.(progress),
        });
      })();
      loading.catch(() => transformersExtractors.delete(key));
      transformersExtractors.set(key, loading);
    }
    return transformersExtractors.get(key);
  }

  function transformersEmbeddingProvider(profile) {
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    return {
      descriptor: () => ({
        id: profile.id,
        type: "transformers",
        model,
        variant: embeddingVariant(profile),
      }),
      async embed(input, options = {}) {
        const extractor = await transformersExtractor(profile);
        const texts = prefixed(profile, input, options.purpose);
        const vectors = [];
        for (let start = 0; start < texts.length; start += 8) {
          if (options.signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
          const tensor = await extractor(texts.slice(start, start + 8), {
            pooling: "mean",
            normalize: true,
          });
          vectors.push(...tensor.tolist());
        }
        if (vectors.length !== texts.length) throw embeddingFailure();
        return { vectors, provider: this.descriptor() };
      },
    };
  }

  function embeddingProviderFor(profile, apiKey) {
    if (!profile) return undefined;
    return profile.engine === "transformers"
      ? transformersEmbeddingProvider(profile)
      : directEmbeddingProvider(profile, apiKey);
  }

  function directGenerationProvider(profile, apiKey) {
    if (!profile) return undefined;
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    return {
      descriptor: () => ({ id: profile.id, type: profile.engine, model }),
      async generate(request, options = {}) {
        const base = providerBase(profile);
        if (profile.engine === "ollama") {
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

  const EMBEDDING_NAME_HINT = /embed|bge|e5|minilm|gte|nomic|mxbai|arctic|snowflake|sentence/i;

  // Lists what the endpoint reports. Servers rarely say whether a model embeds or generates, so the reader
  // chooses the role; names that look like embedding models are only sorted first for the embedding role.
  async function discoverModels(profile, apiKey) {
    let base;
    try {
      base = providerBase(profile);
    } catch (error) {
      return {
        ok: false,
        code: error?.code || "invalid_endpoint",
        message: error instanceof Error ? error.message : String(error),
        models: [],
      };
    }
    const endpoint = profile.engine === "ollama" ? `${base}/api/tags` : `${base}/models`;
    try {
      const body = await providerJson(endpoint, {
        method: "GET",
        headers: profile.engine === "openai" && apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
        cache: "no-store",
      });
      const names =
        profile.engine === "ollama"
          ? (body.models || []).map((item) => item?.name || item?.model).filter(Boolean)
          : (body.data || []).map((item) => item?.id).filter(Boolean);
      const unique = [...new Set(names)].sort((a, b) => a.localeCompare(b));
      const wantsEmbedding = profile.role === "embedding";
      unique.sort(
        (a, b) =>
          Number(EMBEDDING_NAME_HINT.test(b) === wantsEmbedding) -
          Number(EMBEDDING_NAME_HINT.test(a) === wantsEmbedding),
      );
      return { ok: true, code: "ready", message: t("site.runtime.provider_ready"), models: unique };
    } catch (error) {
      if (error?.code === "network" && (await noCorsReachabilityProbe(endpoint))) {
        const origin =
          location.origin === "null" ? t("site.runtime.file_origin") : location.origin;
        return {
          ok: false,
          code: "cors_blocked",
          message: t("site.runtime.provider_cors_blocked", { origin }),
          remediation:
            profile.engine === "ollama" && location.origin !== "null"
              ? `OLLAMA_ORIGINS="${location.origin}" ollama serve`
              : "",
          models: [],
        };
      }
      return {
        ok: false,
        code: error?.code || "provider_error",
        message: t("site.runtime.provider_test_failed", {
          error: error instanceof Error ? error.message : String(error),
        }),
        models: [],
      };
    }
  }

  // Loads the model (downloading it the first time) and embeds a probe string.
  async function testTransformers(profile) {
    try {
      const provider = transformersEmbeddingProvider(profile);
      const result = await provider.embed([t("site.runtime.transformers_probe")], {
        purpose: "query",
      });
      return {
        ok: true,
        code: "ready",
        message: t("site.runtime.transformers_ready", { dimension: result.vectors[0].length }),
      };
    } catch (error) {
      return {
        ok: false,
        code: error?.code || "provider_error",
        message: t("site.runtime.provider_test_failed", {
          error: error instanceof Error ? error.message : String(error),
        }),
      };
    }
  }

  async function rebuildClient() {
    const host = globalThis.__DERRIDAI_HOST_CAPABILITIES__ || {};
    const embeddingProfile = providerProfiles.find((profile) => profile.id === selectedEmbeddingId);
    const generationProfile = providerProfiles.find((profile) => profile.id === selectedGenerationId);
    const embeddings = embeddingProfile
      ? embeddingProviderFor(embeddingProfile, sessionApiKeys.get(embeddingProfile.id) || "")
      : host.embeddings;
    const generation = generationProfile
      ? directGenerationProvider(generationProfile, sessionApiKeys.get(generationProfile.id) || "")
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

  // Semantic and hybrid search need vectors in the same space as the query: the publication's own, or a
  // local index built with the reader's embedding provider.
  function semanticReady() {
    return Boolean(capabilities?.provider.embeddings && capabilities.localIndex?.complete);
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
        "data-tour": "methods",
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

  async function openRecord(record, searchedQuery = "") {
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
      node(
        "div",
        { class: "record-text", tabindex: "0" },
        ...highlighted(String(record.text || ""), searchedQuery),
      ),
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
    dialog.querySelector("mark")?.scrollIntoView({ block: "center" });
  }

  // Search-term highlighting mirrors the SDK's lexical matching: whole tokens of the query (case-folded for the
  // site locale), plus the whole query as a phrase. Text is only ever set as text nodes, never as HTML.
  const TERM_PATTERN = /[\p{L}\p{N}’'_-]+/gu;

  function queryTerms(query) {
    return [...new Set(String(query || "").toLocaleLowerCase(locale).match(TERM_PATTERN) ?? [])];
  }

  function matchRanges(text, query) {
    const terms = new Set(queryTerms(query));
    if (!terms.size) return [];
    const ranges = [];
    for (const match of text.matchAll(TERM_PATTERN)) {
      if (terms.has(match[0].toLocaleLowerCase(locale))) {
        ranges.push([match.index, match.index + match[0].length]);
      }
    }
    const phrase = String(query || "").trim().toLocaleLowerCase(locale);
    const folded = text.toLocaleLowerCase(locale);
    if (terms.size > 1 && folded.length === text.length) {
      for (let at = folded.indexOf(phrase); phrase && at !== -1; at = folded.indexOf(phrase, at + 1)) {
        ranges.push([at, at + phrase.length]);
      }
    }
    ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
    const merged = [];
    for (const range of ranges) {
      const lastRange = merged[merged.length - 1];
      if (lastRange && range[0] <= lastRange[1]) lastRange[1] = Math.max(lastRange[1], range[1]);
      else merged.push([...range]);
    }
    return merged;
  }

  function highlighted(text, query) {
    const parts = [];
    let from = 0;
    for (const [start, end] of matchRanges(text, query)) {
      if (start > from) parts.push(text.slice(from, start));
      parts.push(node("mark", { text: text.slice(start, end) }));
      from = end;
    }
    if (from < text.length) parts.push(text.slice(from));
    return parts;
  }

  /** The start of the record text, or a window around the first match when it lies beyond the start. */
  function snippetText(text, query, limit = 640) {
    if (text.length <= limit) return text;
    const first = matchRanges(text, query)[0];
    if (!first || first[1] <= limit - 40) return text.slice(0, limit);
    const start = Math.max(text.lastIndexOf(" ", Math.max(first[0] - 200, 0)), 0);
    return `${start ? "…" : ""}${text.slice(start, start + limit).trimStart()}`;
  }

  function resultCard(item, searchedQuery = "") {
    const record = item.record;
    const snippet = snippetText(String(record.text || ""), searchedQuery);
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
      node("div", { class: "snippet" }, ...highlighted(snippet, searchedQuery)),
      node("button", {
        type: "button",
        text: t("site.runtime.view_record"),
        on: { click: () => openRecord(record, searchedQuery) },
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
    mode.value = semanticReady() ? "hybrid" : "keyword";
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
        const searchedQuery = query.value;
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
          results.append(...response.results.map((item) => resultCard(item, searchedQuery)));
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
      node("div", { class: "search-row", "data-tour": "search" }, query, submit),
      node(
        "div",
        { class: "filters", "data-tour": "filters" },
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
      { class: "grid", "data-tour": "works", "aria-label": t("site.runtime.works") },
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
          node("span", { class: "work-title", text: item.work }),
          node("div", { class: "meta", text: (item.authors || []).join(", ") }),
          node("div", { class: "count", text: Number(item.record_count || 0).toLocaleString(locale) }),
          node("div", { class: "muted", text: t("site.runtime.records") }),
        ),
      ),
    );
  }

  function engineLabel(engine) {
    if (engine === "openai") return t("site.runtime.provider_openai");
    if (engine === "ollama") return t("site.runtime.provider_ollama");
    return t("site.runtime.provider_transformers");
  }

  function profileSummary(profile) {
    if (!profile) return "";
    const where =
      profile.engine === "transformers"
        ? profile.model_source === "local"
          ? t("site.runtime.transformers_source_local")
          : t("site.runtime.transformers_source_hub")
        : profile.base_url;
    return t("site.runtime.provider_summary", {
      type: engineLabel(profile.engine),
      model: profile.model,
      endpoint: where,
    });
  }

  async function applyProviderSelection(status) {
    writeLocal(embeddingSelectionKey, selectedEmbeddingId);
    writeLocal(generationSelectionKey, selectedGenerationId);
    status.className = "status";
    status.textContent = t("site.runtime.provider_applying");
    try {
      await rebuildClient();
      await render();
    } catch (error) {
      status.className = "status error";
      status.textContent = t("site.runtime.provider_apply_failed", {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  function providerCard(role) {
    const embedding = role === "embedding";
    const profiles = providerProfiles.filter((profile) => profile.role === role);
    const selectedId = embedding ? selectedEmbeddingId : selectedGenerationId;
    const headingId = `provider-${role}-heading`;
    const select = node(
      "select",
      { class: "control", "aria-label": t(`site.runtime.provider_${role}_select`) },
      node("option", { value: "", text: t(`site.runtime.provider_${role}_none`) }),
      ...profiles.map((profile) =>
        node("option", { value: profile.id, text: `${profile.name} · ${engineLabel(profile.engine)}` }),
      ),
    );
    select.value = selectedId;
    const key = node("input", {
      class: "control",
      type: "password",
      autocomplete: "off",
      placeholder: t("site.runtime.api_key_session"),
      "aria-label": t("site.runtime.api_key"),
    });
    const summary = node("div", { class: "provider-summary" });
    const status = node("div", { class: "status", role: "status", "aria-live": "polite" });
    const keyField = node(
      "label",
      { class: "field" },
      node("span", { text: t("site.runtime.api_key") }),
      key,
    );

    function refresh() {
      const profile = profiles.find((item) => item.id === select.value);
      summary.replaceChildren(
        node("strong", { text: profile ? profile.name : t(`site.runtime.provider_${role}_none`) }),
        node("div", {
          class: "meta",
          text: profile ? profileSummary(profile) : t(`site.runtime.provider_${role}_none_help`),
        }),
      );
      keyField.hidden = !profile || profile.engine === "transformers";
      key.value = profile ? sessionApiKeys.get(profile.id) || "" : "";
    }
    refresh();
    select.addEventListener("change", refresh);

    const use = node("button", {
      class: "primary",
      type: "button",
      text: t("site.runtime.apply_provider"),
      on: {
        click: async () => {
          const id = select.value;
          if (id) {
            sessionApiKeys.set(id, key.value);
            saveProviderProfiles();
          }
          if (embedding) selectedEmbeddingId = id;
          else selectedGenerationId = id;
          await applyProviderSelection(status);
        },
      },
    });
    const remove = node("button", {
      class: "danger",
      type: "button",
      text: t("site.runtime.delete_provider"),
      on: {
        click: async () => {
          const profile = profiles.find((item) => item.id === select.value);
          if (!profile) return;
          if (!window.confirm(t("site.runtime.delete_provider_confirm", { name: profile.name }))) return;
          providerProfiles = providerProfiles.filter((item) => item.id !== profile.id);
          sessionApiKeys.delete(profile.id);
          if (selectedEmbeddingId === profile.id) selectedEmbeddingId = "";
          if (selectedGenerationId === profile.id) selectedGenerationId = "";
          saveProviderProfiles();
          await applyProviderSelection(status);
        },
      },
    });

    return node(
      "section",
      { class: "card stack", "aria-labelledby": headingId },
      node("h3", { id: headingId, text: t(`site.runtime.provider_${role}_heading`) }),
      node("p", { class: "muted", text: t(`site.runtime.provider_${role}_help`) }),
      node("label", { class: "field" }, node("span", { text: t("site.runtime.provider_profile") }), select),
      summary,
      keyField,
      node("div", { class: "chips" }, use, remove),
      status,
      embedding ? indexSection() : null,
    );
  }

  // The local index holds vectors computed here with the reader's embedding provider. It is derived from the
  // published Records, kept only in this browser, and can be rebuilt or cleared at any time.
  let indexMessage = "";
  function indexSection() {
    const index = capabilities.localIndex;
    const outcome = node("div", { class: "status", role: "status", "aria-live": "polite" });
    outcome.textContent = indexMessage;
    indexMessage = "";
    const box = node("div", { class: "provider-summary stack", "data-index": index ? "ready" : "none" });
    const heading = node("strong", { text: t("site.runtime.index_heading") });
    const detail = node("div", { class: "meta", role: "status", "aria-live": "polite" });
    const progress = node("progress", {
      value: 0,
      max: 1,
      hidden: true,
      "aria-label": t("site.runtime.index_progress_label"),
    });
    progress.hidden = true;
    const actions = node("div", { class: "chips" });
    box.append(heading, detail, progress, actions, outcome);
    if (!index) {
      detail.textContent = t("site.runtime.index_no_provider");
      return box;
    }
    if (index.usesPublishedVectors) {
      detail.textContent = t("site.runtime.index_published", { model: index.model || "" });
      return box;
    }
    const where = index.persistent
      ? t("site.runtime.index_storage_indexeddb")
      : t("site.runtime.index_storage_memory");
    detail.textContent = index.complete
      ? t("site.runtime.index_ready", { count: index.indexed, storage: where })
      : t("site.runtime.index_needed", { indexed: index.indexed, total: index.total, storage: where });

    let controller = null;
    const build = node("button", {
      class: index.complete ? "" : "primary",
      type: "button",
      text: index.complete
        ? t("site.runtime.index_rebuild")
        : index.indexed
          ? t("site.runtime.index_resume")
          : t("site.runtime.index_build"),
    });
    const cancel = node("button", { type: "button", text: t("site.runtime.index_cancel") });
    cancel.hidden = true;
    const clear = node("button", {
      class: "danger",
      type: "button",
      text: t("site.runtime.index_clear"),
      disabled: !index.indexed,
    });
    actions.append(build, cancel, clear);

    build.addEventListener("click", async () => {
      controller = new AbortController();
      build.disabled = true;
      clear.disabled = true;
      cancel.hidden = false;
      progress.hidden = false;
      progress.max = Math.max(1, index.total);
      progress.value = index.indexed;
      const stopEvents = client.events.subscribe((event) => {
        if (event.type !== "index-progress") return;
        progress.max = Math.max(1, event.total);
        progress.value = event.indexed;
        detail.textContent = t("site.runtime.index_progress", {
          indexed: event.indexed,
          total: event.total,
        });
      });
      modelProgressListener = (info) => {
        if (info?.status === "progress" && info.file) {
          detail.textContent = t("site.runtime.model_download", {
            file: String(info.file).split("/").pop(),
            percent: Math.round(Number(info.progress) || 0),
          });
        }
      };
      let message = "";
      try {
        await client.index.build({ signal: controller.signal });
        message = t("site.runtime.index_done");
      } catch (error) {
        message =
          error?.name === "AbortError"
            ? t("site.runtime.index_cancelled")
            : t("site.runtime.index_failed", {
                error: error instanceof Error ? error.message : String(error),
              });
      } finally {
        stopEvents();
        modelProgressListener = null;
        controller = null;
      }
      capabilities = await client.capabilities();
      indexMessage = message;
      await render();
    });
    cancel.addEventListener("click", () => controller?.abort());
    clear.addEventListener("click", async () => {
      if (!window.confirm(t("site.runtime.index_clear_confirm"))) return;
      await client.index.clear();
      capabilities = await client.capabilities();
      await render();
    });
    return box;
  }

  function providerForm() {
    const status = node("div", { class: "status", role: "status", "aria-live": "polite" });
    const runtimeIncluded = Boolean(publication.features?.transformers_runtime);
    const name = node("input", {
      class: "control",
      required: true,
      autocomplete: "off",
      placeholder: t("site.runtime.provider_name_placeholder"),
    });
    const role = node(
      "select",
      { class: "control" },
      node("option", { value: "embedding", text: t("site.runtime.role_embedding") }),
      node("option", { value: "generation", text: t("site.runtime.role_generation") }),
    );
    const engine = node(
      "select",
      { class: "control" },
      node("option", { value: "ollama", text: t("site.runtime.provider_ollama") }),
      node("option", { value: "openai", text: t("site.runtime.provider_openai") }),
      node("option", {
        value: "transformers",
        text: runtimeIncluded
          ? t("site.runtime.provider_transformers")
          : t("site.runtime.provider_transformers_unavailable"),
        disabled: !runtimeIncluded,
      }),
    );
    const endpoint = node("input", {
      class: "control",
      type: "url",
      autocomplete: "url",
      placeholder: t("site.runtime.provider_url_placeholder"),
    });
    const key = node("input", {
      class: "control",
      type: "password",
      autocomplete: "off",
      placeholder: t("site.runtime.api_key_optional"),
    });
    const remember = node("input", { type: "checkbox" });
    const model = node("input", {
      class: "control",
      required: true,
      autocomplete: "off",
      list: "provider-model-options",
      placeholder: t("site.runtime.provider_model_placeholder"),
    });
    const modelOptions = node("datalist", { id: "provider-model-options" });
    const load = node("button", { type: "button", text: t("site.runtime.load_models") });
    const source = node(
      "select",
      { class: "control" },
      node("option", { value: "hub", text: t("site.runtime.transformers_source_hub") }),
      node("option", { value: "local", text: t("site.runtime.transformers_source_local") }),
    );
    const filesUrl = node("input", {
      class: "control",
      autocomplete: "off",
      placeholder: publication.features?.transformers_local_models
        ? t("site.runtime.transformers_files_placeholder_default", {
            path: publication.features.transformers_local_models,
          })
        : t("site.runtime.transformers_files_placeholder"),
    });
    const queryPrefix = node("input", { class: "control", autocomplete: "off" });
    const documentPrefix = node("input", { class: "control", autocomplete: "off" });
    const test = node("button", { type: "button", text: t("site.runtime.test_provider") });
    const save = node("button", { class: "primary", type: "submit", text: t("site.runtime.save_provider") });

    const field = (label, control, help) =>
      node(
        "label",
        { class: "field" },
        node("span", { text: label }),
        control,
        help ? node("small", { class: "muted", text: help }) : null,
      );
    const urlGroup = node(
      "div",
      { class: "stack" },
      field(t("site.runtime.provider_url"), endpoint),
      field(t("site.runtime.api_key"), key, t("site.runtime.api_key_help")),
      node("label", { class: "toggle" }, remember, node("span", { text: t("site.runtime.remember_key") })),
    );
    const transformersGroup = node(
      "div",
      { class: "stack" },
      field(t("site.runtime.transformers_model_source"), source, t("site.runtime.transformers_model_help")),
      field(t("site.runtime.transformers_files_url"), filesUrl),
    );
    const prefixGroup = node(
      "details",
      { class: "stack" },
      node("summary", { text: t("site.runtime.advanced") }),
      node("p", { class: "muted", text: t("site.runtime.prefix_help") }),
      field(t("site.runtime.query_prefix"), queryPrefix),
      field(t("site.runtime.document_prefix"), documentPrefix),
    );
    const loadRow = node("div", { class: "chips" }, load);

    function syncForm() {
      if (role.value === "generation" && engine.value === "transformers") engine.value = "ollama";
      const transformers = engine.value === "transformers";
      const transformersOption = [...engine.options].find((item) => item.value === "transformers");
      transformersOption.disabled = !runtimeIncluded || role.value === "generation";
      urlGroup.hidden = transformers;
      loadRow.hidden = transformers;
      transformersGroup.hidden = !transformers;
      filesUrl.closest("label").hidden = !transformers || source.value !== "local";
      prefixGroup.hidden = role.value !== "embedding";
      endpoint.required = !transformers;
      modelOptions.replaceChildren(
        ...(transformers && role.value === "embedding"
          ? TRANSFORMERS_SUGGESTIONS.map((item) =>
              node("option", { value: item.id, label: t(item.note) }),
            )
          : []),
      );
    }
    for (const control of [role, engine, source]) control.addEventListener("change", syncForm);
    syncForm();

    function candidate() {
      const transformers = engine.value === "transformers";
      let base = "";
      if (!transformers) {
        try {
          base = new URL(String(endpoint.value || "").trim()).href.replace(/\/$/, "");
        } catch {
          base = String(endpoint.value || "").trim();
        }
      } else if (source.value === "local") {
        base = String(filesUrl.value || "").trim();
      }
      return {
        id: `provider-${globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : Date.now()}`,
        name: String(name.value || "").trim(),
        role: role.value,
        engine: engine.value,
        base_url: base,
        model: String(model.value || "").trim(),
        model_source: transformers && source.value === "local" ? "local" : "hub",
        query_prefix: role.value === "embedding" ? queryPrefix.value : "",
        document_prefix: role.value === "embedding" ? documentPrefix.value : "",
        remember_key: !transformers && remember.checked && Boolean(key.value),
      };
    }

    function showResult(result) {
      status.className = result.ok ? "status success" : "status error";
      status.replaceChildren(node("span", { text: result.message }));
      if (result.remediation) {
        status.append(node("code", { class: "provider-command", text: result.remediation }));
      }
    }

    load.addEventListener("click", async () => {
      const draft = candidate();
      status.className = "status";
      status.textContent = t("site.runtime.testing_provider");
      const result = await discoverModels(draft, key.value);
      showResult(result);
      if (result.ok) {
        modelOptions.replaceChildren(...result.models.map((item) => node("option", { value: item })));
        status.textContent = t("site.runtime.models_loaded", { count: result.models.length });
        if (!result.models.length) status.className = "status warning";
        model.focus();
      }
    });

    test.addEventListener("click", async () => {
      const draft = candidate();
      if (!draft.model) {
        status.className = "status warning";
        status.textContent = t("site.runtime.provider_model_required");
        return;
      }
      status.className = "status";
      status.textContent = t("site.runtime.testing_provider");
      modelProgressListener = (info) => {
        if (info?.status === "progress" && info.file) {
          status.textContent = t("site.runtime.model_download", {
            file: String(info.file).split("/").pop(),
            percent: Math.round(Number(info.progress) || 0),
          });
        }
      };
      try {
        if (draft.engine === "transformers") {
          showResult(await testTransformers(draft));
          return;
        }
        const result = await discoverModels(draft, key.value);
        if (result.ok && !result.models.includes(draft.model)) {
          showResult({
            ok: false,
            message: t("site.runtime.provider_model_missing", { model: draft.model }),
          });
          return;
        }
        showResult(result);
      } finally {
        modelProgressListener = null;
      }
    });

    const form = node(
      "form",
      { class: "provider-form", "aria-labelledby": "provider-add-heading" },
      node("h3", { id: "provider-add-heading", text: t("site.runtime.add_provider") }),
      node("p", { class: "muted", text: t("site.runtime.provider_local_help") }),
      field(t("site.runtime.provider_name"), name),
      field(t("site.runtime.provider_role"), role),
      field(t("site.runtime.provider_engine"), engine),
      urlGroup,
      transformersGroup,
      field(t("site.runtime.provider_model"), model),
      modelOptions,
      loadRow,
      prefixGroup,
      node("div", { class: "chips" }, test, save),
      status,
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const profile = normalizeProfile(candidate());
      if (!profile) {
        status.className = "status error";
        status.textContent = t("site.runtime.provider_endpoint_invalid");
        return;
      }
      if (profile.engine !== "transformers") {
        try {
          providerBase(profile);
        } catch (error) {
          status.className = "status error";
          status.textContent = error instanceof Error ? error.message : String(error);
          return;
        }
      }
      sessionApiKeys.set(profile.id, key.value);
      providerProfiles = [...providerProfiles, profile];
      saveProviderProfiles();
      if (profile.role === "embedding") selectedEmbeddingId = profile.id;
      else selectedGenerationId = profile.id;
      await applyProviderSelection(status);
    });
    return form;
  }

  function providersView() {
    return node(
      "section",
      {
        class: "panel stack provider-panel",
        "data-tour": "provider",
        "aria-labelledby": "provider-heading",
      },
      node("h2", { id: "provider-heading", text: t("site.runtime.providers") }),
      node("p", { class: "muted", text: t("site.runtime.providers_intro") }),
      node("div", { class: "grid" }, providerCard("embedding"), providerCard("generation")),
      providerForm(),
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
    const methods = methodStrip({
      text: true,
      vector: semanticReady(),
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
        vector: semanticReady(),
        llm: Boolean(capabilities.provider.generation),
      });
      status.className = "status";
      status.textContent = semanticReady()
        ? t("site.runtime.activity_research_hybrid")
        : t("site.runtime.activity_research_text");
      answer.textContent = "";
      evidence.replaceChildren();
      const stopProgress = progressListener(status);
      try {
        const response = await client.research({
          question: q,
          retrieval: {
            mode: semanticReady() ? "hybrid" : "keyword",
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
        { class: "panel stack", "data-tour": "research", "aria-labelledby": "research-heading" },
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
        node(
          "section",
          { class: "panel stack", "data-tour": "evidence", "aria-labelledby": "evidence-heading" },
          node("h3", { id: "evidence-heading", text: t("site.runtime.evidence") }),
          evidence,
        ),
      ),
    );
  }

  async function notesView() {
    const items = await client.annotations.list();
    if (!items.length) {
      return node("div", {
        class: "panel empty",
        "data-tour": "notes",
        text: t("site.runtime.no_annotations"),
      });
    }
    return node(
      "section",
      { class: "stack", "data-tour": "notes", "aria-label": t("site.runtime.annotations") },
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

  // Guided tour: dims the page, spotlights one real element at a time, and explains it. Targets are found by
  // data-tour anchors because render() rebuilds the page; a step may switch view first. Steps without a target
  // (or whose target is missing or empty) fall back to a centered card.
  const TOUR_STEPS = [
    {
      id: "welcome",
      titleKey: "site.runtime.tutorial_welcome_title",
      bodyKey: "site.runtime.tutorial_welcome_body",
    },
    {
      id: "nav",
      target: "nav",
      titleKey: "site.runtime.tutorial_nav_title",
      bodyKey: "site.runtime.tutorial_nav_body",
    },
    {
      id: "works",
      view: "works",
      target: "works",
      titleKey: "site.runtime.tutorial_works_title",
      bodyKey: "site.runtime.tutorial_works_body",
    },
    {
      id: "search",
      view: "search",
      target: "search",
      titleKey: "site.runtime.tutorial_search_title",
      bodyKey: "site.runtime.tutorial_search_body",
    },
    {
      id: "filters",
      view: "search",
      target: "filters",
      titleKey: "site.runtime.tutorial_filters_title",
      bodyKey: "site.runtime.tutorial_filters_body",
    },
    {
      id: "methods",
      view: "search",
      target: "methods",
      titleKey: "site.runtime.tutorial_methods_title",
      bodyKey: "site.runtime.tutorial_methods_body",
    },
    {
      id: "research",
      view: "research",
      target: "research",
      titleKey: "site.runtime.tutorial_research_title",
      bodyKey: "site.runtime.tutorial_research_body",
    },
    {
      id: "provider",
      view: "providers",
      target: "provider",
      titleKey: "site.runtime.tutorial_provider_title",
      bodyKey: "site.runtime.tutorial_provider_body",
    },
    {
      id: "evidence",
      view: "research",
      target: "evidence",
      titleKey: "site.runtime.tutorial_evidence_title",
      bodyKey: "site.runtime.tutorial_evidence_body",
    },
    {
      id: "notes",
      view: "notes",
      target: "notes",
      titleKey: "site.runtime.tutorial_notes_title",
      bodyKey: "site.runtime.tutorial_notes_body",
    },
    {
      id: "controls",
      target: "controls",
      titleKey: "site.runtime.tutorial_controls_title",
      bodyKey: "site.runtime.tutorial_controls_body",
    },
    {
      id: "restart",
      target: "tutorial",
      titleKey: "site.runtime.tutorial_restart_title",
      bodyKey: "site.runtime.tutorial_restart_body",
    },
  ];

  function openTutorial() {
    if (document.querySelector("dialog.tour")) return;
    const startView = view;
    const openedFromButton = document.activeElement?.dataset?.tour === "tutorial";
    const last = TOUR_STEPS.length - 1;
    let index = 0;
    let busy = false;
    let outcome = "skipped";
    let target = null;

    const dialog = node("dialog", {
      class: "tour",
      "aria-labelledby": "tutorial-title",
      "aria-describedby": "tutorial-body",
    });
    const spot = node("div", { class: "tour-spot", "aria-hidden": "true" });
    const title = node("h2", { id: "tutorial-title" });
    const progress = node("div", { class: "tutorial-progress" });
    const body = node("p", { id: "tutorial-body", class: "tutorial-copy" });
    const fill = node("span");
    const previous = node("button", { type: "button", text: t("site.runtime.previous") });
    const next = node("button", { class: "primary", type: "button" });
    const skip = node("button", {
      type: "button",
      text: t("site.runtime.skip_tutorial"),
      on: { click: () => dialog.close() },
    });
    const card = node(
      "div",
      { class: "tour-card" },
      node("div", { class: "tour-bar", "aria-hidden": "true" }, fill),
      node(
        "div",
        { "aria-live": "polite", "aria-atomic": "true" },
        node("div", { class: "dialog-head" }, title, progress),
        node("div", { class: "dialog-body" }, body),
      ),
      node("div", { class: "dialog-body muted tour-hint", text: t("site.runtime.tutorial_hint") }),
      node("div", { class: "dialog-actions" }, skip, previous, next),
    );

    function place() {
      const rect = target ? target.getBoundingClientRect() : null;
      const centered = !rect || (rect.width === 0 && rect.height === 0);
      dialog.classList.toggle("tour-centered", centered);
      dialog.classList.remove("tour-dock", "tour-dock-top");
      for (const property of ["top", "left"]) card.style[property] = "";
      if (centered) return;

      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const pad = 6;
      const edge = 8;
      const gap = 14;
      const box = {
        left: Math.max(rect.left - pad, 4),
        top: Math.max(rect.top - pad, 4),
        right: Math.min(rect.right + pad, vw - 4),
        bottom: Math.min(rect.bottom + pad, vh - 4),
      };
      Object.assign(spot.style, {
        left: `${box.left}px`,
        top: `${box.top}px`,
        width: `${Math.max(box.right - box.left, 0)}px`,
        height: `${Math.max(box.bottom - box.top, 0)}px`,
      });

      const width = card.offsetWidth;
      const height = card.offsetHeight;
      const clampLeft = (value) => Math.min(Math.max(value, edge), Math.max(vw - width - edge, edge));
      const clampTop = (value) => Math.min(Math.max(value, edge), Math.max(vh - height - edge, edge));
      const put = (left, top) => {
        card.style.left = `${clampLeft(left)}px`;
        card.style.top = `${clampTop(top)}px`;
      };
      // Docked full-width card: below the target when it fits there, else above it.
      const dock = () =>
        dialog.classList.add(
          box.bottom + edge + height > vh && box.top - edge >= height ? "tour-dock-top" : "tour-dock",
        );
      if (vw <= 760) dock();
      else if (vh - box.bottom - gap - edge >= height) put(box.left, box.bottom + gap);
      else if (box.top - gap - edge >= height) put(box.left, box.top - gap - height);
      else if (vw - box.right - gap - edge >= width) put(box.right + gap, box.top);
      else if (box.left - gap - edge >= width) put(box.left - gap - width, box.top);
      else dock();
    }

    function reveal() {
      if (!target || target.closest("header.top")) return;
      const rect = target.getBoundingClientRect();
      const usable = window.innerHeight - (window.innerWidth <= 760 ? card.offsetHeight + 24 : 0);
      if (rect.top < 72 || rect.bottom > usable) {
        // A phone docks the card over the lower part of the screen, so bring the target to the top.
        if (window.innerWidth <= 760) window.scrollBy(0, rect.top - 16);
        else target.scrollIntoView({ block: rect.height > usable ? "start" : "center", inline: "nearest" });
      }
    }

    let queued = 0;
    function reposition() {
      if (queued) return;
      queued = window.requestAnimationFrame(() => {
        queued = 0;
        place();
      });
    }

    async function show(nextIndex) {
      if (busy) return;
      busy = true;
      try {
        index = nextIndex;
        const step = TOUR_STEPS[index];
        if (step.view && step.view !== view) {
          view = step.view;
          await render();
        }
        title.textContent = t(`site.runtime.tutorial_${step.id}_title`);
        body.textContent = t(`site.runtime.tutorial_${step.id}_body`);
        progress.textContent = t("site.runtime.tutorial_progress", {
          current: index + 1,
          total: TOUR_STEPS.length,
        });
        fill.style.width = `${((index + 1) / TOUR_STEPS.length) * 100}%`;
        previous.disabled = index === 0;
        next.textContent = index === last ? t("site.runtime.finish") : t("site.runtime.next");
        target = step.target ? document.querySelector(`[data-tour="${step.target}"]`) : null;
        place();
        reveal();
        place();
        next.focus();
      } finally {
        busy = false;
      }
    }

    function move(delta) {
      if (busy) return;
      if (delta > 0 && index === last) {
        outcome = "done";
        dialog.close();
      } else if (index + delta >= 0) {
        show(index + delta);
      }
    }

    previous.addEventListener("click", () => move(-1));
    next.addEventListener("click", () => move(1));
    dialog.addEventListener("keydown", (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      const rtl = document.documentElement.dir === "rtl";
      if (event.key === (rtl ? "ArrowLeft" : "ArrowRight")) {
        event.preventDefault();
        move(1);
      } else if (event.key === (rtl ? "ArrowRight" : "ArrowLeft")) {
        event.preventDefault();
        move(-1);
      }
    });
    dialog.addEventListener("close", async () => {
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
      writeLocal(tutorialKey, outcome);
      dialog.remove();
      if (view !== startView) {
        view = startView;
        await render();
      }
      if (openedFromButton) document.querySelector('[data-tour="tutorial"]')?.focus();
    });

    dialog.append(spot, card);
    document.body.append(dialog);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    dialog.showModal();
    show(0);
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
      {
        class: "header-controls",
        "data-tour": "controls",
        role: "group",
        "aria-label": t("site.runtime.display_controls"),
      },
      node("label", { class: "compact-field" }, node("span", { text: t("site.runtime.language") }), languageSelect),
      node("label", { class: "compact-field" }, node("span", { text: t("site.runtime.theme") }), themeSelect),
      contrast,
      node("button", {
        type: "button",
        "data-tour": "tutorial",
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
      on: {
        click: () => {
          window.setTimeout(() => document.getElementById("site-main")?.focus(), 0);
        },
      },
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
          { "data-tour": "nav", "aria-label": t("site.runtime.navigation") },
          navButton("site.runtime.search", "search"),
          navButton("site.runtime.works", "works"),
          navButton("site.runtime.research", "research"),
          navButton("site.runtime.providers", "providers"),
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
    else if (view === "providers") main.append(providersView());
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
