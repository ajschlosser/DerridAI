/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

import { computed, inject, provide, ref } from "vue";
import type {
  Annotation,
  AnnotationInput,
  ClientEvent,
  GenerationRequest,
  GenerationResult,
  LocalIndexStatus,
  PublicationManifest,
  PublicationRecord,
  ResearchRequest,
  ResearchResponse,
  SearchRequest,
  SearchResponse,
  SearchWarning,
} from "../sdk/src/types";

export type PublishedSiteView = "search" | "works" | "research" | "providers" | "notes";

export interface PublicationLanguage {
  code: string;
  name?: string;
  flag?: string;
}

export interface PublishedSitePackage {
  manifest: PublicationManifest & {
    strings?: Record<string, Record<string, string>>;
    languages?: PublicationLanguage[];
    browser_embedding_profile?: Partial<LocalModelSettings>;
    features?: PublicationManifest["features"] & {
      transformers_runtime?: string;
      browser_providers?: boolean;
    };
  };
  chunks: unknown[];
}

export interface LocalModelSettings {
  model: string;
  device: "wasm" | "webgpu";
  revision: string;
  dtype: string;
  pooling: string;
  normalize: boolean;
  query_prefix: string;
  document_prefix: string;
}

export interface EndpointProfile {
  id: string;
  name: string;
  base_url: string;
  model: string;
  remember_key: boolean;
  api_key?: string;
  query_prefix?: string;
  document_prefix?: string;
}

export interface DiscoveredModel {
  name: string;
  detail: string;
}

export interface RecordDialogState {
  record: PublicationRecord;
  searchedQuery: string;
}

interface ProviderError extends Error {
  code?: string;
  status?: number;
}

interface ClientCapabilities {
  browse: boolean;
  lexicalSearch: boolean;
  semanticSearch: boolean;
  annotations: boolean;
  research: boolean;
  publicationVectors: {
    available: boolean;
    model?: string;
    dimension?: number | null;
  };
  provider: {
    embeddings: boolean;
    generation: boolean;
  };
  localIndex: LocalIndexStatus | null;
}

interface SdkClient {
  publication: { info(): PublicationManifest; works(): PublicationManifest["works"] };
  records: { get(recordId: string): Promise<PublicationRecord | null> };
  search(request: SearchRequest): Promise<SearchResponse>;
  research(request: ResearchRequest): Promise<ResearchResponse>;
  capabilities(): Promise<ClientCapabilities>;
  citations: { format(record: PublicationRecord): { plain: string } };
  annotations: {
    list(): Promise<Annotation[]>;
    add(input: AnnotationInput): Promise<Annotation>;
    remove(id: string): Promise<void>;
  };
  index: {
    status(): Promise<LocalIndexStatus | null>;
    build(options?: { signal?: AbortSignal }): Promise<LocalIndexStatus>;
    clear(): Promise<void>;
  };
  events: {
    subscribe(listener: (event: ClientEvent) => void): () => void;
  };
}

interface DerridAISdk {
  createClient(options: Record<string, unknown>): Promise<SdkClient>;
  dataSources: { inline(value: PublishedSitePackage): unknown };
}

interface HostCapabilities {
  storage?: unknown;
  generation?: {
    descriptor(): Record<string, unknown>;
    generate(
      request: GenerationRequest,
      options?: { signal?: AbortSignal },
    ): Promise<GenerationResult>;
  };
}

interface TransformersBundle {
  engine_b64: string;
  wasm_factory_b64: string;
  wasm_gzip_b64: string;
}

interface ProviderResponse {
  data?: unknown[];
  error?: { message?: unknown };
  detail?: unknown;
  choices?: Array<{ message?: { content?: unknown } }>;
}

interface ModelProgress {
  status?: string;
  file?: string;
  progress?: number;
}

interface TransformersTensor {
  tolist(): number[][];
  dispose?(): void;
}

type TransformersExtractor = (
  input: string[],
  options: { pooling: string; normalize: boolean },
) => Promise<TransformersTensor>;

interface TransformersRuntime {
  env: {
    allowRemoteModels: boolean;
    allowLocalModels: boolean;
    useBrowserCache: boolean;
    backends?: {
      onnx?: {
        wasm?: {
          wasmPaths?: { mjs: string; wasm: string };
          numThreads?: number;
        };
      };
    };
  };
  pipeline(
    task: "feature-extraction",
    model: string,
    options: Record<string, unknown>,
  ): Promise<TransformersExtractor>;
}

declare global {
  interface Window {
    __DERRIDAI_SITE_PACKAGE__?: PublishedSitePackage;
    DerridAI?: DerridAISdk;
    __DERRIDAI_HOST_CAPABILITIES__?: HostCapabilities;
    __DERRIDAI_TRANSFORMERS_RUNTIME__?: TransformersBundle;
  }
}

const memoryStorage = new Map<string, string>();

function readLocal(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return memoryStorage.get(key) || null;
  }
}

function writeLocal(key: string, value: unknown): void {
  const text = String(value);
  memoryStorage.set(key, text);
  try {
    localStorage.setItem(key, text);
  } catch {
    // Opaque file origins and privacy modes may disable localStorage.
  }
}

function providerError(message: string, code: string, status = 0): ProviderError {
  const error = new Error(message) as ProviderError;
  error.code = code;
  error.status = status;
  return error;
}

function isLoopbackHost(hostname: string): boolean {
  return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(
    String(hostname || "").toLocaleLowerCase(),
  );
}

function base64Bytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

async function gunzip(bytes: Uint8Array): Promise<Uint8Array> {
  if (typeof DecompressionStream !== "function") {
    throw providerError("DecompressionStream is unavailable.", "unsupported");
  }
  const stream = new Blob([bytes as BlobPart])
    .stream()
    .pipeThrough(new DecompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

function blobUrl(bytes: Uint8Array, type: string): string {
  return URL.createObjectURL(new Blob([bytes as BlobPart], { type }));
}

function directionForLocale(code: string): "rtl" | "ltr" {
  try {
    const script = new Intl.Locale(code).maximize().script || "";
    return new Set(["Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm", "Rohg", "Mand"]).has(script)
      ? "rtl"
      : "ltr";
  } catch {
    return "ltr";
  }
}

export function createPublishedSiteContext() {
  const publicationPackageCandidate = window.__DERRIDAI_SITE_PACKAGE__;
  const sdkCandidate = window.DerridAI;
  if (
    !publicationPackageCandidate?.manifest ||
    !Array.isArray(publicationPackageCandidate.chunks)
  ) {
    throw new Error("This DerridAI publication package is incomplete.");
  }
  if (!sdkCandidate?.createClient || !sdkCandidate?.dataSources?.inline) {
    throw new Error("The DerridAI SDK could not be loaded.");
  }
  const publicationPackage: PublishedSitePackage = publicationPackageCandidate;
  const sdk: DerridAISdk = sdkCandidate;

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
  const localModelKey = `derridai.site.local-model.${publicationId}`;
  const endpointsKey = `derridai.site.endpoints.${publicationId}`;

  const availableLocales = Object.keys(publication.strings || {});
  const languageMetadata = Array.isArray(publication.languages) ? publication.languages : [];
  const initialLocale =
    readLocal(localeKey) || publication.locale || availableLocales[0] || "en-US";

  const locale = ref(
    availableLocales.includes(initialLocale) ? initialLocale : availableLocales[0] || "en-US",
  );
  const theme = ref<"light" | "dark">(readLocal(themeKey) === "dark" ? "dark" : "light");
  const highContrast = ref(readLocal(contrastKey) === "high");
  const view = ref<PublishedSiteView>("search");
  const tutorialSeen = ref(Boolean(readLocal(tutorialKey)));
  const searchWork = ref("");
  const recordDialog = ref<RecordDialogState | null>(null);
  const activeDevice = ref("");
  const client = ref<SdkClient | null>(null);
  const capabilities = ref<ClientCapabilities | null>(null);

  const publishedBrowserProfile = {
    model: "Xenova/multilingual-e5-small",
    revision: "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
    dtype: "q8",
    pooling: "mean",
    normalize: true,
    query_prefix: "query: ",
    document_prefix: "passage: ",
    ...(publication.browser_embedding_profile || {}),
  };

  const transformerSuggestions = [
    {
      id: String(publishedBrowserProfile.model),
      revision: String(publishedBrowserProfile.revision || ""),
      dtype: String(publishedBrowserProfile.dtype || ""),
      pooling: String(publishedBrowserProfile.pooling || "mean"),
      normalize: publishedBrowserProfile.normalize !== false,
      note: "site.runtime.transformers_model_multilingual_small",
      query_prefix: String(publishedBrowserProfile.query_prefix || ""),
      document_prefix: String(publishedBrowserProfile.document_prefix || ""),
    },
    {
      id: "Xenova/all-MiniLM-L6-v2",
      revision: "",
      dtype: "",
      pooling: "mean",
      normalize: true,
      note: "site.runtime.transformers_model_english_small",
      query_prefix: "",
      document_prefix: "",
    },
    {
      id: "Xenova/bge-m3",
      aliases: ["bge-m3", "bge-m3:latest", "BAAI/bge-m3", "Xenova/bge-m3"],
      revision: "",
      dtype: "q8",
      pooling: "cls",
      normalize: true,
      note: "site.runtime.transformers_model_bge_m3",
      query_prefix: "",
      document_prefix: "",
    },
  ];

  const defaultTransformersModel = String(publishedBrowserProfile.model);
  const defaultTransformersDevice: LocalModelSettings["device"] = "wasm";
  const modelCacheName = "transformers-cache";

  function t(key: string, vars: Record<string, unknown> = {}): string {
    const dictionary = (publication.strings || {})[locale.value] || {};
    let value = String(dictionary[key] || key);
    for (const [name, replacement] of Object.entries(vars)) {
      value = value.replaceAll(`{${name}}`, String(replacement));
    }
    return value;
  }

  function sourceEmbeddingModel(): string {
    return String(
      publication.vector_index?.model ||
        (publication.source_collection as Record<string, unknown> | undefined)?.embedding_model ||
        "",
    ).trim();
  }

  function suggestedProfileForModel(model: string) {
    const normalized = String(model || "")
      .trim()
      .toLocaleLowerCase();
    return transformerSuggestions.find(
      (item) =>
        item.id.toLocaleLowerCase() === normalized ||
        ("aliases" in item &&
          (item.aliases || []).some((alias) => alias.toLocaleLowerCase() === normalized)),
    );
  }

  function settingsForModel(model: string) {
    const match = suggestedProfileForModel(model);
    return {
      revision: match?.revision || "",
      dtype: match?.dtype || "",
      pooling: match?.pooling || "mean",
      normalize: match?.normalize !== false,
      query_prefix: match?.query_prefix || "",
      document_prefix: match?.document_prefix || "",
    };
  }

  function loadLocalModel(): LocalModelSettings {
    try {
      const raw = JSON.parse(readLocal(localModelKey) || "{}") as Partial<LocalModelSettings>;
      const model = String(raw.model || defaultTransformersModel);
      const defaults = settingsForModel(model);
      const device: LocalModelSettings["device"] =
        raw.device === "webgpu" || raw.device === "wasm" ? raw.device : defaultTransformersDevice;
      return {
        model,
        device,
        revision: raw.revision == null ? defaults.revision : String(raw.revision),
        dtype: raw.dtype == null ? defaults.dtype : String(raw.dtype),
        pooling: raw.pooling == null ? defaults.pooling : String(raw.pooling),
        normalize: raw.normalize == null ? defaults.normalize : Boolean(raw.normalize),
        query_prefix: raw.query_prefix == null ? defaults.query_prefix : String(raw.query_prefix),
        document_prefix:
          raw.document_prefix == null ? defaults.document_prefix : String(raw.document_prefix),
      };
    } catch {
      const defaults = settingsForModel(defaultTransformersModel);
      return {
        model: defaultTransformersModel,
        device: defaultTransformersDevice,
        ...defaults,
      };
    }
  }

  function normalizeEndpoint(raw: Partial<EndpointProfile> | null): EndpointProfile | null {
    if (!raw || !raw.id || !raw.name || !raw.base_url) return null;
    return {
      id: String(raw.id),
      name: String(raw.name),
      base_url: String(raw.base_url),
      model: String(raw.model || ""),
      remember_key: Boolean(raw.remember_key ?? raw.api_key),
      api_key: String(raw.api_key || ""),
      query_prefix: String(raw.query_prefix || ""),
      document_prefix: String(raw.document_prefix || ""),
    };
  }

  function loadEndpoints(): EndpointProfile[] {
    try {
      const saved = JSON.parse(readLocal(endpointsKey) || "null");
      if (Array.isArray(saved)) {
        return saved.map((item) => normalizeEndpoint(item)).filter(Boolean) as EndpointProfile[];
      }
    } catch {
      // Fall through to the older browser-only provider list.
    }
    try {
      const older = JSON.parse(readLocal(providersKey) || "[]");
      return Array.isArray(older)
        ? (older.map((item) => normalizeEndpoint(item)).filter(Boolean) as EndpointProfile[])
        : [];
    } catch {
      return [];
    }
  }

  const localModel = ref<LocalModelSettings>(loadLocalModel());
  const endpoints = ref<EndpointProfile[]>(loadEndpoints());
  const sessionApiKeys = new Map<string, string>();
  for (const endpoint of endpoints.value) {
    if (endpoint.remember_key && endpoint.api_key) {
      sessionApiKeys.set(endpoint.id, endpoint.api_key);
    }
  }

  const initialEmbedding = readLocal(embeddingSelectionKey) || "";
  const selectedEmbeddingId = ref(
    endpoints.value.some((endpoint) => endpoint.id === initialEmbedding) ? initialEmbedding : "",
  );
  const initialGeneration = readLocal(generationSelectionKey) || readLocal(legacyProviderKey) || "";
  const selectedGenerationId = ref(
    endpoints.value.some((endpoint) => endpoint.id === initialGeneration) ? initialGeneration : "",
  );

  function saveLocalModel(): void {
    writeLocal(localModelKey, JSON.stringify(localModel.value));
  }

  function saveEndpoints(): void {
    writeLocal(
      endpointsKey,
      JSON.stringify(
        endpoints.value.map((endpoint) => ({
          ...endpoint,
          api_key: endpoint.remember_key ? sessionApiKeys.get(endpoint.id) || "" : "",
        })),
      ),
    );
    writeLocal(embeddingSelectionKey, selectedEmbeddingId.value);
    writeLocal(generationSelectionKey, selectedGenerationId.value);
  }

  function applyAppearance(): void {
    document.documentElement.dataset.theme = theme.value;
    document.documentElement.dataset.contrast = highContrast.value ? "high" : "normal";
    document.documentElement.lang = locale.value;
    document.documentElement.dir = directionForLocale(locale.value);
    document.title = publication.title || t("site.runtime.site_title");
  }

  function setLocale(value: string): void {
    locale.value = availableLocales.includes(value) ? value : locale.value;
    writeLocal(localeKey, locale.value);
    applyAppearance();
  }

  function setTheme(value: string): void {
    theme.value = value === "dark" ? "dark" : "light";
    writeLocal(themeKey, theme.value);
    applyAppearance();
  }

  function setHighContrast(value: boolean): void {
    highContrast.value = Boolean(value);
    writeLocal(contrastKey, highContrast.value ? "high" : "normal");
    applyAppearance();
  }

  function markTutorial(outcome: "done" | "skipped"): void {
    writeLocal(tutorialKey, outcome);
    tutorialSeen.value = true;
  }

  function languageLabel(code: string): string {
    const metadata = languageMetadata.find((item) => item.code === code);
    return metadata ? `${metadata.flag || ""} ${metadata.name || code}`.trim() : code;
  }

  function formatDate(value: unknown): string {
    try {
      return new Intl.DateTimeFormat(locale.value, { dateStyle: "medium" }).format(
        new Date(String(value)),
      );
    } catch {
      return String(value || "");
    }
  }

  function filterFields(): string[] {
    const excluded = new Set(["text", "record_id", "source_spans", "field_assertions", "updates"]);
    const sourceCollection = publication.source_collection as
      | { filter_fields?: unknown[] }
      | undefined;
    const declared = Array.isArray(sourceCollection?.filter_fields)
      ? sourceCollection.filter_fields
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
    return [...new Set([...declared, ...common].map(String))]
      .filter((key) => key && !excluded.has(key) && key !== "work")
      .sort((left, right) => left.localeCompare(right));
  }

  function localizedWarning(warning: SearchWarning | undefined): string {
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

  function warningText(warnings: SearchWarning[] | undefined): string {
    return (warnings || []).map(localizedWarning).filter(Boolean).join(" ");
  }

  function providerBase(profile: EndpointProfile): string {
    const raw = String(profile?.base_url || "")
      .trim()
      .replace(/\/$/, "");
    if (!raw) {
      throw providerError(t("site.runtime.provider_endpoint_missing"), "invalid_endpoint");
    }

    if (raw.startsWith("/")) {
      if (!["http:", "https:"].includes(location.protocol)) {
        throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
      }
      const sameOrigin = new URL(raw, location.origin);
      if (sameOrigin.origin !== location.origin) {
        throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
      }
      return sameOrigin.href.replace(/\/$/, "");
    }

    let parsed: URL;
    try {
      parsed = new URL(raw);
    } catch {
      throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
    }
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw providerError(t("site.runtime.provider_endpoint_invalid"), "invalid_endpoint");
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

  function providerHeaders(apiKey: string): Record<string, string> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
    return headers;
  }

  async function providerJson(url: string, init: RequestInit): Promise<ProviderResponse> {
    let response: Response;
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
    let body: ProviderResponse = {};
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

  async function noCorsReachabilityProbe(url: string): Promise<boolean> {
    try {
      await fetch(url, { method: "GET", mode: "no-cors", cache: "no-store" });
      return true;
    } catch {
      return false;
    }
  }

  function embeddingVariant(profile: { query_prefix?: string; document_prefix?: string }): string {
    return [
      profile.query_prefix ? `query-prefix=${profile.query_prefix}` : "",
      profile.document_prefix ? `document-prefix=${profile.document_prefix}` : "",
    ]
      .filter(Boolean)
      .join(";");
  }

  function prefixed(
    profile: { query_prefix?: string; document_prefix?: string },
    input: string[],
    purpose?: string,
  ): string[] {
    const prefix = purpose === "query" ? profile.query_prefix : profile.document_prefix;
    return prefix ? input.map((text) => `${prefix}${text}`) : input;
  }

  async function yieldAfterEmbeddingBatch(signal?: AbortSignal): Promise<void> {
    if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
    const scheduler = (
      globalThis as typeof globalThis & { scheduler?: { yield?: () => Promise<void> } }
    ).scheduler;
    if (scheduler?.yield) {
      await scheduler.yield();
    } else {
      await new Promise<void>((resolve) => {
        if (typeof globalThis.requestAnimationFrame === "function") {
          globalThis.requestAnimationFrame(() => setTimeout(resolve, 0));
        } else {
          setTimeout(resolve, 0);
        }
      });
    }
    if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
  }

  function embeddingFailure(): ProviderError {
    return providerError(t("site.runtime.embedding_failed"), "embedding_failed");
  }

  function directEmbeddingProvider(profile: EndpointProfile, apiKey: string) {
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    const descriptor = () => ({
      id: profile.id,
      type: "openai",
      model,
      variant: embeddingVariant(profile),
    });
    return {
      descriptor,
      async embed(input: string[], options: { signal?: AbortSignal; purpose?: string } = {}) {
        const base = providerBase(profile);
        const texts = prefixed(profile, input, options.purpose);
        const body = await providerJson(`${base}/embeddings`, {
          method: "POST",
          headers: providerHeaders(apiKey),
          body: JSON.stringify({ model, input: texts }),
          signal: options.signal,
        });
        const vectors = Array.isArray(body.data)
          ? [...body.data]
              .sort((left, right) => Number(left?.index ?? 0) - Number(right?.index ?? 0))
              .map((item) => item?.embedding)
          : [];
        if (vectors.length !== texts.length || !vectors.every(Array.isArray)) {
          throw embeddingFailure();
        }
        return { vectors, provider: descriptor() };
      },
    };
  }

  let transformersRuntime: Promise<TransformersRuntime> | null = null;
  let modelProgressListener: ((info: ModelProgress) => void) | null = null;
  const transformersExtractors = new Map<string, Promise<TransformersExtractor>>();

  async function loadTransformersRuntime(): Promise<TransformersRuntime> {
    if (transformersRuntime) return transformersRuntime;
    transformersRuntime = (async () => {
      const delivery = publication.features?.transformers_runtime || "inline";
      let engineUrl: string;
      let wasmPaths: { mjs: string; wasm: string };
      if (delivery === "files") {
        const base = new URL("./vendor/transformers/", location.href).href;
        engineUrl = `${base}transformers.min.js`;
        wasmPaths = {
          mjs: `${base}ort-wasm-simd-threaded.mjs`,
          wasm: `${base}ort-wasm-simd-threaded.wasm`,
        };
      } else {
        const bundle = window.__DERRIDAI_TRANSFORMERS_RUNTIME__;
        if (!bundle) {
          throw providerError(t("site.runtime.transformers_not_included"), "runtime_missing");
        }
        engineUrl = blobUrl(base64Bytes(bundle.engine_b64), "text/javascript");
        wasmPaths = {
          mjs: blobUrl(base64Bytes(bundle.wasm_factory_b64), "text/javascript"),
          wasm: blobUrl(await gunzip(base64Bytes(bundle.wasm_gzip_b64)), "application/wasm"),
        };
      }
      const runtime = (await import(/* @vite-ignore */ engineUrl)) as TransformersRuntime;
      runtime.env.allowRemoteModels = true;
      runtime.env.allowLocalModels = false;
      runtime.env.useBrowserCache = true;
      if (runtime.env.backends?.onnx?.wasm) {
        runtime.env.backends.onnx.wasm.wasmPaths = wasmPaths;
        runtime.env.backends.onnx.wasm.numThreads = 1;
      }
      return runtime;
    })();
    transformersRuntime.catch(() => {
      transformersRuntime = null;
    });
    return transformersRuntime;
  }

  async function resolveDevice(
    preference: LocalModelSettings["device"],
  ): Promise<"wasm" | "webgpu"> {
    if (preference !== "webgpu") return "wasm";
    const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<unknown> } }).gpu;
    if (!gpu) return "wasm";
    try {
      if (await gpu.requestAdapter()) return "webgpu";
    } catch {
      // Explicit WebGPU can still be unavailable under browser or driver policy.
    }
    return "wasm";
  }

  function transformersExtractor(profile: LocalModelSettings): Promise<TransformersExtractor> {
    const key = [
      profile.model,
      profile.revision || "",
      profile.dtype || "",
      profile.device || defaultTransformersDevice,
    ].join("|");
    const cached = transformersExtractors.get(key);
    if (cached) return cached;
    const loading = (async () => {
      const runtime = await loadTransformersRuntime();
      const device = await resolveDevice(profile.device || defaultTransformersDevice);
      activeDevice.value = device;
      try {
        return await runtime.pipeline("feature-extraction", profile.model, {
          device,
          ...(profile.revision ? { revision: profile.revision } : {}),
          ...(profile.dtype ? { dtype: profile.dtype } : {}),
          progress_callback: (progress: unknown) => modelProgressListener?.(progress),
        });
      } catch (error) {
        if (device === "wasm") throw error;
        activeDevice.value = "wasm";
        return runtime.pipeline("feature-extraction", profile.model, {
          device: "wasm",
          ...(profile.revision ? { revision: profile.revision } : {}),
          ...(profile.dtype ? { dtype: profile.dtype } : {}),
          progress_callback: (progress: unknown) => modelProgressListener?.(progress),
        });
      }
    })();
    loading.catch(() => transformersExtractors.delete(key));
    transformersExtractors.set(key, loading);
    return loading;
  }

  async function deleteModelCache(): Promise<void> {
    transformersExtractors.clear();
    activeDevice.value = "";
    if (typeof caches === "undefined") return;
    const names = await caches.keys();
    await Promise.all(
      names
        .filter((name) => name === modelCacheName || name.toLowerCase().includes("transformers"))
        .map((name) => caches.delete(name)),
    );
  }

  function transformersEmbeddingProvider(profile: LocalModelSettings) {
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    const descriptor = () => ({
      id: "transformers-local",
      type: "transformers",
      model,
      revision: profile.revision || undefined,
      variant: [
        embeddingVariant(profile),
        profile.dtype ? `dtype=${profile.dtype}` : "",
        `pooling=${profile.pooling || "mean"}`,
        `normalize=${profile.normalize !== false}`,
      ]
        .filter(Boolean)
        .join(";"),
    });
    return {
      descriptor,
      async embed(input: string[], options: { signal?: AbortSignal; purpose?: string } = {}) {
        const extractor = await transformersExtractor(profile);
        const texts = prefixed(profile, input, options.purpose);
        const vectors: number[][] = [];
        const microBatchSize = /bge-m3$/i.test(model) ? 1 : 4;
        for (let start = 0; start < texts.length; start += microBatchSize) {
          if (options.signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
          const tensor = await extractor(texts.slice(start, start + microBatchSize), {
            pooling: profile.pooling || "mean",
            normalize: profile.normalize !== false,
          });
          try {
            vectors.push(...tensor.tolist());
          } finally {
            tensor.dispose?.();
          }
          if (start + microBatchSize < texts.length) {
            await yieldAfterEmbeddingBatch(options.signal);
          }
        }
        if (vectors.length !== texts.length) throw embeddingFailure();
        return { vectors, provider: descriptor() };
      },
    };
  }

  function directGenerationProvider(profile: EndpointProfile, apiKey: string) {
    const model = String(profile.model || "").trim();
    if (!model) return undefined;
    const descriptor = () => ({ id: profile.id, type: "openai", model });
    return {
      descriptor,
      async generate(request: GenerationRequest, options: { signal?: AbortSignal } = {}) {
        const base = providerBase(profile);
        const body = await providerJson(`${base}/chat/completions`, {
          method: "POST",
          headers: providerHeaders(apiKey),
          body: JSON.stringify({
            model,
            temperature: 0,
            messages: [{ role: "user", content: request.prompt }],
          }),
          signal: options.signal,
        });
        return {
          text: String(body.choices?.[0]?.message?.content || ""),
          provider: descriptor(),
        };
      },
    };
  }

  function endpointById(id: string): EndpointProfile | null {
    return endpoints.value.find((endpoint) => endpoint.id === id) || null;
  }

  function embeddingProviderFor(profile: EndpointProfile | null) {
    if (!profile) return transformersEmbeddingProvider(localModel.value);
    return directEmbeddingProvider(profile, sessionApiKeys.get(profile.id) || "");
  }

  async function rebuildClient(): Promise<void> {
    const host = window.__DERRIDAI_HOST_CAPABILITIES__ || {};
    const embeddingProfile = endpointById(selectedEmbeddingId.value);
    const generationProfile = endpointById(selectedGenerationId.value);
    const embeddings = embeddingProviderFor(embeddingProfile);
    const generation = generationProfile
      ? directGenerationProvider(generationProfile, sessionApiKeys.get(generationProfile.id) || "")
      : host.generation;
    client.value = await sdk.createClient({
      dataSource: sdk.dataSources.inline(publicationPackage),
      storage: host.storage,
      embeddings,
      generation,
      locale: locale.value,
    });
    capabilities.value = await client.value.capabilities();
  }

  async function setLocaleAndRebuild(value: string): Promise<void> {
    setLocale(value);
    await rebuildClient();
  }

  function semanticReady(): boolean {
    return Boolean(
      capabilities.value?.provider?.embeddings && capabilities.value?.localIndex?.complete,
    );
  }

  function subscribeProgress(setStatus: (message: string) => void): () => void {
    if (!client.value) return () => undefined;
    return client.value.events.subscribe((event: ClientEvent) => {
      if (event.type === "embedding-start") {
        setStatus(t("site.runtime.activity_vector_embedding"));
        return;
      }
      if (event.type === "generation-start") {
        setStatus(t("site.runtime.activity_llm_generation"));
        return;
      }
      if (event.type !== "load-progress") return;
      setStatus(
        t("site.runtime.loading_progress", {
          stage:
            event.stage === "vectors"
              ? t("site.runtime.loading_vectors")
              : t("site.runtime.loading_records"),
          current: event.completed,
          total: event.total,
          work: event.work || "",
        }),
      );
    });
  }

  async function refreshCapabilities(): Promise<void> {
    if (client.value) capabilities.value = await client.value.capabilities();
  }

  function updateLocalModel(model: string, device: LocalModelSettings["device"]): void {
    const nextModel = String(model || "").trim();
    const defaults = settingsForModel(nextModel);
    localModel.value = {
      model: nextModel,
      device,
      ...defaults,
    };
    saveLocalModel();
  }

  async function testLocalModel(
    onProgress?: (info: ModelProgress) => void,
  ): Promise<{ ok: boolean; message: string }> {
    const profile = localModel.value;
    if (!profile.model) {
      return { ok: false, message: t("site.runtime.provider_model_required") };
    }
    modelProgressListener = onProgress || null;
    try {
      const provider = transformersEmbeddingProvider(profile);
      if (!provider) {
        return { ok: false, message: t("site.runtime.provider_model_required") };
      }
      const result = await provider.embed([t("site.runtime.transformers_probe")], {
        purpose: "query",
      });
      return {
        ok: true,
        message: t("site.runtime.transformers_ready", {
          dimension: result.vectors[0]?.length || 0,
        }),
      };
    } catch (error) {
      return {
        ok: false,
        message: t("site.runtime.provider_test_failed", {
          error: error instanceof Error ? error.message : String(error),
        }),
      };
    } finally {
      modelProgressListener = null;
    }
  }

  const embeddingNameHint = /embed|bge|e5|minilm|gte|nomic|mxbai|arctic|snowflake|sentence/i;

  async function discoverModels(
    profile: EndpointProfile,
    apiKey: string,
    role: "embedding" | "generation" = "generation",
  ): Promise<{ ok: boolean; message: string; models: DiscoveredModel[] }> {
    let base: string;
    try {
      base = providerBase(profile);
    } catch (error) {
      return {
        ok: false,
        message: error instanceof Error ? error.message : String(error),
        models: [],
      };
    }
    const endpoint = `${base}/models`;
    try {
      const body = await providerJson(endpoint, {
        method: "GET",
        headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
        cache: "no-store",
      });
      const models: DiscoveredModel[] = (body.data || [])
        .map((item) => {
          const model = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
          return {
            name: String(model.id || ""),
            detail: [model.owned_by].filter(Boolean).join(" · "),
          };
        })
        .filter((item: DiscoveredModel) => item.name);
      const unique: DiscoveredModel[] = [];
      const seen = new Set<string>();
      for (const model of models.sort((left, right) => left.name.localeCompare(right.name))) {
        if (seen.has(model.name)) continue;
        seen.add(model.name);
        unique.push(model);
      }
      const wantsEmbedding = role === "embedding";
      unique.sort(
        (left, right) =>
          Number(embeddingNameHint.test(right.name) === wantsEmbedding) -
          Number(embeddingNameHint.test(left.name) === wantsEmbedding),
      );
      return {
        ok: true,
        message: t("site.runtime.provider_ready"),
        models: unique,
      };
    } catch (error) {
      const providerFailure = error as ProviderError;
      if (providerFailure.code === "network" && (await noCorsReachabilityProbe(endpoint))) {
        const origin = location.origin === "null" ? t("site.runtime.file_origin") : location.origin;
        return {
          ok: false,
          message: t("site.runtime.provider_cors_blocked", { origin }),
          models: [],
        };
      }
      return {
        ok: false,
        message: t("site.runtime.provider_test_failed", {
          error: error instanceof Error ? error.message : String(error),
        }),
        models: [],
      };
    }
  }

  async function applySelections(embeddingId: string, generationId: string): Promise<void> {
    selectedEmbeddingId.value = embeddingId;
    selectedGenerationId.value = generationId;
    saveLocalModel();
    saveEndpoints();
    await rebuildClient();
  }

  async function addEndpoint(input: {
    name: string;
    baseUrl: string;
    model: string;
    apiKey: string;
    rememberKey: boolean;
    useForEmbeddings: boolean;
    useForAnswers: boolean;
  }): Promise<EndpointProfile> {
    let base = String(input.baseUrl || "").trim();
    try {
      base = new URL(base).href.replace(/\/$/, "");
    } catch {
      base = base.replace(/\/$/, "");
    }
    const raw: EndpointProfile = {
      id: `endpoint-${globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : Date.now()}`,
      name: String(input.name || "").trim(),
      base_url: base,
      model: String(input.model || "").trim(),
      remember_key: input.rememberKey && Boolean(input.apiKey),
    };
    const profile = normalizeEndpoint(raw);
    if (!profile || !profile.model) {
      throw new Error(
        profile
          ? t("site.runtime.provider_model_required")
          : t("site.runtime.provider_endpoint_invalid"),
      );
    }
    providerBase(profile);
    sessionApiKeys.set(profile.id, input.apiKey);
    endpoints.value = [...endpoints.value, profile];
    if (input.useForEmbeddings) selectedEmbeddingId.value = profile.id;
    if (input.useForAnswers) selectedGenerationId.value = profile.id;
    saveEndpoints();
    await rebuildClient();
    return profile;
  }

  async function removeEndpoint(id: string): Promise<void> {
    const profile = endpointById(id);
    if (!profile) return;
    endpoints.value = endpoints.value.filter((endpoint) => endpoint.id !== profile.id);
    sessionApiKeys.delete(profile.id);
    if (selectedEmbeddingId.value === profile.id) selectedEmbeddingId.value = "";
    if (selectedGenerationId.value === profile.id) selectedGenerationId.value = "";
    saveEndpoints();
    await rebuildClient();
  }

  async function buildIndex(
    options: {
      prepareLocalModel?: boolean;
      signal?: AbortSignal;
      onIndexProgress?: (indexed: number, total: number) => void;
      onModelProgress?: (info: ModelProgress) => void;
    } = {},
  ): Promise<LocalIndexStatus> {
    if (options.prepareLocalModel) {
      saveLocalModel();
      await rebuildClient();
    }
    if (!client.value) throw new Error(t("site.runtime.index_no_provider"));
    const stop = client.value.events.subscribe((event: ClientEvent) => {
      if (event.type === "index-progress") {
        options.onIndexProgress?.(Number(event.indexed || 0), Number(event.total || 0));
      }
    });
    modelProgressListener = options.onModelProgress || null;
    try {
      const result = await client.value.index.build({ signal: options.signal });
      await refreshCapabilities();
      return result;
    } finally {
      stop();
      modelProgressListener = null;
    }
  }

  async function clearIndex(): Promise<void> {
    if (!client.value) return;
    await client.value.index.clear();
    await refreshCapabilities();
  }

  function openRecord(record: PublicationRecord, searchedQuery = ""): void {
    recordDialog.value = { record, searchedQuery };
  }

  function closeRecord(): void {
    recordDialog.value = null;
  }

  const recordCount = computed(() =>
    (publication.works || []).reduce((sum, item) => sum + Number(item.record_count || 0), 0),
  );

  async function initialize(): Promise<void> {
    applyAppearance();
    await rebuildClient();
  }

  return {
    publication,
    publicationPackage,
    locale,
    theme,
    highContrast,
    availableLocales,
    view,
    tutorialSeen,
    searchWork,
    recordDialog,
    client,
    capabilities,
    endpoints,
    selectedEmbeddingId,
    selectedGenerationId,
    localModel,
    activeDevice,
    transformerSuggestions,
    recordCount,
    t,
    languageLabel,
    formatDate,
    filterFields,
    warningText,
    sourceEmbeddingModel,
    semanticReady,
    setLocaleAndRebuild,
    setTheme,
    setHighContrast,
    markTutorial,
    subscribeProgress,
    refreshCapabilities,
    updateLocalModel,
    testLocalModel,
    deleteModelCache,
    discoverModels,
    endpointById,
    applySelections,
    addEndpoint,
    removeEndpoint,
    buildIndex,
    clearIndex,
    openRecord,
    closeRecord,
    initialize,
  };
}

export type PublishedSiteContext = ReturnType<typeof createPublishedSiteContext>;

const contextKey = Symbol("published-site-context");

export function providePublishedSiteContext(context: PublishedSiteContext): void {
  provide(contextKey, context);
}

export function usePublishedSite(): PublishedSiteContext {
  const context = inject<PublishedSiteContext>(contextKey);
  if (!context) throw new Error("Published site context is unavailable.");
  return context;
}
