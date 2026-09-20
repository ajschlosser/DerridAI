/* Copyright 2026 Aaron John Schlosser, PhD. */
import { esc } from "./html";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Text highlighting, snippets and model/similarity display helpers, moved verbatim from the legacy runtime.

export function highlight(text: unknown, query: unknown): string {
  const s = String(text ?? ""),
    q = String(query ?? "");
  if (!q) return esc(s);
  const low = s.toLocaleLowerCase(),
    needle = q.toLocaleLowerCase();
  let out = "",
    pos = 0,
    i;
  while ((i = low.indexOf(needle, pos)) >= 0) {
    out += esc(s.slice(pos, i)) + "<mark>" + esc(s.slice(i, i + q.length)) + "</mark>";
    pos = i + Math.max(1, q.length);
  }
  return out + esc(s.slice(pos));
}

export function highlightTerms(text: unknown, query: unknown): string {
  const source = String(text ?? "");
  const terms = [
    ...new Set(
      String(query ?? "")
        .trim()
        .split(/\s+/)
        // eslint-disable-next-line no-useless-escape -- SA-14: preserve legacy matching until dedicated text fixtures cover it.
        .map((term) => term.replace(/^["'()\[\]{}]+|["'()\[\]{},.;:!?]+$/g, ""))
        .filter((term) => term.length > 1),
    ),
  ].sort((a, b) => b.length - a.length);
  if (!terms.length) return esc(source);
  const pattern = new RegExp(
    `(${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`,
    "gi",
  );
  let out = "",
    last = 0,
    match;
  while ((match = pattern.exec(source))) {
    out += esc(source.slice(last, match.index)) + `<mark>${esc(match[0])}</mark>`;
    last = match.index + match[0].length;
    if (!match[0].length) pattern.lastIndex++;
  }
  return out + esc(source.slice(last));
}

export function snippet(text: unknown, query?: string | null, max: number = 430): string {
  const s = String(text ?? "")
    .replace(/\s+/g, " ")
    .trim();
  if (!s) return "";
  if (!query) return s.length > max ? s.slice(0, max) + "…" : s;
  const i = s.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  if (i < 0) return s.length > max ? s.slice(0, max) + "…" : s;
  const a = Math.max(0, i - Math.floor(max / 2)),
    b = Math.min(s.length, a + max);
  return (a ? "…" : "") + s.slice(a, b) + (b < s.length ? "…" : "");
}

export function semanticSimilarity(distance: unknown): number | null {
  const d = Number(distance);
  if (!Number.isFinite(d)) return null;
  // Chroma distances are not calibrated probabilities. This monotonic transform
  // provides an intuitive 0..1 display while preserving the result ranking.
  return 1 / (1 + Math.max(0, d));
}

export function modelOptionLabel(model: Loose): string {
  const bits = [];
  if (model.parameter_size) bits.push(model.parameter_size);
  if (model.quantization_level) bits.push(model.quantization_level);
  return bits.length ? `${model.name} · ${bits.join(" · ")}` : model.name;
}

export function openAiModelMatchesKind(name: unknown, kind: string | null | undefined): boolean {
  if (!kind || kind === "any") return true;
  const value = String(name || "").toLocaleLowerCase();
  const patterns: Record<string, string[]> = {
    reasoning: ["reason", "deepseek", "r1", "qwq", "o1", "o3", "thinking"],
    coding: ["code", "coder", "codex", "devstral", "starcoder"],
    fast: ["mini", "small", "flash", "haiku", "fast", "3b", "4b", "7b", "8b"],
    general: ["gpt", "gemma", "llama", "qwen", "mistral", "claude", "general", "chat"],
  };
  return (patterns[kind] || []).some((token) => value.includes(token));
}
