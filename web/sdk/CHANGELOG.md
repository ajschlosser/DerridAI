<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI Publication Runtime changelog

## Unreleased

- Rename the product from "DerridAI Publication Runtime" to "DerridAI Publication Runtime". The npm package is now `@derridai/publication-runtime` (was `@derridai/publication-runtime`); the `web/sdk` directory, `derridai-sdk.js` asset name, and `globalThis.DerridAI` export are unchanged.
- Remove the author-specific name from the built-in research prompt; it now refers to "the document author".

## 0.1.1

- Preserve cancellation as cancellation across Record loading, embedding, and generation instead of degrading aborted operations into provider fallback warnings.
- Validate explicitly declared embedding model and revision metadata before semantic retrieval, and validate returned embedding provenance when supplied.
- Deduplicate retrieval candidates deterministically by stable `record_id` before scoring and expose `duplicatesRemoved` in search diagnostics.
- Add an external-consumer packaging gate that installs the packed Publication Runtime into a separate TypeScript/Vite application and exercises Search and Research.

## 0.1.0

- Initial framework-neutral Publication Runtime release with inline/HTTP publication data sources, keyword/semantic/hybrid retrieval, MMR, evidence packets, citations, annotations, and injected embedding/generation capabilities.
