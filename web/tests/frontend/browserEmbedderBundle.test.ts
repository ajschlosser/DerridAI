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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  renderBrowserEmbedderRuntime,
  toBase64Chunks,
} from "../../scripts/browser-embedder-lib.mjs";

const MODEL_REVISION = "test-revision";
let runtimeInstance = 0;

function asset(bytes: Uint8Array | Buffer | string, mediaType: string) {
  const buffer = typeof bytes === "string" ? Buffer.from(bytes) : Buffer.from(bytes);
  return {
    mediaType,
    size: buffer.length,
    sha256: "test",
    chunks: toBase64Chunks(buffer),
  };
}

async function importTestRuntime() {
  runtimeInstance += 1;
  const fakeTransformers = `
    // synthetic runtime ${runtimeInstance}
    export const env = {
      allowLocalModels: true,
      allowRemoteModels: false,
      remoteHost: "",
      remotePathTemplate: "",
      useBrowserCache: true,
      useFSCache: true,
      useCustomCache: true,
      useWasmCache: true,
      fetch: globalThis.fetch,
      backends: { onnx: { wasm: { wasmPaths: "remote" } } },
    };

    const state = globalThis.__derridaiBrowserEmbedderTestState = {
      calls: [],
      fetched: [],
      env,
      pipelineOptions: null,
    };

    export async function pipeline(task, model, options) {
      state.pipelineOptions = { task, model, ...options };
      const configUrl = env.remoteHost + model + "/resolve/main/config.json";
      const response = await env.fetch(configUrl);
      if (!response.ok) throw new Error("Embedded config was not available.");
      state.fetched.push({
        url: configUrl,
        config: await response.json(),
      });

      const extractor = async (texts, inferenceOptions) => {
        state.calls.push({ texts: [...texts], inferenceOptions });
        return {
          tolist() {
            return texts.map((text) => {
              const vector = new Array(384).fill(0);
              vector[0] = text.startsWith("query: ") ? 1 : text.startsWith("passage: ") ? 2 : 3;
              vector[1] = text.length;
              return vector;
            });
          },
        };
      };
      extractor.dispose = async () => {
        state.disposed = true;
      };
      return extractor;
    }
  `;

  const assets = {
    "runtime/transformers.min.js": asset(fakeTransformers, "text/javascript"),
    "runtime/ort-wasm-simd-threaded.mjs": asset(
      "export default async function createWasm() { return {}; }",
      "text/javascript",
    ),
    "runtime/ort-wasm-simd-threaded.wasm": asset(
      new Uint8Array([0, 97, 115, 109]),
      "application/wasm",
    ),
    "model/config.json": asset(JSON.stringify({ model_type: "bert" }), "application/json"),
  };

  const info = {
    artifact: {
      id: "test-browser-embedder",
      formatVersion: 1,
      selfContained: true,
      runtimeNetworkRequired: false,
    },
    runtime: {
      transformers: { version: "test" },
      onnxWasmFactory: { version: "test" },
      onnxWasm: { version: "test" },
    },
    model: {
      id: "Xenova/multilingual-e5-small",
      upstreamId: "intfloat/multilingual-e5-small",
      revision: MODEL_REVISION,
      license: "MIT",
      dimensions: 384,
      maxLength: 512,
      dtype: "q8",
      device: "wasm",
      pooling: "mean",
      normalize: true,
      queryPrefix: "query: ",
      passagePrefix: "passage: ",
      files: [],
    },
  };

  const template = await readFile(
    resolve(process.cwd(), "scripts/browser-embedder-runtime.mjs"),
    "utf8",
  );
  const source =
    renderBrowserEmbedderRuntime(template, JSON.stringify(assets), info) +
    `\n// synthetic module ${runtimeInstance}\n`;
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  return import(/* @vite-ignore */ moduleUrl);
}

afterEach(() => {
  delete (
    globalThis as typeof globalThis & {
      __derridaiBrowserEmbedderTestState?: unknown;
    }
  ).__derridaiBrowserEmbedderTestState;
});

describe("self-contained browser embedder runtime", () => {
  it("serves model assets from memory and applies multilingual E5 retrieval prefixes", async () => {
    const runtime = await importTestRuntime();
    const embedder = await runtime.createEmbedder();

    const query = await embedder.embedQuery("Qu’est-ce que la trace ?");
    const documents = await embedder.embedDocuments([
      "Die Spur ist nicht einfach eine Anwesenheit.",
      "La trace n’est pas simplement une présence.",
    ]);

    expect(query).toBeInstanceOf(Float32Array);
    expect(query).toHaveLength(384);
    expect(query[0]).toBe(1);
    expect(documents).toHaveLength(2);
    expect(documents[0][0]).toBe(2);

    const state = (
      globalThis as typeof globalThis & {
        __derridaiBrowserEmbedderTestState: {
          calls: Array<{
            texts: string[];
            inferenceOptions: { pooling: string; normalize: boolean };
          }>;
          fetched: Array<{ url: string; config: { model_type: string } }>;
          env: {
            allowLocalModels: boolean;
            allowRemoteModels: boolean;
            useBrowserCache: boolean;
            useFSCache: boolean;
            useCustomCache: boolean;
            useWasmCache: boolean;
            backends: {
              onnx: {
                wasm: {
                  numThreads: number;
                  proxy: boolean;
                  wasmBinary?: Uint8Array;
                  wasmPaths: { mjs: string; wasm: string };
                };
              };
            };
          };
          pipelineOptions: {
            task: string;
            model: string;
            revision: string;
            dtype: string;
            device: string;
          };
        };
      }
    ).__derridaiBrowserEmbedderTestState;

    expect(state.calls[0].texts).toEqual(["query: Qu’est-ce que la trace ?"]);
    expect(state.calls[1].texts).toEqual([
      "passage: Die Spur ist nicht einfach eine Anwesenheit.",
      "passage: La trace n’est pas simplement une présence.",
    ]);
    expect(state.calls[0].inferenceOptions).toEqual({
      pooling: "mean",
      normalize: true,
    });
    expect(state.fetched[0].config).toEqual({ model_type: "bert" });
    expect(state.pipelineOptions).toMatchObject({
      task: "feature-extraction",
      model: "Xenova/multilingual-e5-small",
      revision: MODEL_REVISION,
      dtype: "q8",
      device: "wasm",
    });

    expect(state.env.allowLocalModels).toBe(false);
    expect(state.env.allowRemoteModels).toBe(true);
    expect(state.env.useBrowserCache).toBe(false);
    expect(state.env.useFSCache).toBe(false);
    expect(state.env.useCustomCache).toBe(false);
    expect(state.env.useWasmCache).toBe(false);
    expect(state.env.backends.onnx.wasm.numThreads).toBe(1);
    expect(state.env.backends.onnx.wasm.proxy).toBe(false);
    expect(state.env.backends.onnx.wasm.wasmBinary).toBeUndefined();
    expect(state.env.backends.onnx.wasm.wasmPaths.mjs).toMatch(/^(blob:|data:)/);
    expect(state.env.backends.onnx.wasm.wasmPaths.wasm).toMatch(/^(blob:|data:)/);

    await embedder.dispose();
  });

  it("preserves input text and rejects invalid runtime requests", async () => {
    const runtime = await importTestRuntime();
    const embedder = await runtime.createEmbedder();

    const raw = await embedder.embed(["  déjà vu  "], {
      mode: "raw",
      batchSize: 1,
    });
    expect(raw[0][0]).toBe(3);

    const state = (
      globalThis as typeof globalThis & {
        __derridaiBrowserEmbedderTestState: {
          calls: Array<{ texts: string[] }>;
        };
      }
    ).__derridaiBrowserEmbedderTestState;
    expect(state.calls[0].texts).toEqual(["  déjà vu  "]);

    await expect(embedder.embed(["test"], { mode: "unsupported" })).rejects.toThrow(/mode/);
    await expect(embedder.embed(["test"], { batchSize: 0 })).rejects.toThrow(/batchSize/);

    await embedder.dispose();
    await expect(embedder.embedQuery("test")).rejects.toThrow(/disposed/);
  });
});
