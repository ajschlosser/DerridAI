/* Copyright 2026 Aaron John Schlosser, PhD. */
(() => {
  "use strict";

  const root = document.getElementById("app");
  const sitePackage = globalThis.__DERRIDAI_SITE_PACKAGE__;
  if (!root) return;
  if (!sitePackage?.manifest || !Array.isArray(sitePackage.chunks)) {
    root.textContent = "This DerridAI site package is incomplete.";
    return;
  }

  const publication = sitePackage.manifest;
  const chunks = sitePackage.chunks;
  const vectors = publication.vector_index || {};
  const vectorById = new Map();
  const recordCache = new Map();
  const vectorChunkCache = new Set();
  const totalRecordCount = (publication.works || []).reduce(
    (sum, item) => sum + Number(item.record_count || 0),
    0,
  );
  const publicationId = String(publication.publication_id || "publication");
  const localeKey = `derridai.site.locale.${publicationId}`;
  const annotationKey = `derridai.site.annotations.${publicationId}`;
  const providerKey = `derridai.site.provider.${publicationId}`;
  const memoryStorage = new Map();

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return memoryStorage.get(key) || null;
    }
  }

  function storageSet(key, value) {
    memoryStorage.set(key, String(value));
    try {
      localStorage.setItem(key, String(value));
    } catch {
      // Opaque file origins and privacy modes may disable localStorage.
    }
  }

  const availableLocales = Object.keys(publication.strings || {});
  let locale = storageGet(localeKey) || publication.locale || availableLocales[0] || "en-US";
  if (!availableLocales.includes(locale)) locale = availableLocales[0] || "en-US";
  let view = "search";
  let sessionApiKey = "";

  const style = document.createElement("style");
  style.textContent = `
    :root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light dark;
      --bg:Canvas;--fg:CanvasText;--muted:color-mix(in srgb,CanvasText 62%,transparent);--surface:color-mix(in srgb,Canvas 96%,CanvasText 4%);
      --raised:color-mix(in srgb,Canvas 92%,CanvasText 8%);--border:color-mix(in srgb,CanvasText 18%,transparent);--accent:LinkText;
      --danger:color-mix(in srgb,red 72%,CanvasText 28%);--shadow:0 12px 32px color-mix(in srgb,CanvasText 13%,transparent)}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);line-height:1.55}button,input,select,textarea{font:inherit;color:inherit}
    button,.button{min-height:2.5rem;border:1px solid var(--border);border-radius:.55rem;background:var(--surface);padding:.45rem .8rem;cursor:pointer}
    button:hover{background:var(--raised)}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
    button.primary{background:var(--accent);color:Canvas;border-color:var(--accent)}button.danger{color:var(--danger)}
    button[disabled]{opacity:.55;cursor:not-allowed}.shell{min-height:100vh}.top{border-bottom:1px solid var(--border);background:var(--surface);position:sticky;top:0;z-index:5}
    .top-inner,.main{width:min(1180px,calc(100% - 2rem));margin:auto}.top-inner{display:flex;gap:1rem;align-items:center;padding:.8rem 0;flex-wrap:wrap}
    .brand{min-width:13rem;flex:1}.brand strong{display:block;font-size:1.05rem}.brand small{color:var(--muted)}
    nav{display:flex;gap:.35rem;flex-wrap:wrap}nav button[aria-current="page"]{background:var(--fg);color:var(--bg)}
    .locale{width:auto;min-height:2.5rem;border:1px solid var(--border);border-radius:.55rem;background:var(--bg);padding:.4rem}
    .hero{padding:2.7rem 0 1.4rem}.hero h1{font-size:clamp(2rem,5vw,3.8rem);line-height:1;margin:0}.hero p{max-width:52rem;color:var(--muted);font-size:1.05rem}
    .panel,.card{border:1px solid var(--border);border-radius:.8rem;background:var(--surface);box-shadow:0 1px 0 color-mix(in srgb,CanvasText 4%,transparent)}
    .panel{padding:1rem}.stack{display:grid;gap:1rem}.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr))}
    .card{padding:1rem}.card h2,.card h3{margin:.1rem 0 .5rem}.muted{color:var(--muted)}.meta{font-size:.88rem;color:var(--muted)}
    .search-row{display:grid;grid-template-columns:minmax(12rem,1fr) auto;gap:.6rem}.control{width:100%;min-height:2.6rem;border:1px solid var(--border);border-radius:.55rem;background:var(--bg);padding:.5rem .65rem}
    .filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:.7rem;margin-top:.8rem}.field{display:grid;gap:.3rem}.field>span,.field>label{font-size:.8rem;font-weight:700;color:var(--muted)}
    .result{display:grid;gap:.5rem}.result-head{display:flex;gap:.7rem;justify-content:space-between;align-items:start}.score{font-variant-numeric:tabular-nums;color:var(--muted);font-size:.82rem}
    .snippet{white-space:pre-wrap}.chips{display:flex;flex-wrap:wrap;gap:.35rem}.chip{font-size:.75rem;padding:.15rem .45rem;border-radius:999px;background:var(--raised)}
    .status{min-height:1.5rem;color:var(--muted);margin:.6rem 0}.status.error{color:var(--danger)}.status.warning{font-weight:650}.empty{text-align:center;padding:2.3rem;color:var(--muted)}
    dialog{width:min(900px,calc(100% - 2rem));max-height:88vh;border:1px solid var(--border);border-radius:.9rem;background:var(--bg);color:var(--fg);box-shadow:var(--shadow);padding:0}
    dialog::backdrop{background:color-mix(in srgb,CanvasText 42%,transparent)}.dialog-head{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--border);padding:1rem;display:flex;justify-content:space-between;gap:1rem;align-items:start}
    .dialog-head h2{margin:0}.dialog-body{padding:1rem;display:grid;gap:1rem}.record-text{white-space:pre-wrap;font-family:Georgia,serif;font-size:1.04rem;line-height:1.7;border-block:1px solid var(--border);padding:1rem 0}
    .metadata{display:grid;grid-template-columns:minmax(9rem,auto) 1fr;gap:.35rem 1rem;font-size:.88rem}.metadata dt{font-weight:700}.metadata dd{margin:0;overflow-wrap:anywhere}
    textarea{min-height:6rem;resize:vertical}.annotation{border-left:3px solid var(--accent);padding:.7rem .9rem;background:var(--surface)}.annotation blockquote{margin:.35rem 0;font-family:Georgia,serif}
    .research-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(16rem,22rem);gap:1rem}.answer{white-space:pre-wrap;font-family:Georgia,serif;font-size:1.04rem}
    details.settings>summary{cursor:pointer;font-weight:700}.provider-test{display:grid;gap:.45rem;padding:.7rem;border:1px solid var(--border);border-radius:.55rem;background:var(--surface)}.provider-test.ok{border-color:color-mix(in srgb,green 55%,var(--border))}.provider-test.error{border-color:color-mix(in srgb,var(--danger) 65%,var(--border))}.provider-origin{overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.78rem}.provider-command{display:block;overflow:auto;padding:.5rem;border-radius:.45rem;background:var(--raised);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.78rem;white-space:pre}.evidence{display:grid;gap:.6rem}.evidence button{text-align:left;height:auto}.footer{margin-top:3rem;border-top:1px solid var(--border);padding:1.2rem 0 2.5rem;color:var(--muted);font-size:.8rem}
    .work-button{width:100%;text-align:left;height:100%;padding:1rem}.work-button h2{font-size:1.1rem}.count{font-size:1.6rem;font-weight:800}
    @media(max-width:760px){.research-layout{grid-template-columns:1fr}.search-row{grid-template-columns:1fr}.top{position:static}.top-inner,.main{width:min(100% - 1rem,1180px)}}
    @media(prefers-reduced-motion:no-preference){dialog[open]{animation:site-in .14s ease-out}@keyframes site-in{from{opacity:0;transform:translateY(.3rem)}}}
  `;
  document.head.appendChild(style);

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
        try { element[key] = value; } catch { element.setAttribute(key, String(value)); }
      } else element.setAttribute(key, value === true ? "" : String(value));
    }
    for (const child of children.flat()) {
      if (child == null) continue;
      element.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return element;
  }

  function formatDate(value) {
    try { return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value)); }
    catch { return String(value || ""); }
  }

  function tokens(value) {
    return String(value || "").toLocaleLowerCase(locale).match(/[\p{L}\p{N}’'_-]+/gu) || [];
  }

  function searchable(record) {
    return Object.entries(record)
      .filter(([key]) => !["source_spans", "field_assertions"].includes(key))
      .map(([, value]) => Array.isArray(value) ? value.join(" ") : typeof value === "object" ? "" : String(value ?? ""))
      .join(" ");
  }

  function decodeBase64Bytes(value) {
    const binary = atob(String(value || ""));
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  }

  function decodeBase64Json(value) {
    const bytes = decodeBase64Bytes(value);
    return JSON.parse(new TextDecoder("utf-8").decode(bytes));
  }

  function decodeFloat32(value) {
    if (!value) return new Float32Array();
    const bytes = decodeBase64Bytes(value);
    if (bytes.byteLength % 4 !== 0) {
      throw new Error(t("site.runtime.vector_payload_invalid"));
    }
    const count = bytes.byteLength / 4;
    const nativeLittleEndian = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
    if (nativeLittleEndian) return new Float32Array(bytes.buffer, bytes.byteOffset, count);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const values = new Float32Array(count);
    for (let index = 0; index < count; index += 1) {
      values[index] = view.getFloat32(index * 4, true);
    }
    return values;
  }

  async function yieldToBrowser() {
    if (globalThis.scheduler?.yield) {
      await globalThis.scheduler.yield();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 0));
  }

  function selectedChunks(filters = {}) {
    if (!filters.work) return chunks;
    return chunks.filter((chunk) => String(chunk.work || "") === String(filters.work));
  }

  async function loadChunkRecords(chunk) {
    if (recordCache.has(chunk.id)) return recordCache.get(chunk.id);
    const records = decodeBase64Json(chunk.records_b64);
    if (!Array.isArray(records)) throw new Error(t("site.runtime.record_payload_invalid"));
    recordCache.set(chunk.id, records);
    return records;
  }

  async function loadCandidateRecords(filters = {}, onProgress) {
    const targetChunks = selectedChunks(filters);
    const candidates = [];
    for (let index = 0; index < targetChunks.length; index += 1) {
      const chunk = targetChunks[index];
      const records = await loadChunkRecords(chunk);
      for (const record of records) {
        if (filters.field && filters.value) {
          const raw = record[filters.field];
          const text = Array.isArray(raw)
            ? raw.join(" ")
            : typeof raw === "object"
              ? JSON.stringify(raw)
              : String(raw ?? "");
          if (
            !text
              .toLocaleLowerCase(locale)
              .includes(String(filters.value).toLocaleLowerCase(locale))
          ) {
            continue;
          }
        }
        candidates.push(record);
      }
      onProgress?.(index + 1, targetChunks.length, chunk.work);
      if (index + 1 < targetChunks.length) await yieldToBrowser();
    }
    return candidates;
  }

  async function loadVectorChunks(filters = {}, onProgress) {
    const dimension = Number(vectors.dimension || 0);
    if (!dimension) return;
    const targetChunks = selectedChunks(filters);
    for (let index = 0; index < targetChunks.length; index += 1) {
      const chunk = targetChunks[index];
      if (!vectorChunkCache.has(chunk.id)) {
        const ids = Array.isArray(chunk.vector_ids) ? chunk.vector_ids : [];
        const values = decodeFloat32(chunk.vectors_b64);
        if (ids.length * dimension !== values.length) {
          throw new Error(t("site.runtime.vector_payload_invalid"));
        }
        ids.forEach((id, vectorIndex) => {
          const start = vectorIndex * dimension;
          vectorById.set(String(id), values.subarray(start, start + dimension));
        });
        vectorChunkCache.add(chunk.id);
      }
      onProgress?.(index + 1, targetChunks.length, chunk.work);
      if (index + 1 < targetChunks.length) await yieldToBrowser();
    }
  }

  async function findRecordById(recordId, work) {
    const targetChunks = work
      ? chunks.filter((chunk) => String(chunk.work || "") === String(work))
      : chunks;
    for (const chunk of targetChunks) {
      const records = await loadChunkRecords(chunk);
      const record = records.find((item) => String(item.record_id || "") === String(recordId));
      if (record) return record;
      await yieldToBrowser();
    }
    return null;
  }

  function lexicalScores(query, candidates) {
    const q = [...new Set(tokens(query))];
    if (!q.length) return candidates.map((record) => ({ record, score: 0 }));
    const docs = candidates.map((record) => {
      const body = searchable(record);
      return { record, body: body.toLocaleLowerCase(locale), terms: tokens(body) };
    });
    const n = docs.length || 1;
    const avg = Math.max(1, docs.reduce((sum, item) => sum + item.terms.length, 0) / n);
    const df = new Map(q.map((term) => [term, docs.filter((doc) => doc.terms.includes(term)).length]));
    return docs.map((doc) => {
      const frequencies = new Map();
      for (const term of doc.terms) if (q.includes(term)) frequencies.set(term, (frequencies.get(term) || 0) + 1);
      let score = 0;
      for (const term of q) {
        const tf = frequencies.get(term) || 0;
        if (!tf) continue;
        const idf = Math.log(1 + (n - (df.get(term) || 0) + .5) / ((df.get(term) || 0) + .5));
        const k1 = 1.2, b = .75;
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc.terms.length / avg));
      }
      if (query && doc.body.includes(String(query).toLocaleLowerCase(locale))) score += 2.5;
      return { record: doc.record, score };
    }).sort((a, b) => b.score - a.score);
  }

  function cosine(a, b) {
    if (!a || !b || !a.length || a.length !== b.length) return -1;
    let dot = 0, aa = 0, bb = 0;
    for (let i = 0; i < a.length; i += 1) {
      const x = Number(a[i]), y = Number(b[i]);
      dot += x * y; aa += x * x; bb += y * y;
    }
    return aa && bb ? dot / Math.sqrt(aa * bb) : -1;
  }

  function providerDefaults() {
    const profiles = Array.isArray(publication.provider_profiles) ? publication.provider_profiles : [];
    const providerRef = String(vectors.provider || "");
    let profile = providerRef.startsWith("profile:") ? profiles.find((p) => p.id === providerRef.slice(8)) : null;
    if (!profile && providerRef === "ollama") profile = profiles.find((p) => p.type === "ollama") || null;
    let stored = {};
    try {
      stored = JSON.parse(storageGet(providerKey) || "{}");
    } catch {
      stored = {};
    }
    return {
      profileId: stored.profileId || profile?.id || "",
      type: stored.type || profile?.type || (providerRef === "ollama" ? "ollama" : "openai"),
      baseUrl: stored.baseUrl || profile?.base_url || (providerRef === "ollama" ? "http://localhost:11434" : ""),
      chatModel: stored.chatModel || profile?.model || "",
      embeddingModel: stored.embeddingModel || vectors.model || "",
    };
  }

  function saveProvider(config) {
    const safe = { ...config };
    delete safe.apiKey;
    storageSet(providerKey, JSON.stringify(safe));
  }

  function providerError(message, kind = "provider", status = 0) {
    const error = new Error(message);
    error.kind = kind;
    error.status = status;
    return error;
  }

  function providerOrigin() {
    return location.origin === "null" ? "null" : location.origin;
  }

  function isLoopbackHost(hostname) {
    return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(
      String(hostname || "").toLocaleLowerCase(),
    );
  }

  function providerUrl(config) {
    const raw = String(config.baseUrl || "").trim();
    if (!raw) throw providerError(t("site.runtime.endpoint_required"), "configuration");
    let parsed;
    try {
      parsed = new URL(raw);
    } catch {
      throw providerError(t("site.runtime.endpoint_invalid"), "configuration");
    }
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw providerError(t("site.runtime.endpoint_http_required"), "configuration");
    }
    if (
      location.protocol === "https:" &&
      parsed.protocol === "http:" &&
      !isLoopbackHost(parsed.hostname)
    ) {
      throw providerError(
        t("site.runtime.provider_mixed_content", { endpoint: parsed.origin }),
        "mixed-content",
      );
    }
    return raw.replace(/\/$/, "");
  }

  function providerHeaders(config, json = false) {
    const headers = {};
    if (json) headers["Content-Type"] = "application/json";
    if (config.type !== "ollama" && config.apiKey) {
      headers.Authorization = `Bearer ${config.apiKey}`;
    }
    return headers;
  }

  async function requestJson(url, init = {}) {
    let response;
    try {
      response = await fetch(url, init);
    } catch (cause) {
      throw providerError(
        t("site.runtime.provider_browser_blocked", { endpoint: url }),
        "network",
      );
    }
    const text = await response.text();
    let body;
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      body = {};
    }
    if (!response.ok) {
      const message =
        body?.error?.message ||
        body?.error ||
        body?.detail ||
        text ||
        `${response.status} ${response.statusText}`;
      const kind =
        response.status === 401 || response.status === 403
          ? "authentication"
          : response.status === 404
            ? "not-found"
            : "provider";
      throw providerError(String(message), kind, response.status);
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

  async function testProviderConnection(config) {
    let base;
    try {
      base = providerUrl(config);
    } catch (error) {
      return {
        ok: false,
        kind: error.kind || "configuration",
        message: error.message,
        origin: providerOrigin(),
      };
    }

    const discoveryUrl =
      config.type === "ollama" ? `${base}/api/tags` : `${base}/models`;
    let body;
    try {
      body = await requestJson(discoveryUrl, {
        method: "GET",
        headers: providerHeaders(config),
        cache: "no-store",
      });
    } catch (error) {
      if (error.kind === "network") {
        const reachable = await noCorsReachabilityProbe(discoveryUrl);
        if (reachable) {
          return {
            ok: false,
            kind: "cors",
            message: t("site.runtime.provider_cors_blocked", {
              origin: providerOrigin(),
            }),
            origin: providerOrigin(),
            endpoint: base,
          };
        }
      }
      return {
        ok: false,
        kind: error.kind || "provider",
        message: error.message,
        origin: providerOrigin(),
        endpoint: base,
      };
    }

    const modelNames =
      config.type === "ollama"
        ? (body.models || [])
            .flatMap((item) => [item?.name, item?.model])
            .filter(Boolean)
            .map(String)
        : (body.data || []).map((item) => String(item?.id || "")).filter(Boolean);
    const missing = [];
    if (config.chatModel && modelNames.length && !modelNames.includes(config.chatModel)) {
      missing.push(config.chatModel);
    }
    if (
      config.embeddingModel &&
      modelNames.length &&
      !modelNames.includes(config.embeddingModel)
    ) {
      missing.push(config.embeddingModel);
    }

    if (missing.length) {
      return {
        ok: false,
        kind: "model",
        message: t("site.runtime.provider_models_missing", {
          models: [...new Set(missing)].join(", "),
        }),
        origin: providerOrigin(),
        endpoint: base,
        models: modelNames,
      };
    }

    return {
      ok: true,
      kind: "ready",
      message: t("site.runtime.provider_ready"),
      origin: providerOrigin(),
      endpoint: base,
      models: modelNames,
    };
  }

  async function embedQuery(query, config) {
    if (!config.embeddingModel) throw new Error(t("site.runtime.embedding_model_required"));
    if (vectors.model && config.embeddingModel !== vectors.model) {
      throw new Error(
        t("site.runtime.embedding_model_mismatch", {
          expected: vectors.model,
          actual: config.embeddingModel,
        }),
      );
    }
    const base = providerUrl(config);
    if (config.type === "ollama") {
      try {
        const body = await requestJson(`${base}/api/embed`, {
          method: "POST", headers: providerHeaders(config, true),
          body: JSON.stringify({ model: config.embeddingModel, input: [query] }),
        });
        const vector = body.embeddings?.[0];
        if (Array.isArray(vector)) return vector;
      } catch (firstError) {
        const body = await requestJson(`${base}/api/embeddings`, {
          method: "POST", headers: providerHeaders(config, true),
          body: JSON.stringify({ model: config.embeddingModel, prompt: query }),
        });
        if (Array.isArray(body.embedding)) return body.embedding;
        throw firstError;
      }
    }
    const body = await requestJson(`${base}/embeddings`, {
      method: "POST", headers: providerHeaders(config, true),
      body: JSON.stringify({ model: config.embeddingModel, input: query }),
    });
    const vector = body.data?.[0]?.embedding;
    if (!Array.isArray(vector)) throw new Error(t("site.runtime.embedding_failed"));
    return vector;
  }

  async function generate(prompt, config) {
    if (!config.chatModel) throw new Error(t("site.runtime.chat_model_required"));
    const base = providerUrl(config);
    if (config.type === "ollama") {
      const body = await requestJson(`${base}/api/chat`, {
        method: "POST", headers: providerHeaders(config, true),
        body: JSON.stringify({
          model: config.chatModel,
          stream: false,
          messages: [{ role: "user", content: prompt }],
          options: { temperature: 0 },
        }),
      });
      return String(body.message?.content || body.response || "");
    }
    const body = await requestJson(`${base}/chat/completions`, {
      method: "POST", headers: providerHeaders(config, true),
      body: JSON.stringify({
        model: config.chatModel,
        temperature: 0,
        messages: [{ role: "user", content: prompt }],
      }),
    });
    return String(body.choices?.[0]?.message?.content || "");
  }

  async function retrieve(
    query,
    mode,
    filters,
    limit = 30,
    config = providerDefaults(),
    onProgress,
  ) {
    const candidates = await loadCandidateRecords(filters, (current, total, work) => {
      onProgress?.("records", current, total, work);
    });
    const lexical = lexicalScores(query, candidates);
    if (mode === "keyword" || !query.trim()) {
      return { items: lexical.slice(0, limit), warning: "" };
    }
    if (!publication.features?.semantic_search) {
      return {
        items: lexical.slice(0, limit),
        warning: t("site.runtime.semantic_unavailable_keyword_fallback"),
      };
    }

    let queryVector;
    try {
      queryVector = await embedQuery(query, config);
    } catch (error) {
      return {
        items: lexical.slice(0, limit),
        warning: t("site.runtime.semantic_provider_fallback", {
          error: error instanceof Error ? error.message : String(error),
        }),
      };
    }

    const expected = Number(vectors.dimension || 0);
    if (expected && queryVector.length !== expected) {
      return {
        items: lexical.slice(0, limit),
        warning: t("site.runtime.semantic_provider_fallback", {
          error: t("site.runtime.embedding_dimension_mismatch", {
            expected,
            actual: queryVector.length,
          }),
        }),
      };
    }

    await loadVectorChunks(filters, (current, total, work) => {
      onProgress?.("vectors", current, total, work);
    });
    const semantic = candidates
      .map((record) => ({
        record,
        score: cosine(queryVector, vectorById.get(String(record.record_id))),
      }))
      .filter((item) => item.score > -1)
      .sort((a, b) => b.score - a.score);
    if (mode === "semantic") return { items: semantic.slice(0, limit), warning: "" };

    const lexicalMax = Math.max(...lexical.map((item) => item.score), 1);
    const semMap = new Map(semantic.map((item) => [String(item.record.record_id), item.score]));
    const merged = lexical
      .map((item) => {
        const semanticScore = semMap.get(String(item.record.record_id));
        const semNorm = semanticScore == null ? 0 : (semanticScore + 1) / 2;
        return { record: item.record, score: 0.45 * (item.score / lexicalMax) + 0.55 * semNorm };
      })
      .concat(
        semantic
          .filter(
            (item) =>
              !lexical.some((lex) => lex.record.record_id === item.record.record_id),
          )
          .map((item) => ({ record: item.record, score: 0.55 * ((item.score + 1) / 2) })),
      )
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
    return { items: merged, warning: "" };
  }

  function mmr(items, limit = 10, lambda = .72) {
    const remaining = [...items];
    const selected = [];
    while (remaining.length && selected.length < limit) {
      let bestIndex = 0, bestScore = -Infinity;
      for (let i = 0; i < remaining.length; i += 1) {
        const item = remaining[i];
        const vector = vectorById.get(String(item.record.record_id));
        const redundancy = selected.length && vector
          ? Math.max(...selected.map((chosen) => cosine(vector, vectorById.get(String(chosen.record.record_id)))))
          : 0;
        const score = lambda * Number(item.score || 0) - (1 - lambda) * Math.max(0, redundancy);
        if (score > bestScore) { bestScore = score; bestIndex = i; }
      }
      selected.push(remaining.splice(bestIndex, 1)[0]);
    }
    return selected;
  }

  function citation(record) {
    const base = String(record.full_citation || record.citation || record.work || record.record_id || "").trim();
    const start = record.printed_page ?? record.page_start ?? record.page;
    const end = record.page_end;
    if (start == null || base.match(/\bp{1,2}\.\s*\d/i)) return base;
    return end != null && String(end) !== String(start) ? `${base}, ${t("site.runtime.pages")} ${start}–${end}` : `${base}, ${t("site.runtime.page")} ${start}`;
  }

  function annotations() {
    try {
      const value = JSON.parse(storageGet(annotationKey) || "[]");
      return Array.isArray(value) ? value : [];
    } catch { return []; }
  }

  function setAnnotations(items) {
    storageSet(annotationKey, JSON.stringify(items));
  }

  function addAnnotation(record, quote, note, tags) {
    const items = annotations();
    items.unshift({
      id: crypto.randomUUID ? crypto.randomUUID() : `a-${Date.now()}-${Math.random()}`,
      record_id: String(record.record_id || ""),
      work: String(record.work || ""),
      quote: String(quote || "").trim(),
      note: String(note || "").trim(),
      tags: String(tags || "").split(",").map((item) => item.trim()).filter(Boolean),
      created_at: new Date().toISOString(),
      publication_id: publicationId,
    });
    setAnnotations(items);
  }

  function deleteAnnotation(id) {
    setAnnotations(annotations().filter((item) => item.id !== id));
    render();
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
      .sort((a, b) => a.localeCompare(b));
  }

  function openRecord(record) {
    const dialog = node("dialog", { "aria-labelledby": "record-title" });
    const title = node("h2", { id: "record-title", text: record.work || record.record_id });
    const close = node("button", { type: "button", text: t("site.runtime.close"), on: { click: () => dialog.close() } });
    const body = node("div", { class: "dialog-body" });
    body.append(node("div", { class: "meta", text: citation(record) }));
    const text = node("div", { class: "record-text", text: record.text || "", tabindex: "0" });
    body.append(text);

    const dl = node("dl", { class: "metadata" });
    for (const [key, value] of Object.entries(record).sort(([a], [b]) => a.localeCompare(b))) {
      if (["text", "field_assertions", "source_spans"].includes(key) || value == null || value === "") continue;
      let rendered;
      if (Array.isArray(value)) rendered = value.map((item) => typeof item === "object" ? JSON.stringify(item) : item).join(", ");
      else if (typeof value === "object") continue;
      else rendered = String(value);
      dl.append(node("dt", { text: key.replaceAll("_", " ") }), node("dd", { text: rendered }));
    }
    body.append(dl);

    const annotationTitle = node("h3", { text: t("site.runtime.add_annotation") });
    const quote = node("textarea", { class: "control", placeholder: t("site.runtime.quote_placeholder"), "aria-label": t("site.runtime.quotation") });
    const capture = node("button", {
      type: "button", text: t("site.runtime.use_selection"),
      on: { click: () => {
        const selection = window.getSelection();
        if (selection && text.contains(selection.anchorNode) && text.contains(selection.focusNode)) quote.value = selection.toString().trim();
      }},
    });
    const note = node("textarea", { class: "control", placeholder: t("site.runtime.note_placeholder"), "aria-label": t("site.runtime.note") });
    const tags = node("input", { class: "control", placeholder: t("site.runtime.tags_placeholder"), "aria-label": t("site.runtime.tags") });
    const saved = node("span", { class: "status", role: "status" });
    const save = node("button", {
      class: "primary", type: "button", text: t("site.runtime.save_annotation"),
      on: { click: () => {
        if (!String(note.value).trim() && !String(quote.value).trim() && !String(tags.value).trim()) return;
        addAnnotation(record, quote.value, note.value, tags.value);
        quote.value = ""; note.value = ""; tags.value = "";
        saved.textContent = t("site.runtime.annotation_saved");
      }},
    });
    body.append(annotationTitle, capture, quote, note, tags, save, saved);
    dialog.append(node("div", { class: "dialog-head" }, title, close), body);
    dialog.addEventListener("close", () => dialog.remove());
    document.body.append(dialog);
    dialog.showModal();
  }

  function resultCard(item, rank) {
    const record = item.record;
    const body = String(record.text || "");
    const snippet = body.length > 650 ? `${body.slice(0, 650)}…` : body;
    return node("article", { class: "card result" },
      node("div", { class: "result-head" },
        node("div", {},
          node("h3", { text: record.work || record.record_id }),
          node("div", { class: "meta", text: citation(record) })
        ),
        node("span", { class: "score", text: `#${rank} · ${Number(item.score || 0).toFixed(3)}` })
      ),
      node("div", { class: "snippet", text: snippet }),
      node("div", { class: "chips" },
        ...["speaker", "position_holder", "stance", "discourse_role"].filter((key) => record[key]).map((key) => node("span", { class: "chip", text: `${key.replaceAll("_", " ")}: ${record[key]}` }))
      ),
      node("button", { type: "button", text: t("site.runtime.view_record"), on: { click: () => openRecord(record) } })
    );
  }

  function searchView() {
    const panel = node("section", { class: "panel" });
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
        disabled: !publication.features?.semantic_search,
      }),
      node("option", {
        value: "hybrid",
        text: t("site.runtime.hybrid"),
        disabled: !publication.features?.semantic_search,
      }),
    );
    mode.value = publication.features?.semantic_search ? "hybrid" : "keyword";
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
    const status = node("div", {
      class: "status",
      role: "status",
      "aria-live": "polite",
    });
    const results = node("div", { class: "stack" });

    async function run() {
      submit.disabled = true;
      status.className = "status";
      status.textContent = t("site.runtime.searching");
      results.replaceChildren();
      try {
        const retrieval = await retrieve(
          query.value,
          mode.value,
          { work: work.value, field: field.value, value: value.value },
          50,
          providerDefaults(),
          (stage, current, total, workName) => {
            status.textContent = t("site.runtime.loading_progress", {
              stage:
                stage === "vectors"
                  ? t("site.runtime.loading_vectors")
                  : t("site.runtime.loading_records"),
              current,
              total,
              work: workName || "",
            });
          },
        );
        const found = retrieval.items;
        status.className = retrieval.warning ? "status warning" : "status";
        status.textContent = retrieval.warning
          ? t("site.runtime.results_with_warning", {
              count: found.length,
              warning: retrieval.warning,
            })
          : t("site.runtime.results_count", { count: found.length });
        if (!found.length) {
          results.append(node("div", { class: "empty", text: t("site.runtime.no_results") }));
        } else {
          results.append(...found.map((item, index) => resultCard(item, index + 1)));
        }
      } catch (error) {
        status.className = "status error";
        status.textContent = t("site.runtime.search_failed", {
          error: error instanceof Error ? error.message : String(error),
        });
      } finally {
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
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.search_mode") }),
          mode,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.work_filter") }),
          work,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.field_filter") }),
          field,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.filter_value") }),
          value,
        ),
      ),
      status,
    );
    return node("div", { class: "stack" }, panel, results);
  }

  function worksView() {
    const cards = (publication.works || []).map((item) => node("button", {
      class: "work-button card", type: "button",
      on: { click: () => {
        view = "search";
        render();
        const searchWork = root.querySelector("[aria-label='" + CSS.escape(t("site.runtime.work_filter")) + "']");
        if (searchWork) { searchWork.value = item.work; searchWork.dispatchEvent(new Event("change")); }
      }},
    },
      node("h2", { text: item.work }),
      node("div", { class: "meta", text: (item.authors || []).join(", ") }),
      node("div", { class: "count", text: Number(item.record_count || 0).toLocaleString(locale) }),
      node("div", { class: "muted", text: t("site.runtime.records") })
    ));
    return node("div", { class: "grid" }, ...cards);
  }

  function providerSettings(config, onChange) {
    const profiles = Array.isArray(publication.provider_profiles)
      ? publication.provider_profiles
      : [];
    const profile = node(
      "select",
      { class: "control" },
      node("option", { value: "", text: t("site.runtime.custom_provider") }),
      ...profiles.map((item) =>
        node("option", {
          value: item.id,
          text: `${item.name || item.id} · ${item.model || ""}`,
        }),
      ),
    );
    profile.value = config.profileId || "";

    const type = node(
      "select",
      { class: "control" },
      node("option", { value: "ollama", text: t("site.runtime.provider_ollama") }),
      node("option", { value: "openai", text: t("site.runtime.provider_openai") }),
    );
    type.value = config.type;

    const endpoint = node("input", {
      class: "control",
      value: config.baseUrl,
      placeholder: t("site.runtime.endpoint_placeholder"),
      inputMode: "url",
    });
    const chat = node("input", {
      class: "control",
      value: config.chatModel,
      placeholder: t("site.runtime.chat_model"),
    });
    const embedding = node("input", {
      class: "control",
      value: config.embeddingModel,
      placeholder: t("site.runtime.embedding_model"),
      readOnly: Boolean(vectors.model),
      title: vectors.model
        ? t("site.runtime.embedding_model_locked", { model: vectors.model })
        : "",
    });
    const key = node("input", {
      class: "control",
      type: "password",
      value: sessionApiKey,
      autocomplete: "off",
      placeholder: t("site.runtime.api_key_session"),
    });
    const testButton = node("button", {
      type: "button",
      text: t("site.runtime.test_provider"),
    });
    const diagnostic = node("div", {
      class: "provider-test",
      role: "status",
      "aria-live": "polite",
    });

    function current() {
      return {
        profileId: profile.value,
        type: type.value,
        baseUrl: endpoint.value.trim(),
        chatModel: chat.value.trim(),
        embeddingModel: embedding.value.trim(),
        apiKey: key.value,
      };
    }

    function changed() {
      const next = current();
      sessionApiKey = next.apiKey;
      saveProvider(next);
      diagnostic.className = "provider-test";
      diagnostic.replaceChildren(
        node("span", { class: "muted", text: t("site.runtime.provider_not_tested") }),
      );
      onChange(next);
    }

    function corsCommand(result, next) {
      if (next.type !== "ollama" || result.origin === "null") return "";
      return `OLLAMA_ORIGINS="${result.origin}" ollama serve`;
    }

    async function copyCommand(command, button) {
      try {
        await navigator.clipboard.writeText(command);
        button.textContent = t("site.runtime.copied");
      } catch {
        button.textContent = t("site.runtime.copy_failed");
      }
    }

    function showDiagnostic(result, next) {
      diagnostic.className = `provider-test ${result.ok ? "ok" : "error"}`;
      const children = [
        node("strong", { text: result.message }),
        node("div", {
          class: "provider-origin",
          text: t("site.runtime.current_origin", {
            origin:
              result.origin === "null"
                ? t("site.runtime.file_origin")
                : result.origin,
          }),
        }),
      ];

      if (result.kind === "cors" && next.type === "ollama") {
        const command = corsCommand(result, next);
        if (command) {
          const copy = node("button", {
            type: "button",
            text: t("site.runtime.copy_command"),
            on: { click: () => copyCommand(command, copy) },
          });
          children.push(
            node("small", { text: t("site.runtime.ollama_cors_help") }),
            node("code", { class: "provider-command", text: command }),
            copy,
          );
        } else {
          children.push(
            node("small", { text: t("site.runtime.file_origin_cors_help") }),
          );
        }
      } else if (result.kind === "cors") {
        children.push(
          node("small", {
            text: t("site.runtime.openai_cors_help", {
              origin:
                result.origin === "null"
                  ? t("site.runtime.file_origin")
                  : result.origin,
            }),
          }),
        );
      } else if (result.kind === "mixed-content") {
        children.push(
          node("small", { text: t("site.runtime.mixed_content_help") }),
        );
      }

      diagnostic.replaceChildren(...children);
    }

    profile.addEventListener("change", () => {
      const chosen = profiles.find((item) => item.id === profile.value);
      if (chosen) {
        type.value = chosen.type || "openai";
        if (chosen.base_url) endpoint.value = chosen.base_url;
        chat.value = chosen.model || "";
      }
      changed();
    });
    for (const control of [type, endpoint, chat, embedding, key]) {
      control.addEventListener("change", changed);
    }

    testButton.addEventListener("click", async () => {
      const next = current();
      sessionApiKey = next.apiKey;
      saveProvider(next);
      onChange(next);
      testButton.disabled = true;
      diagnostic.className = "provider-test";
      diagnostic.replaceChildren(
        node("span", { text: t("site.runtime.testing_provider") }),
      );
      try {
        const result = await testProviderConnection(next);
        showDiagnostic(result, next);
      } catch (error) {
        showDiagnostic(
          {
            ok: false,
            kind: "provider",
            message:
              error instanceof Error ? error.message : String(error),
            origin: providerOrigin(),
          },
          next,
        );
      } finally {
        testButton.disabled = false;
      }
    });

    diagnostic.append(
      node("span", { class: "muted", text: t("site.runtime.provider_not_tested") }),
    );

    return node(
      "details",
      { class: "settings", open: !config.baseUrl },
      node("summary", { text: t("site.runtime.provider_settings") }),
      node(
        "div",
        { class: "stack" },
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.provider_profile") }),
          profile,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.provider_type") }),
          type,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.endpoint") }),
          endpoint,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.chat_model") }),
          chat,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.embedding_model") }),
          embedding,
        ),
        node(
          "label",
          { class: "field" },
          node("span", { text: t("site.runtime.api_key") }),
          key,
        ),
        node("small", { class: "muted", text: t("site.runtime.api_key_help") }),
        node("small", { class: "muted", text: t("site.runtime.cors_help") }),
        testButton,
        diagnostic,
      ),
    );
  }

  function researchView() {
    let config = { ...providerDefaults(), apiKey: sessionApiKey };
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
    const status = node("div", {
      class: "status",
      role: "status",
      "aria-live": "polite",
    });
    const answer = node("div", { class: "answer" });
    const evidence = node("div", { class: "evidence" });

    async function run() {
      const q = String(question.value || "").trim();
      if (!q) return;
      ask.disabled = true;
      status.className = "status";
      status.textContent = t("site.runtime.retrieving");
      answer.textContent = "";
      evidence.replaceChildren();

      try {
        const retrieval = await retrieve(
          q,
          publication.features?.semantic_search ? "hybrid" : "keyword",
          {},
          24,
          config,
          (stage, current, total, workName) => {
            status.textContent = t("site.runtime.loading_progress", {
              stage:
                stage === "vectors"
                  ? t("site.runtime.loading_vectors")
                  : t("site.runtime.loading_records"),
              current,
              total,
              work: workName || "",
            });
          },
        );
        const selected = mmr(retrieval.items, 10);
        if (!selected.length) {
          status.className = "status warning";
          status.textContent = t("site.runtime.no_evidence");
          return;
        }

        selected.forEach((item, index) =>
          evidence.append(
            node(
              "button",
              {
                type: "button",
                on: { click: () => openRecord(item.record) },
              },
              node("strong", {
                text: `[E${index + 1}] ${item.record.work || item.record.record_id}`,
              }),
              node("small", { class: "muted", text: citation(item.record) }),
            ),
          ),
        );

        const packet = selected
          .map((item, index) => {
            const record = item.record;
            return `[E${index + 1}] ${citation(record)}
Record ID: ${record.record_id}
Speaker: ${record.speaker || ""}
Position holder: ${record.position_holder || ""}
Stance: ${record.stance || ""}
TEXT:
${record.text || ""}`;
          })
          .join("\n\n");
        const prompt = `${t("site.runtime.research_instruction")}

${t("site.runtime.question")}: ${q}

${t("site.runtime.evidence")}:
${packet}`;

        status.className = retrieval.warning ? "status warning" : "status";
        status.textContent = retrieval.warning
          ? retrieval.warning
          : t("site.runtime.generating");

        try {
          const response = await generate(prompt, config);
          answer.textContent = response || t("site.runtime.empty_answer");
          status.className = retrieval.warning ? "status warning" : "status";
          status.textContent = retrieval.warning
            ? t("site.runtime.complete_with_warning", {
                warning: retrieval.warning,
              })
            : t("site.runtime.complete");
        } catch (generationError) {
          answer.textContent = t("site.runtime.generation_unavailable_evidence");
          status.className = "status warning";
          status.textContent = t("site.runtime.generation_failed_evidence_ready", {
            error:
              generationError instanceof Error
                ? generationError.message
                : String(generationError),
          });
        }
      } catch (error) {
        status.className = "status error";
        status.textContent = t("site.runtime.research_failed", {
          error: error instanceof Error ? error.message : String(error),
        });
      } finally {
        ask.disabled = false;
      }
    }

    ask.addEventListener("click", run);
    const settings = providerSettings(config, (next) => {
      config = next;
    });

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
        node("div", { class: "answer", "aria-live": "polite" }, answer),
      ),
      node(
        "aside",
        { class: "stack" },
        node("section", { class: "panel" }, settings),
        node(
          "section",
          { class: "panel stack" },
          node("h3", { text: t("site.runtime.evidence") }),
          evidence,
        ),
      ),
    );
  }

  function notesView() {
    const items = annotations();
    if (!items.length) {
      return node("div", {
        class: "panel empty",
        text: t("site.runtime.no_annotations"),
      });
    }

    return node(
      "div",
      { class: "stack" },
      ...items.map((item) => {
        const noteStatus = node("span", {
          class: "status",
          role: "status",
          "aria-live": "polite",
        });
        const open = node("button", {
          type: "button",
          text: t("site.runtime.view_record"),
          on: {
            click: async () => {
              open.disabled = true;
              noteStatus.textContent = t("site.runtime.loading_record");
              try {
                const record = await findRecordById(item.record_id, item.work);
                if (record) {
                  noteStatus.textContent = "";
                  openRecord(record);
                } else {
                  noteStatus.className = "status warning";
                  noteStatus.textContent = t("site.runtime.record_not_found");
                }
              } catch (error) {
                noteStatus.className = "status warning";
                noteStatus.textContent = t("site.runtime.record_load_failed", {
                  error: error instanceof Error ? error.message : String(error),
                });
              } finally {
                open.disabled = false;
              }
            },
          },
        });

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
            ...(item.tags || []).map((tag) =>
              node("span", { class: "chip", text: tag }),
            ),
          ),
          node(
            "div",
            {},
            open,
            node("button", {
              type: "button",
              class: "danger",
              text: t("site.runtime.delete"),
              on: { click: () => deleteAnnotation(item.id) },
            }),
          ),
          noteStatus,
        );
      }),
    );
  }

  function navButton(name, target) {
    return node("button", {
      type: "button", text: t(name),
      "aria-current": view === target ? "page" : null,
      on: { click: () => { view = target; render(); } },
    });
  }

  function render() {
    document.documentElement.lang = locale;
    const localeSelect = node("select", {
      class: "locale", "aria-label": t("site.runtime.language"),
      on: { change: (event) => { locale = event.target.value; storageSet(localeKey, locale); render(); } },
    }, ...availableLocales.map((code) => node("option", { value: code, text: code })));
    localeSelect.value = locale;

    const header = node("header", { class: "top" },
      node("div", { class: "top-inner" },
        node("div", { class: "brand" },
          node("strong", { text: publication.title || t("site.runtime.site_title") }),
          node("small", { text: t("site.runtime.powered_by") })
        ),
        node("nav", { "aria-label": t("site.runtime.navigation") },
          navButton("site.runtime.search", "search"),
          navButton("site.runtime.works", "works"),
          navButton("site.runtime.research", "research"),
          navButton("site.runtime.annotations", "notes")
        ),
        localeSelect
      )
    );

    let content;
    if (view === "works") content = worksView();
    else if (view === "research") content = researchView();
    else if (view === "notes") content = notesView();
    else content = searchView();

    const main = node("main", { class: "main" },
      node("section", { class: "hero" },
        node("h1", { text: publication.title || t("site.runtime.site_title") }),
        publication.description ? node("p", { text: publication.description }) : null,
        node("div", { class: "meta", text: t("site.runtime.publication_summary", {
          works: Number((publication.works || []).length).toLocaleString(locale),
          records: Number(totalRecordCount).toLocaleString(locale),
          date: formatDate(publication.created_at),
        }) })
      ),
      content,
      node("footer", { class: "footer" },
        node("div", { text: t("site.runtime.publication_id", { id: publicationId }) }),
        node("div", { text: t("site.runtime.local_state_notice") })
      )
    );
    root.replaceChildren(node("div", { class: "shell" }, header, main));
  }

  render();
})();
