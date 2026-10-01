// Copyright 2026 Aaron John Schlosser, PhD.

/**
 * Runtime template for the generated, dependency-free browser embedding module.
 *
 * The build script replaces the two marked empty objects with the pinned runtime,
 * model assets, and immutable provenance needed at runtime. Do not import this
 * template directly; use the generated dist/derridai-multilingual-embedder.mjs.
 */

const EMBEDDED_ASSETS = /*__DERRIDAI_EMBEDDED_ASSETS__*/ {};
export const EMBEDDER_INFO = Object.freeze(/*__DERRIDAI_EMBEDDER_INFO__*/ {});

const VIRTUAL_MODEL_ROOT = "https://derridai.invalid/__embedded_models__/";
const TRANSFORMERS_ASSET_KEY = "runtime/transformers.web.min.js";
const ORT_JAVASCRIPT_ASSET_KEY = "runtime/ort.webgpu.bundle.min.mjs";
const ORT_WASM_ASSET_KEY = "runtime/ort-wasm-simd-threaded.jsep.wasm";
const decodedAssets = new Map();

let transformersModulePromise;
let singletonPromise;

function requireAsset(key) {
  const asset = EMBEDDED_ASSETS[key];
  if (!asset) {
    throw new Error(`Embedded asset is missing: ${key}`);
  }
  return asset;
}

function decodedLength(base64) {
  if (!base64) return 0;
  let padding = 0;
  if (base64.endsWith("==")) padding = 2;
  else if (base64.endsWith("=")) padding = 1;
  return Math.floor((base64.length * 3) / 4) - padding;
}

function decodeEmbeddedAsset(key) {
  const cached = decodedAssets.get(key);
  if (cached) return cached;

  const asset = requireAsset(key);
  const total = asset.chunks.reduce((sum, chunk) => sum + decodedLength(chunk), 0);
  const bytes = new Uint8Array(total);
  let offset = 0;

  for (const chunk of asset.chunks) {
    const binary = atob(chunk);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[offset + index] = binary.charCodeAt(index);
    }
    offset += binary.length;
  }

  if (asset.size !== undefined && bytes.byteLength !== asset.size) {
    throw new Error(
      `Embedded asset size mismatch for ${key}: expected ${asset.size}, got ${bytes.byteLength}`,
    );
  }

  decodedAssets.set(key, bytes);
  return bytes;
}

function isNodeRuntime() {
  return (
    typeof process !== "undefined" &&
    typeof process.versions === "object" &&
    Boolean(process.versions?.node)
  );
}

function moduleSpecifierForSource(source) {
  if (!isNodeRuntime() && typeof Blob !== "undefined" && typeof URL.createObjectURL === "function") {
    return URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
  }

  const encoded = btoa(unescape(encodeURIComponent(source)));
  return `data:text/javascript;base64,${encoded}`;
}

function decodedTextAsset(key) {
  return new TextDecoder().decode(decodeEmbeddedAsset(key));
}

function transformersModuleSpecifier() {
  const onnxSpecifier = moduleSpecifierForSource(decodedTextAsset(ORT_JAVASCRIPT_ASSET_KEY));
  const transformersSource = decodedTextAsset(TRANSFORMERS_ASSET_KEY);
  const expectedImports = ["onnxruntime-web/webgpu", "onnxruntime-common"];

  let rewritten = transformersSource;
  const replacedImports = new Set();

  for (const importSpecifier of expectedImports) {
    for (const quote of ['"', "'"]) {
      const quotedImport = `${quote}${importSpecifier}${quote}`;
      const occurrences = rewritten.split(quotedImport).length - 1;
      if (occurrences === 0) continue;
      replacedImports.add(importSpecifier);
      rewritten = rewritten.split(quotedImport).join(JSON.stringify(onnxSpecifier));
    }
  }

  const missingImports = expectedImports.filter(
    (importSpecifier) => !replacedImports.has(importSpecifier),
  );
  if (missingImports.length > 0) {
    throw new Error(
      `Embedded Transformers.js did not contain the expected ONNX Runtime imports: ${missingImports.join(", ")}.`,
    );
  }

  return moduleSpecifierForSource(rewritten);
}

async function loadTransformersModule() {
  transformersModulePromise ??= import(transformersModuleSpecifier());
  return transformersModulePromise;
}

function requestUrl(input) {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  if (input && typeof input.url === "string") return input.url;
  throw new TypeError("Unsupported fetch input.");
}

function responseForAsset(key, method) {
  const asset = EMBEDDED_ASSETS[key];
  if (!asset) {
    return new Response("Embedded model asset not found.", {
      status: 404,
      statusText: "Not Found",
    });
  }

  const headers = new Headers({
    "Content-Type": asset.mediaType || "application/octet-stream",
    "Content-Length": String(asset.size),
    "Cache-Control": "no-store",
    "X-DerridAI-Embedded-Asset": key,
  });

  if (method === "HEAD") {
    return new Response(null, { status: 200, headers });
  }

  return new Response(decodeEmbeddedAsset(key), { status: 200, headers });
}

function modelAssetKey(url) {
  if (!url.href.startsWith(VIRTUAL_MODEL_ROOT)) return null;

  const marker = `/resolve/${EMBEDDER_INFO.model.revision}/`;
  const markerIndex = url.pathname.indexOf(marker);
  if (markerIndex < 0) return null;

  const relative = decodeURIComponent(url.pathname.slice(markerIndex + marker.length));
  return `model/${relative}`;
}

async function embeddedFetch(input, init = undefined) {
  const url = new URL(requestUrl(input));
  const method = String(init?.method || input?.method || "GET").toUpperCase();

  const key = modelAssetKey(url);
  if (key) {
    if (method !== "GET" && method !== "HEAD") {
      return new Response("Method not allowed.", { status: 405 });
    }
    return responseForAsset(key, method);
  }

  throw new Error(
    `The self-contained DerridAI embedder blocked an unexpected network request: ${url.href}`,
  );
}

function applyMode(text, mode) {
  if (mode === "query") return `${EMBEDDER_INFO.model.queryPrefix}${text}`;
  if (mode === "passage") return `${EMBEDDER_INFO.model.passagePrefix}${text}`;
  return text;
}

function validateTexts(texts) {
  if (!Array.isArray(texts)) {
    throw new TypeError("texts must be an array of strings.");
  }
  for (const text of texts) {
    if (typeof text !== "string") {
      throw new TypeError("Every embedding input must be a string.");
    }
  }
}

function validateBatchSize(batchSize) {
  if (!Number.isInteger(batchSize) || batchSize < 1 || batchSize > 256) {
    throw new RangeError("batchSize must be an integer from 1 to 256.");
  }
}

export class BrowserTextEmbedder {
  #extractor;
  #disposed = false;

  constructor(extractor) {
    this.#extractor = extractor;
  }

  get info() {
    return EMBEDDER_INFO;
  }

  async embed(texts, options = {}) {
    this.#assertReady();
    validateTexts(texts);

    const mode = options.mode ?? "raw";
    if (!["raw", "query", "passage"].includes(mode)) {
      throw new RangeError('mode must be "raw", "query", or "passage".');
    }

    const batchSize = options.batchSize ?? 8;
    validateBatchSize(batchSize);

    if (texts.length === 0) return [];

    const prefixed = texts.map((text) => applyMode(text, mode));
    const embeddings = [];

    for (let start = 0; start < prefixed.length; start += batchSize) {
      const batch = prefixed.slice(start, start + batchSize);
      const output = await this.#extractor(batch, {
        pooling: EMBEDDER_INFO.model.pooling,
        normalize: EMBEDDER_INFO.model.normalize,
      });
      const rows = output.tolist();

      if (!Array.isArray(rows) || rows.length !== batch.length) {
        throw new Error("Embedding runtime returned an unexpected batch shape.");
      }

      for (const row of rows) {
        if (!Array.isArray(row) || row.length !== EMBEDDER_INFO.model.dimensions) {
          throw new Error(
            `Embedding runtime returned an unexpected vector dimension; expected ${EMBEDDER_INFO.model.dimensions}.`,
          );
        }
        embeddings.push(Float32Array.from(row));
      }
    }

    return embeddings;
  }

  async embedQuery(query) {
    if (typeof query !== "string") {
      throw new TypeError("query must be a string.");
    }
    return (await this.embed([query], { mode: "query", batchSize: 1 }))[0];
  }

  async embedDocuments(texts, options = {}) {
    return this.embed(texts, {
      mode: "passage",
      batchSize: options.batchSize ?? 8,
    });
  }

  async dispose() {
    if (this.#disposed) return;
    this.#disposed = true;

    if (typeof this.#extractor?.dispose === "function") {
      await this.#extractor.dispose();
    }
    this.#extractor = null;
  }

  #assertReady() {
    if (this.#disposed || !this.#extractor) {
      throw new Error("This embedder has been disposed.");
    }
  }
}

export async function createEmbedder(options = {}) {
  const transformers = await loadTransformersModule();
  const { env, pipeline } = transformers;

  env.allowLocalModels = false;
  env.allowRemoteModels = true;
  env.remoteHost = VIRTUAL_MODEL_ROOT;
  env.remotePathTemplate = "{model}/resolve/{revision}/";
  env.useBrowserCache = false;
  if ("useFSCache" in env) env.useFSCache = false;
  if ("useCustomCache" in env) env.useCustomCache = false;
  if ("useWasmCache" in env) env.useWasmCache = false;
  env.fetch = embeddedFetch;

  const wasm = env.backends?.onnx?.wasm;
  if (!wasm) {
    throw new Error("Transformers.js did not expose the ONNX Runtime WASM backend.");
  }

  wasm.numThreads = 1;
  wasm.proxy = false;
  wasm.wasmBinary = decodeEmbeddedAsset(ORT_WASM_ASSET_KEY);
  if ("wasmPaths" in wasm) wasm.wasmPaths = undefined;

  const extractor = await pipeline("feature-extraction", EMBEDDER_INFO.model.id, {
    revision: EMBEDDER_INFO.model.revision,
    dtype: EMBEDDER_INFO.model.dtype,
    device: EMBEDDER_INFO.model.device,
    progress_callback: typeof options.onProgress === "function" ? options.onProgress : undefined,
  });

  return new BrowserTextEmbedder(extractor);
}

export function load(options = {}) {
  singletonPromise ??= createEmbedder(options);
  return singletonPromise;
}
