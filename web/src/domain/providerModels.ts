// Which of an endpoint's models fit a "kind" the reviewer chose. The endpoint only reports names, so the kind is a
// judgement from the name; it narrows the list, it does not promise anything about the model.
export type ModelKind = "any" | "general" | "reasoning" | "coding" | "fast";
export const MODEL_KINDS: ModelKind[] = ["any", "general", "reasoning", "coding", "fast"];
const PATTERNS: Record<Exclude<ModelKind, "any">, string[]> = {
  reasoning: ["reason", "deepseek", "r1", "qwq", "o1", "o3", "thinking"],
  coding: ["code", "coder", "codex", "devstral", "starcoder"],
  fast: ["mini", "small", "flash", "haiku", "fast", "3b", "4b", "7b", "8b"],
  general: ["gpt", "gemma", "llama", "qwen", "mistral", "claude", "general", "chat"],
};
export function modelMatchesKind(name: string, kind: string | undefined): boolean {
  if (!kind || kind === "any") return true;
  const value = name.toLocaleLowerCase();
  return (PATTERNS[kind as Exclude<ModelKind, "any">] ?? []).some(token => value.includes(token));
}
export interface DiscoveredModel { name?: string; parameter_size?: string; quantization_level?: string }
