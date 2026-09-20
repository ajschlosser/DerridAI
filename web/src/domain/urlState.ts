/* Copyright 2026 Aaron John Schlosser, PhD. */

// Compact, shareable URL encoding for table and search state. Extracted verbatim from the legacy
// runtime; the encoded form must stay stable because people keep links created by earlier builds.

function base64UrlEncodeBinary(binary: string): string {
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlDecodeBinary(token: unknown): string {
  let b64 = String(token || "")
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  while (b64.length % 4) b64 += "=";
  return atob(b64);
}

export function compressUrlState(value: unknown): string {
  try {
    // Table state is frequently small. Fixed-width LZW is excellent once column
    // and filter names repeat, but can expand a tiny payload. Generate both a
    // raw UTF-8 base64url form and the 12-bit LZW form and keep whichever is
    // shorter. The one-character prefix keeps decoding deterministic while the
    // legacy unprefixed LZW path in decompressUrlState preserves links created by early 0.23 builds.
    const bytes = new TextEncoder().encode(JSON.stringify(value));
    if (!bytes.length) return "";
    const input = String.fromCharCode(...bytes);
    const raw = `r${base64UrlEncodeBinary(input)}`;
    const dict = new Map<string, number>();
    for (let i = 0; i < 256; i++) dict.set(String.fromCharCode(i), i);
    let next = 256;
    let w = "";
    const codes: number[] = [];
    for (const c of input) {
      const wc = w + c;
      if (dict.has(wc)) {
        w = wc;
        continue;
      }
      if (w) codes.push(dict.get(w) as number);
      if (next < 4096) dict.set(wc, next++);
      w = c;
    }
    if (w) codes.push(dict.get(w) as number);
    const packed: number[] = [];
    let buffer = 0;
    let bits = 0;
    for (const code of codes) {
      buffer = (buffer << 12) | code;
      bits += 12;
      while (bits >= 8) {
        bits -= 8;
        packed.push((buffer >> bits) & 255);
        buffer &= (1 << bits) - 1;
      }
    }
    if (bits) packed.push((buffer << (8 - bits)) & 255);
    let binary = "";
    for (const byte of packed) binary += String.fromCharCode(byte);
    const compressed = `z${base64UrlEncodeBinary(binary)}`;
    return compressed.length < raw.length ? compressed : raw;
  } catch (error) {
    console.warn("Could not compress URL table state", error);
    return "";
  }
}

export function decompressUrlState(token: unknown): unknown {
  try {
    const source = String(token || "");
    if (!source) return null;
    if (source[0] === "r") {
      const raw = base64UrlDecodeBinary(source.slice(1));
      const bytes = Uint8Array.from(raw, (ch) => ch.charCodeAt(0));
      return JSON.parse(new TextDecoder().decode(bytes));
    }
    // `z` is the current compressed representation. No prefix means the link
    // came from the first 0.23 implementation and is decoded as legacy LZW.
    const encoded = source[0] === "z" ? source.slice(1) : source;
    const binary = base64UrlDecodeBinary(encoded);
    const codes: number[] = [];
    let buffer = 0;
    let bits = 0;
    for (let i = 0; i < binary.length; i++) {
      buffer = (buffer << 8) | binary.charCodeAt(i);
      bits += 8;
      while (bits >= 12) {
        bits -= 12;
        codes.push((buffer >> bits) & 4095);
        buffer &= (1 << bits) - 1;
      }
    }
    if (!codes.length) return null;
    const dict = new Map<number, string>();
    for (let i = 0; i < 256; i++) dict.set(i, String.fromCharCode(i));
    let next = 256;
    let w = dict.get(codes[0]);
    if (w == null) return null;
    let output = w;
    for (let i = 1; i < codes.length; i++) {
      const code = codes[i];
      let entry = dict.get(code);
      if (entry == null && code === next) entry = w + w[0];
      if (entry == null) return null;
      output += entry;
      if (next < 4096) dict.set(next++, w + entry[0]);
      w = entry;
    }
    const bytes = Uint8Array.from(output, (ch) => ch.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch (error) {
    console.warn("Could not decode URL table state", error);
    return null;
  }
}
