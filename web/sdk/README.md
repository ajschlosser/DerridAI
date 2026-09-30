<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI SDK

The DerridAI SDK is the headless browser research library used by published DerridAI sites and by custom “bring your own site” integrations.

The SDK owns publication semantics, progressive Record loading, filtering, lexical/semantic/hybrid retrieval, MMR diversification, evidence-packet construction, deterministic citation resolution, annotations, and Research orchestration. It does not render DOM and does not require Vue, React, Pinia, Vue Router, or the DerridAI application frontend.

AI execution is transport-neutral. A host application injects embedding and generation capabilities as TypeScript/JavaScript objects. The SDK does not accept an API endpoint or API key and does not make direct browser-to-model-provider requests.

## Minimal usage

```ts
import { createClient, dataSources } from "./src";

const client = await createClient({
  dataSource: dataSources.inline(publicationPackage),
  embeddings: {
    descriptor: () => ({ type: "host", model: "bge-m3:latest" }),
    async embed(input, { signal } = {}) {
      return hostAI.embed(input, { signal });
    },
  },
  generation: {
    descriptor: () => ({ type: "host", model: "qwen3:8b" }),
    async generate(request, { signal } = {}) {
      return hostAI.generate(request, { signal });
    },
  },
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

The IIFE distribution is built with:

```bash
cd web
npm run build:sdk
```

and exposes `globalThis.DerridAI`. The generated artifact is written to `api/app/site_assets/derridai-sdk.js` so the publication builder can package the same SDK used by the reference published-site UI.
