/* Copyright 2026 Aaron John Schlosser, PhD. */
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";

const root = resolve(process.cwd(), process.argv[2] || "storybook-static");
const host = process.argv[3] || "127.0.0.1";
const port = Number(process.argv[4] || 6006);

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".ico", "image/x-icon"],
  [".jpeg", "image/jpeg"],
  [".jpg", "image/jpeg"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".map", "application/json; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".txt", "text/plain; charset=utf-8"],
  [".webp", "image/webp"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
]);

function resolveRequestPath(requestUrl) {
  const pathname = decodeURIComponent(new URL(requestUrl || "/", "http://localhost").pathname);
  const relative = pathname.replace(/^\/+/, "") || "index.html";
  const candidate = resolve(root, relative);
  if (candidate !== root && !candidate.startsWith(root + sep)) return null;
  return candidate;
}

const server = createServer(async (request, response) => {
  try {
    let filePath = resolveRequestPath(request.url);
    if (!filePath) {
      response.writeHead(400);
      response.end("Bad request");
      return;
    }

    const metadata = await stat(filePath);
    if (metadata.isDirectory()) {
      filePath = resolve(filePath, "index.html");
    }

    const body = await readFile(filePath);
    response.writeHead(200, {
      "content-type":
        contentTypes.get(extname(filePath).toLowerCase()) || "application/octet-stream",
      "cache-control": "no-store",
    });
    response.end(body);
  } catch (error) {
    const code = error && typeof error === "object" && "code" in error ? error.code : undefined;
    response.writeHead(code === "ENOENT" ? 404 : 500);
    response.end(code === "ENOENT" ? "Not found" : "Internal server error");
  }
});

server.listen(port, host, () => {
  console.log(`Serving ${root} at http://${host}:${port}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
