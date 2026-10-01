<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI SDK

The DerridAI SDK is the framework-neutral research library used by published DerridAI sites and custom “bring your own site” integrations. It is written in TypeScript and can be consumed either as an ESM package with declarations or as the browser IIFE exposed as `globalThis.DerridAI`.

The SDK owns publication semantics, progressive Record loading, filtering, lexical/semantic/hybrid retrieval, embedding-contract validation, MMR diversification, evidence-packet construction, deterministic citation resolution, annotations, and Research orchestration. It does not render DOM and does not require Vue, React, Pinia, Vue Router, or the DerridAI application frontend.

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
});
```

Any framework can wrap the same client. React, Vue, Svelte, Solid, plain DOM code, Electron/Tauri shells, and server-backed Web applications do not require framework-specific DerridAI adapters.

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
