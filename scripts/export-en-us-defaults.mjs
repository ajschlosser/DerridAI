/* Copyright 2026 Aaron John Schlosser, PhD. */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parseEnUsPy } from "./parse-en-us-locale.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = fs.readFileSync(path.join(root, "api/app/locales/en_us.py"), "utf8");
const map = parseEnUsPy(source);
const keys = Object.keys(map);
if (keys.length < 3000) throw new Error(`parsed too few keys: ${keys.length}`);
const out = path.join(root, "web/src/i18n/enUsDefaults.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, `${JSON.stringify(map, null, 2)}\n`);
console.log(`wrote ${keys.length} keys to ${path.relative(root, out)}`);
