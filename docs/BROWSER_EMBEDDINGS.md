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

# Browser-native multilingual embeddings

DerridAI can build a single ECMAScript module that contains the complete text-embedding runtime: Transformers.js, ONNX Runtime WebAssembly, the multilingual tokenizer/configuration, and a pinned quantized ONNX model. The generated module performs inference entirely in the browser and blocks unexpected runtime network requests.

This artifact is deliberately separate from DerridAI's canonical corpus state. Embeddings remain a derived, rebuildable projection. Adopting this runtime for an existing vector store therefore requires an explicit embedding-compatibility migration rather than silently mixing vectors produced by different models or preprocessing contracts.

## Build

From `web/`:

```bash
npm run build:browser-embedder
```

The builder downloads the pinned inputs into `data/models/browser-embedder-cache/`, validates the known large-file SHA-256 digests, computes provenance for every embedded asset, and writes:

```text
web/dist/derridai-multilingual-embedder.mjs
```

Both locations are already covered by DerridAI's ignored runtime/build-data paths. The generated artifact is intentionally not committed.

Use `--refresh` to replace the build cache, or invoke the script directly to choose another output path:

```bash
node scripts/build-browser-embedder.mjs \
  --output /tmp/derridai-multilingual-embedder.mjs \
  --refresh
```

The build step requires network access. The generated module does not.

## Pinned semantic contract

The initial browser profile uses:

- `@huggingface/transformers` 4.3.0;
- `Xenova/multilingual-e5-small` at revision `761b726dd34fb83930e26aab4e9ac3899aa1fa78`;
- the q8 `onnx/model_quantized.onnx` model;
- 384-dimensional vectors;
- a maximum model sequence length of 512 tokens;
- mean pooling followed by L2 normalization;
- `query: ` and `passage: ` prefixes for retrieval;
- ONNX Runtime WASM with one runtime thread and no proxy worker.

The model is multilingual and places supported languages in one embedding space. No translation is inserted into the embedding path. DerridAI preserves the caller's text exactly and adds only the retrieval prefix selected by the API.

The generated `EMBEDDER_INFO` object records the model revision, model/runtime file sizes, SHA-256 digests, dimensions, pooling/normalization policy, prefixes, and runtime versions. Persist that information with any derived embedding index that depends on this artifact.

## Runtime API

Serve or otherwise import the generated module as an ES module:

```js
import { EMBEDDER_INFO, load } from "./derridai-multilingual-embedder.mjs";

const embedder = await load();

const query = await embedder.embedQuery("Qu’est-ce que la trace ?");

const documents = await embedder.embedDocuments([
  "Die Spur ist nicht einfach eine Anwesenheit.",
  "La trace n’est pas simplement une présence.",
]);

console.log(EMBEDDER_INFO.model.id);
console.log(query.length); // 384
console.log(documents.length); // 2
```

The lower-level method is available when the caller already owns task-specific prefixing:

```js
const vectors = await embedder.embed(["query: trace", "passage: la trace"], {
  mode: "raw",
  batchSize: 8,
});
```

`embedQuery()` and `embedDocuments()` are preferred for retrieval because they make the E5 query/document distinction explicit.

## Offline boundary

At runtime the module:

1. imports its embedded Transformers.js bundle from memory;
2. supplies the embedded ONNX Runtime WASM binary directly;
3. installs an in-memory fetch implementation for the pinned model files;
4. initializes the feature-extraction pipeline against a virtual, non-routable model origin;
5. throws if Transformers.js attempts any request outside that virtual model origin.

There is therefore no Hugging Face, jsDelivr, npm, API, or DerridAI backend request required to produce an embedding after the single module has been built and distributed.

This is intentionally stricter than relying on the browser HTTP cache: missing embedded assets fail closed instead of silently falling back to the network.

## Browser and packaging considerations

The single-file format trades deployment simplicity for size and peak memory. The q8 model is about 118 MB and the multilingual tokenizer about 17 MB before base64 packaging, in addition to the Transformers.js/ONNX runtime. The generated JavaScript module will consequently be substantially larger than those raw assets.

The first profile uses WASM rather than WebGPU so the same artifact has a broad browser execution path and does not need a second fp16 model. A future WebGPU profile should be a separately versioned embedding contract because changing dtype/runtime behavior can affect vector compatibility.

The runtime uses an in-memory module URL for the embedded Transformers.js code. Deployments with a restrictive Content Security Policy must allow the applicable `blob:` module source, or the packaging strategy must be adapted to that policy.

## Internationalization

Semantic multilingual support and UI localization are separate concerns. This module addresses semantic multilingual embeddings only. It does not replace DerridAI's `en-US` / `fr-CA` UI locale contract, locale formatting, bidirectional-layout support, or accessibility requirements.

Cross-language retrieval should be evaluated on representative project languages before an index migration. A model being multilingual does not imply equal retrieval quality across every language or domain.

## Validation

Unit coverage uses a synthetic embedded Transformers.js module and model asset to verify the single-file virtual filesystem, E5 query/passage prefixing, pooling/normalization options, WASM configuration, input-text preservation, disposal, and fail-closed loading behavior without downloading the production model during normal frontend CI.

A production artifact build is a separate acceptance step because it downloads more than 100 MB of pinned model/runtime data. For release or deployment, build the artifact once, record the emitted SHA-256 digest, then run a browser smoke test using the real generated file before publishing it.
