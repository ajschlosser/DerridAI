#!/usr/bin/env node
// Copyright 2026 Aaron John Schlosser, PhD.

import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDir, "..");
const artifactPath = resolve(webRoot, "dist/derridai-multilingual-embedder.mjs");

const pageHtml = `<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>DerridAI browser embedder smoke test</title></head>
  <body>
    <script type="module">
      globalThis.__derridaiSmoke = { done: false };
      try {
        const { createEmbedder, EMBEDDER_INFO } = await import("/embedder.mjs");
        const embedder = await createEmbedder();
        const query = await embedder.embedQuery("un chat assis sur un tapis");
        const documents = await embedder.embedDocuments([
          "a cat is sitting on a mat",
          "quantum field equations describe particle interactions",
        ]);

        const dot = (left, right) => {
          let total = 0;
          for (let index = 0; index < left.length; index += 1) {
            total += left[index] * right[index];
          }
          return total;
        };

        globalThis.__derridaiSmoke = {
          done: true,
          dimensions: EMBEDDER_INFO.model.dimensions,
          queryLength: query.length,
          documentLengths: documents.map((vector) => vector.length),
          relatedScore: dot(query, documents[0]),
          unrelatedScore: dot(query, documents[1]),
          runtimeNetworkRequired: EMBEDDER_INFO.artifact.runtimeNetworkRequired,
          model: EMBEDDER_INFO.model.id,
          revision: EMBEDDER_INFO.model.revision,
        };
        await embedder.dispose();
      } catch (error) {
        globalThis.__derridaiSmoke = {
          done: true,
          error: error instanceof Error ? error.stack || error.message : String(error),
        };
      }
    </script>
  </body>
</html>`;

async function listen(server) {
  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolveListen(server.address()));
  });
}

async function closeServer(server) {
  return new Promise((resolveClose) => server.close(() => resolveClose()));
}

async function main() {
  const artifact = await stat(artifactPath);
  if (!artifact.isFile() || artifact.size === 0) {
    throw new Error("Browser embedder artifact is missing or empty.");
  }

  const server = createServer((request, response) => {
    if (request.url === "/" || request.url === "/index.html") {
      response.writeHead(200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
      });
      response.end(pageHtml);
      return;
    }

    if (request.url === "/embedder.mjs") {
      response.writeHead(200, {
        "Content-Type": "text/javascript; charset=utf-8",
        "Content-Length": String(artifact.size),
        "Cache-Control": "no-store",
      });
      createReadStream(artifactPath).pipe(response);
      return;
    }

    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
  });

  const address = await listen(server);
  if (!address || typeof address === "string") {
    await closeServer(server);
    throw new Error("Could not determine browser smoke-test server address.");
  }

  const origin = `http://127.0.0.1:${address.port}`;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const externalRequests = [];

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol === "http:" || url.protocol === "https:") {
      if (url.origin !== origin) externalRequests.push(url.href);
    }
  });

  try {
    await page.goto(origin, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => globalThis.__derridaiSmoke?.done === true, undefined, {
      timeout: 240_000,
    });

    const result = await page.evaluate(() => globalThis.__derridaiSmoke);
    if (result.error) throw new Error(result.error);
    if (result.dimensions !== 384 || result.queryLength !== 384) {
      throw new Error(`Unexpected embedding dimensions: ${JSON.stringify(result)}`);
    }
    if (result.documentLengths.some((length) => length !== 384)) {
      throw new Error(`Unexpected document dimensions: ${JSON.stringify(result)}`);
    }
    if (!(result.relatedScore > result.unrelatedScore)) {
      throw new Error(`Cross-language retrieval smoke check failed: ${JSON.stringify(result)}`);
    }
    if (result.runtimeNetworkRequired !== false) {
      throw new Error("Generated embedder does not declare an offline runtime.");
    }
    if (externalRequests.length) {
      throw new Error(`Generated embedder made external requests: ${externalRequests.join(", ")}`);
    }

    console.log(JSON.stringify(result, null, 2));
  } finally {
    await page.close();
    await browser.close();
    await closeServer(server);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : error);
  process.exitCode = 1;
});
