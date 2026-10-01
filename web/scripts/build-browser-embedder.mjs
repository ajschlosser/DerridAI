#!/usr/bin/env node
// Copyright 2026 Aaron John Schlosser, PhD.

import { createHash } from "node:crypto";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { mkdir, readFile, rename, rm } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { once } from "node:events";
import {
  ASSET_TABLE_MARKER,
  EMBEDDER_INFO_MARKER,
  jsonForModule,
} from "./browser-embedder-lib.mjs";
import { browserEmbedderManifest, modelFileUrl } from "./browser-embedder-manifest.mjs";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDir, "..");
const repoRoot = resolve(webRoot, "..");

function parseArgs(argv) {
  const options = {
    output: resolve(webRoot, browserEmbedderManifest.artifact.defaultOutput),
    cacheDir: resolve(repoRoot, "data/models/browser-embedder-cache"),
    refresh: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--refresh") {
      options.refresh = true;
      continue;
    }
    if (arg === "--output" || arg === "--cache-dir") {
      const value = argv[index + 1];
      if (!value) throw new Error(`${arg} requires a path.`);
      index += 1;
      const target = resolve(process.cwd(), value);
      if (arg === "--output") options.output = target;
      else options.cacheDir = target;
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return options;
}

function cachePath(cacheDir, key) {
  return resolve(cacheDir, ...key.split("/"));
}

async function sha256File(path) {
  const hash = createHash("sha256");
  let size = 0;
  for await (const chunk of createReadStream(path)) {
    hash.update(chunk);
    size += chunk.length;
  }
  return { sha256: hash.digest("hex"), size };
}

function verifyMetadata(asset, actual, label) {
  if (asset.size !== undefined && actual.size !== asset.size) {
    throw new Error(`${label} size mismatch: expected ${asset.size}, got ${actual.size}.`);
  }
  if (asset.sha256 && actual.sha256 !== asset.sha256) {
    throw new Error(`${label} SHA-256 mismatch: expected ${asset.sha256}, got ${actual.sha256}.`);
  }
}

async function downloadAsset(asset, cacheDir, refresh) {
  const destination = cachePath(cacheDir, asset.assetKey);
  await mkdir(dirname(destination), { recursive: true });

  if (existsSync(destination) && !refresh) {
    const actual = await sha256File(destination);
    try {
      verifyMetadata(asset, actual, asset.assetKey);
      return { ...asset, ...actual, path: destination };
    } catch {
      await rm(destination, { force: true });
    }
  }

  const temporary = `${destination}.partial-${process.pid}`;
  await rm(temporary, { force: true });

  const response = await fetch(asset.url, {
    redirect: "follow",
    headers: {
      "User-Agent": "DerridAI-browser-embedder-builder/1",
    },
  });
  if (!response.ok || !response.body) {
    throw new Error(
      `Failed to download ${asset.assetKey}: HTTP ${response.status} ${response.statusText}`,
    );
  }

  const output = createWriteStream(temporary, { flags: "wx" });
  const hash = createHash("sha256");
  let size = 0;

  try {
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = Buffer.from(value);
      hash.update(chunk);
      size += chunk.length;
      if (!output.write(chunk)) await once(output, "drain");
    }
    output.end();
    await once(output, "finish");

    const actual = { sha256: hash.digest("hex"), size };
    verifyMetadata(asset, actual, asset.assetKey);
    await rename(temporary, destination);
    return { ...asset, ...actual, path: destination };
  } catch (error) {
    output.destroy();
    await rm(temporary, { force: true });
    throw error;
  }
}

function sourceAssets() {
  const { runtime, model } = browserEmbedderManifest;
  return [
    {
      assetKey: runtime.transformers.assetKey,
      url: runtime.transformers.url,
      mediaType: runtime.transformers.mediaType,
    },
    {
      assetKey: runtime.onnxWasm.assetKey,
      url: runtime.onnxWasm.url,
      mediaType: runtime.onnxWasm.mediaType,
    },
    ...model.files.map((file) => ({
      ...file,
      assetKey: `model/${file.path}`,
      url: modelFileUrl(file.path),
    })),
  ];
}

function buildInfo(downloaded) {
  const byKey = new Map(downloaded.map((asset) => [asset.assetKey, asset]));
  const { artifact, runtime, model } = browserEmbedderManifest;

  return {
    artifact: {
      id: artifact.id,
      formatVersion: artifact.formatVersion,
      selfContained: true,
      runtimeNetworkRequired: false,
    },
    runtime: {
      transformers: {
        version: runtime.transformers.version,
        sha256: byKey.get(runtime.transformers.assetKey).sha256,
        size: byKey.get(runtime.transformers.assetKey).size,
        license: runtime.transformers.license,
        projectUrl: runtime.transformers.projectUrl,
      },
      onnxWasm: {
        sha256: byKey.get(runtime.onnxWasm.assetKey).sha256,
        size: byKey.get(runtime.onnxWasm.assetKey).size,
      },
    },
    model: {
      id: model.id,
      upstreamId: model.upstreamId,
      revision: model.revision,
      license: model.license,
      dimensions: model.dimensions,
      maxLength: model.maxLength,
      dtype: model.dtype,
      device: model.device,
      pooling: model.pooling,
      normalize: model.normalize,
      queryPrefix: model.queryPrefix,
      passagePrefix: model.passagePrefix,
      files: model.files.map((file) => {
        const asset = byKey.get(`model/${file.path}`);
        return {
          path: file.path,
          sha256: asset.sha256,
          size: asset.size,
        };
      }),
    },
  };
}

async function writeChunk(stream, chunk) {
  if (!stream.write(chunk)) await once(stream, "drain");
}

async function writeAssetTable(stream, downloaded) {
  await writeChunk(stream, "{");
  for (let index = 0; index < downloaded.length; index += 1) {
    const asset = downloaded[index];
    if (index > 0) await writeChunk(stream, ",");

    await writeChunk(
      stream,
      `${jsonForModule(asset.assetKey)}:{"mediaType":${jsonForModule(
        asset.mediaType,
      )},"size":${asset.size},"sha256":${jsonForModule(asset.sha256)},"chunks":[`,
    );

    let firstChunk = true;
    for await (const chunk of createReadStream(asset.path, {
      highWaterMark: 786432,
    })) {
      if (!firstChunk) await writeChunk(stream, ",");
      firstChunk = false;
      await writeChunk(stream, jsonForModule(chunk.toString("base64")));
    }
    await writeChunk(stream, "]}");
  }
  await writeChunk(stream, "}");
}

async function writeArtifact(template, downloaded, info, outputPath) {
  const assetMarkerIndex = template.indexOf(ASSET_TABLE_MARKER);
  const infoMarkerIndex = template.indexOf(EMBEDDER_INFO_MARKER);
  if (assetMarkerIndex < 0 || infoMarkerIndex < 0 || infoMarkerIndex <= assetMarkerIndex) {
    throw new Error("Browser embedder runtime template markers are missing or out of order.");
  }

  const beforeAssets = template.slice(0, assetMarkerIndex);
  const between = template.slice(assetMarkerIndex + ASSET_TABLE_MARKER.length, infoMarkerIndex);
  const afterInfo = template.slice(infoMarkerIndex + EMBEDDER_INFO_MARKER.length);

  await mkdir(dirname(outputPath), { recursive: true });
  const temporary = `${outputPath}.partial-${process.pid}`;
  await rm(temporary, { force: true });

  const output = createWriteStream(temporary, { encoding: "utf8", flags: "wx" });
  try {
    await writeChunk(output, beforeAssets);
    await writeAssetTable(output, downloaded);
    await writeChunk(output, between);
    await writeChunk(output, jsonForModule(info));
    await writeChunk(output, afterInfo);
    output.end();
    await once(output, "finish");
    await rename(temporary, outputPath);
  } catch (error) {
    output.destroy();
    await rm(temporary, { force: true });
    throw error;
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const assets = sourceAssets();

  console.log(
    `Building ${browserEmbedderManifest.artifact.id} with Transformers.js ${browserEmbedderManifest.runtime.transformers.version} and ${browserEmbedderManifest.model.id}.`,
  );

  const downloaded = [];
  for (const asset of assets) {
    process.stdout.write(`  acquiring ${asset.assetKey} ... `);
    const result = await downloadAsset(asset, options.cacheDir, options.refresh);
    downloaded.push(result);
    console.log(`${(result.size / (1024 * 1024)).toFixed(2)} MiB`);
  }

  const template = await readFile(resolve(scriptDir, "browser-embedder-runtime.mjs"), "utf8");
  const info = buildInfo(downloaded);
  await writeArtifact(template, downloaded, info, options.output);

  const artifact = await sha256File(options.output);
  const displayPath = relative(process.cwd(), options.output) || options.output;
  console.log(
    `Created ${displayPath} (${(artifact.size / (1024 * 1024)).toFixed(
      2,
    )} MiB, SHA-256 ${artifact.sha256}).`,
  );
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : error);
  process.exitCode = 1;
});
