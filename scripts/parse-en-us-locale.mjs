/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * Parse api/app/locales/en_us.py into a {key: value} map.
 * Adjacent Python string literals are concatenated, matching the locale module.
 */
export function parseEnUsPy(text) {
  const start = text.indexOf("{");
  if (start < 0) throw new Error("EN_US dict not found");
  const body = text.slice(start);
  const map = {};
  const keyRe = /'((?:\\'|[^'])*)'\s*:/g;
  let match;
  while ((match = keyRe.exec(body))) {
    const key = match[1].replace(/\\'/g, "'");
    let i = keyRe.lastIndex;
    const parts = [];
    for (;;) {
      while (i < body.length && /\s/.test(body[i])) i += 1;
      const quote = body[i];
      if (quote !== "'" && quote !== '"') break;
      i += 1;
      let value = "";
      while (i < body.length) {
        if (body[i] === "\\" && i + 1 < body.length) {
          const next = body[i + 1];
          value += next === "n" ? "\n" : next === "t" ? "\t" : next;
          i += 2;
          continue;
        }
        if (body[i] === quote) {
          i += 1;
          break;
        }
        value += body[i];
        i += 1;
      }
      parts.push(value);
    }
    map[key] = parts.join("");
    keyRe.lastIndex = i;
  }
  return map;
}
