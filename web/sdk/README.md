<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# DerridAI SDK

The DerridAI SDK is the framework-neutral research library used by published DerridAI sites and custom “bring your own site” integrations. It is written in TypeScript and can be consumed either as an ESM package with declarations or as the browser IIFE exposed as `globalThis.DerridAI`.

The SDK is not the DerridAI Published Site Runtime. A published site's runtime is the complete browser execution package: publication data, this SDK, the optional DerridAI reference interface, and browser dependencies required by enabled features. The SDK can be used independently of that generated-site runtime and independently of `derridai-site.js`.

The SDK owns publication semantics, progressive Record loading, filtering, lexical/semantic/hybrid retrieval, embedding-contract validation, MMR diversification, evidence-packet construction, deterministic citation resolution, annotations, and Research orchestration. It does not render DOM and does not require Vue, React, Pinia, Vue Router, or the DerridAI application frontend.

Contributors should keep the SDK framework-neutral and side-effect boundaries explicit. Pure retrieval/math helpers should use descriptive names even when implementing standard formulas; provider and storage effects belong behind the existing interfaces. See [`docs/CODE_READABILITY.md`](../../docs/CODE_READABILITY.md) and the frontend validation commands in [`web/README.md`](../README.md).

AI execution is transport-neutral. A host application injects embedding and generation capabilities as TypeScript/JavaScript objects. The SDK does not accept an API endpoint or API key and does not make direct browser-to-model-provider requests.

The publication's own vectors are used only when the injected embedding model is exactly the model that embedded the publication (`matchesPublicationModel`). Any other embedding model searches a local index instead: `client.index.build()` embeds the published Records with the injected provider, stores the vectors through the optional `vectorIndex` store (IndexedDB by default, memory when unavailable) keyed by publication and exact model, and `client.index.status()` / `client.index.clear()` inspect and remove it. Until the index is complete, semantic and hybrid search return keyword results with a `local_index_required` warning.

## TypeScript / ESM

Build the package from the repository root:

```bash
cd web
npm run build:sdk:package
```

The package metadata lives at `web/sdk/package.json`, and the build emits ESM JavaScript plus `.d.ts` declarations to `web/sdk/dist`. To create an installable tarball:

```bash
cd web
npm run pack:sdk
```

A consuming Web application can then install that tarball (or a published `@derridai/sdk` package) and use normal TypeScript imports:

```ts
import {
  createClient,
  dataSources,
  type EmbeddingProvider,
  type GenerationProvider,
} from "@derridai/sdk";

const embeddings: EmbeddingProvider = {
  descriptor: () => ({ type: "host", model: "bge-m3:latest" }),
  async embed(input, { signal } = {}) {
    return hostAI.embed(input, { signal });
  },
};

const generation: GenerationProvider = {
  descriptor: () => ({ type: "host", model: "qwen3:8b" }),
  async generate(request, { signal } = {}) {
    return hostAI.generate(request, { signal });
  },
};

const client = await createClient({
  dataSource: dataSources.inline(publicationPackage),
  embeddings,
  generation,
});

const search = await client.search({
  query: "unconditional hospitality",
  mode: "hybrid",
  filters: { work: ["Of Hospitality"] },
});

const research = await client.research({
  question: "How does Derrida distinguish conditional from unconditional hospitality?",
  retrieval: {
    mode: "hybrid",
    limit: 24, // k: ranked Records retained after retrieval
    fetchLimit: 500, // fetch_k: candidates considered before final ranking
    evidenceLimit: 10, // top_n: diversified evidence Records sent to generation
    mmrLambda: 0.72,
    filters: { work: ["Of Hospitality", "Adieu to Emmanuel Levinas"] },
  },
});
```

Any framework can wrap the same client. React, Vue, Svelte, Solid, plain DOM code, Electron/Tauri shells, and server-backed Web applications do not require framework-specific DerridAI adapters.

## Runtime guarantees

Search deduplicates transport-level duplicate rows by stable `record_id` before scoring. The first encountered Record remains authoritative for that search, and `response.diagnostics.duplicatesRemoved` reports how many duplicate identities were suppressed. Records with different IDs are never collapsed merely because their text is identical.

Semantic retrieval validates the publication embedding contract against an injected provider when both sides declare comparable metadata. Model and revision mismatches produce `embedding_contract_mismatch`; vector-size mismatches produce `embedding_dimension_mismatch`. Missing optional descriptor metadata is not treated as a mismatch.

Cancellation remains distinct from provider failure. An `AbortError` raised while loading Records, embedding a query, or generating an answer is rethrown and causes the client to emit `operation-cancelled`; it is not converted into keyword fallback or `generation_unavailable`.

Research emits separate retrieval, evidence-selection, and generation events. Hosts can therefore report progress without treating generation as one opaque wait. `SearchRequest.fetchLimit` and `ResearchRequest.retrieval.fetchLimit` bound the lexical/semantic candidate pool when applicable; leaving them unset preserves the SDK's previous unbounded local-candidate behavior.

## Browser script

The browser distribution is built with:

```bash
cd web
npm run build:sdk
```

It writes `api/app/site_assets/derridai-sdk.js` and exposes `globalThis.DerridAI`:

```html
<script src="./derridai-publication.js"></script>
<script src="./derridai-sdk.js"></script>
<script>
  const client = await DerridAI.createClient({
    dataSource: DerridAI.dataSources.inline(window.__DERRIDAI_SITE_PACKAGE__),
    embeddings: window.myHost?.embeddings,
    generation: window.myHost?.generation,
  });
</script>
```

The generated DerridAI reference site consumes this same public SDK. The SDK is therefore not an alternate implementation path: it is the research engine shared by the built-in site and bring-your-own-site applications.
