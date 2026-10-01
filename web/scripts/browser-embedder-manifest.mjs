// Copyright 2026 Aaron John Schlosser, PhD.

export const browserEmbedderManifest = Object.freeze({
  artifact: {
    id: "derridai-multilingual-embedder",
    formatVersion: 1,
    defaultOutput: "dist/derridai-multilingual-embedder.mjs",
  },
  runtime: {
    transformers: {
      version: "4.3.0",
      url: "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.0/dist/transformers.min.js",
      assetKey: "runtime/transformers.min.js",
      mediaType: "text/javascript",
      size: 581935,
      sha256: "1475fd440e9932ab206682ee42cb18f6097403e9ee77ea62084c592d0f83597d",
      license: "Apache-2.0",
      projectUrl: "https://github.com/huggingface/transformers.js",
    },
    onnxWasmFactory: {
      version: "1.31.0-dev.20260914-8d85527a0",
      url: "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.31.0-dev.20260914-8d85527a0/dist/ort-wasm-simd-threaded.mjs",
      assetKey: "runtime/ort-wasm-simd-threaded.mjs",
      mediaType: "text/javascript",
      size: 24381,
      sha256: "c57ca56328877353a575e51bbca6f18450027d6c9bf2307a2cb2c41363b4de9f",
      license: "MIT",
      projectUrl: "https://github.com/microsoft/onnxruntime",
    },
    onnxWasm: {
      version: "1.31.0-dev.20260914-8d85527a0",
      url: "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.31.0-dev.20260914-8d85527a0/dist/ort-wasm-simd-threaded.wasm",
      assetKey: "runtime/ort-wasm-simd-threaded.wasm",
      mediaType: "application/wasm",
      size: 14264838,
      sha256: "06ba057753da3847e4c24f02d91ab133455b0817c69a44993a9a53a2146df9e3",
      license: "MIT",
      projectUrl: "https://github.com/microsoft/onnxruntime",
    },
  },
  model: {
    id: "Xenova/multilingual-e5-small",
    upstreamId: "intfloat/multilingual-e5-small",
    revision: "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
    license: "MIT",
    dimensions: 384,
    maxLength: 512,
    dtype: "q8",
    device: "wasm",
    pooling: "mean",
    normalize: true,
    queryPrefix: "query: ",
    passagePrefix: "passage: ",
    files: [
      {
        path: "config.json",
        mediaType: "application/json",
      },
      {
        path: "tokenizer.json",
        mediaType: "application/json",
        size: 17082730,
        sha256: "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
      },
      {
        path: "tokenizer_config.json",
        mediaType: "application/json",
      },
      {
        path: "special_tokens_map.json",
        mediaType: "application/json",
      },
      {
        path: "onnx/model_quantized.onnx",
        mediaType: "application/octet-stream",
        size: 118308185,
        sha256: "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193",
      },
    ],
  },
});

export function modelFileUrl(path) {
  const { id, revision } = browserEmbedderManifest.model;
  return `https://huggingface.co/${id}/resolve/${revision}/${path}?download=true`;
}
