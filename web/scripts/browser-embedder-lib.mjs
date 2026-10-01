// Copyright 2026 Aaron John Schlosser, PhD.

export const ASSET_TABLE_MARKER = "/*__DERRIDAI_EMBEDDED_ASSETS__*/ {}";
export const EMBEDDER_INFO_MARKER = "/*__DERRIDAI_EMBEDDER_INFO__*/ {}";

export function jsonForModule(value) {
  return JSON.stringify(value)
    .replaceAll("<", "\\u003c")
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
}

function replaceExactlyOnce(source, marker, replacement) {
  const first = source.indexOf(marker);
  if (first < 0) {
    throw new Error(`Missing runtime marker: ${marker}`);
  }
  if (source.indexOf(marker, first + marker.length) >= 0) {
    throw new Error(`Runtime marker occurs more than once: ${marker}`);
  }
  return source.slice(0, first) + replacement + source.slice(first + marker.length);
}

export function renderBrowserEmbedderRuntime(template, assetTableSource, info) {
  const withAssets = replaceExactlyOnce(template, ASSET_TABLE_MARKER, assetTableSource);
  return replaceExactlyOnce(withAssets, EMBEDDER_INFO_MARKER, jsonForModule(info));
}

export function toBase64Chunks(bytes, chunkBytes = 786432) {
  if (!Number.isInteger(chunkBytes) || chunkBytes <= 0 || chunkBytes % 3 !== 0) {
    throw new Error("chunkBytes must be a positive multiple of 3.");
  }

  const buffer = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
  const chunks = [];
  for (let offset = 0; offset < buffer.length; offset += chunkBytes) {
    chunks.push(buffer.subarray(offset, offset + chunkBytes).toString("base64"));
  }
  return chunks;
}
