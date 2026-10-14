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

/**
 * Research filter expressions.
 *
 * A deliberately tiny, DerridAI-owned grammar that compiles to the Chroma-style
 * `metadata_filter` / `document_filter` the server validates again before a run:
 *
 *   expr    := or
 *   or      := and ("or" and)*
 *   and     := primary ("and" unary)*
 *   primary := "(" or ")" | field op value | field ("not")? "in" "(" value ("," value)* ")"
 *            | "document" ("not")? "contains" string
 *   op      := = != > >= < <=
 *
 * No function calls and nothing is evaluated: the output is data. Field resolution
 * uses the collection's field catalog, never hard-coded Research field names.
 */

export type FilterScalar = string | number | boolean;

export type ResearchFilterField = {
  /** Indexed Chroma projection key. */
  key: string;
  type?: "string" | "number" | "boolean" | "any";
  values?: FilterScalar[];
  values_truncated?: boolean;
  field_ids?: string[];
  schema_ids?: string[];
  works?: string[];
  encoding?: "scalar" | "json";
};

export type ResearchFilterErrorCode =
  | "unexpected_character"
  | "unterminated_string"
  | "unexpected_end"
  | "unexpected_token"
  | "unknown_field"
  | "unknown_operator"
  | "type_mismatch"
  | "mixed_document_and_metadata"
  | "mixed_list_types";

export type ResearchFilterError = {
  code: ResearchFilterErrorCode;
  /** Character offset in the source expression. */
  position: number;
  params: Record<string, string | number>;
};

type Token =
  | { kind: "word"; value: string; position: number }
  | { kind: "string"; value: string; position: number }
  | { kind: "number"; value: number; position: number }
  | { kind: "op"; value: string; position: number }
  | { kind: "punct"; value: "(" | ")" | ","; position: number };

type PredicateOperator = "=" | "!=" | ">" | ">=" | "<" | "<=" | "in" | "not in";

export type FilterNode =
  | { type: "group"; operator: "and" | "or"; children: FilterNode[] }
  | {
      type: "predicate";
      field: string;
      operator: PredicateOperator;
      value: FilterScalar | FilterScalar[];
      position: number;
    }
  | { type: "document"; negated: boolean; value: string; position: number };

export type ResearchFilterPlanDraft = {
  metadata_filter: Record<string, unknown> | null;
  document_filter: Record<string, unknown> | null;
};

export type ParseResult =
  | { ok: true; ast: FilterNode | null; plan: ResearchFilterPlanDraft }
  | { ok: false; errors: ResearchFilterError[] };

class ParseFailure extends Error {
  constructor(readonly detail: ResearchFilterError) {
    super(detail.code);
  }
}

const KEYWORDS = new Set(["and", "or", "not", "in", "contains", "true", "false"]);
const DOCUMENT_FIELD = "document";

function fail(
  code: ResearchFilterErrorCode,
  position: number,
  params: Record<string, string | number> = {},
): never {
  throw new ParseFailure({ code, position, params });
}

function tokenize(text: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (/\s/u.test(ch)) {
      i += 1;
    } else if (ch === "(" || ch === ")" || ch === ",") {
      tokens.push({ kind: "punct", value: ch, position: i });
      i += 1;
    } else if (ch === '"' || ch === "'") {
      let value = "";
      let j = i + 1;
      let closed = false;
      while (j < text.length) {
        if (text[j] === "\\" && j + 1 < text.length) {
          value += text[j + 1];
          j += 2;
        } else if (text[j] === ch) {
          closed = true;
          j += 1;
          break;
        } else {
          value += text[j];
          j += 1;
        }
      }
      if (!closed) fail("unterminated_string", i);
      tokens.push({ kind: "string", value, position: i });
      i = j;
    } else if (/[=!<>]/u.test(ch)) {
      const two = text.slice(i, i + 2);
      const op = ["!=", ">=", "<="].includes(two) ? two : ["=", ">", "<"].includes(ch) ? ch : "";
      if (!op) fail("unexpected_character", i, { character: ch });
      tokens.push({ kind: "op", value: op, position: i });
      i += op.length;
    } else if (/[0-9]/u.test(ch) || (ch === "-" && /[0-9]/u.test(text[i + 1] ?? ""))) {
      const match = /^-?\d+(?:\.\d+)?/u.exec(text.slice(i)) as RegExpExecArray;
      tokens.push({ kind: "number", value: Number(match[0]), position: i });
      i += match[0].length;
    } else if (/[\p{L}_]/u.test(ch)) {
      const match = /^[\p{L}\p{N}_.-]+/u.exec(text.slice(i)) as RegExpExecArray;
      tokens.push({ kind: "word", value: match[0], position: i });
      i += match[0].length;
    } else {
      fail("unexpected_character", i, { character: ch });
    }
  }
  return tokens;
}

function isWord(token: Token | undefined, value: string): boolean {
  return token?.kind === "word" && token.value.toLowerCase() === value;
}

class Parser {
  private index = 0;
  constructor(
    private readonly tokens: Token[],
    private readonly fields: Map<string, ResearchFilterField>,
    private readonly endPosition: number,
  ) {}

  parse(): FilterNode | null {
    if (!this.tokens.length) return null;
    const node = this.parseOr();
    const extra = this.tokens[this.index];
    if (extra) fail("unexpected_token", extra.position, { token: tokenText(extra) });
    return node;
  }

  private peek(): Token | undefined {
    return this.tokens[this.index];
  }

  private next(): Token {
    const token = this.tokens[this.index];
    if (!token) fail("unexpected_end", this.endPosition);
    this.index += 1;
    return token;
  }

  private parseGroup(operator: "and" | "or", parseChild: () => FilterNode): FilterNode {
    const children = [parseChild()];
    while (isWord(this.peek(), operator)) {
      this.index += 1;
      children.push(parseChild());
    }
    return children.length === 1
      ? children[0]
      : { type: "group", operator, children: children.flatMap((c) => flatten(c, operator)) };
  }

  private parseOr(): FilterNode {
    return this.parseGroup("or", () => this.parseAnd());
  }

  private parseAnd(): FilterNode {
    return this.parseGroup("and", () => this.parsePrimary());
  }

  private parsePrimary(): FilterNode {
    const token = this.next();
    if (token.kind === "punct" && token.value === "(") {
      const inner = this.parseOr();
      const close = this.next();
      if (!(close.kind === "punct" && close.value === ")"))
        fail("unexpected_token", close.position, { token: tokenText(close) });
      return inner;
    }
    if (token.kind !== "word" || KEYWORDS.has(token.value.toLowerCase()))
      fail("unexpected_token", token.position, { token: tokenText(token) });

    if (token.value.toLowerCase() === DOCUMENT_FIELD && !this.fields.has(token.value)) {
      let negated = false;
      if (isWord(this.peek(), "not")) {
        this.index += 1;
        negated = true;
      }
      const verb = this.next();
      if (!isWord(verb, "contains"))
        fail("unknown_operator", verb.position, { operator: tokenText(verb) });
      const operand = this.next();
      if (operand.kind !== "string")
        fail("unexpected_token", operand.position, { token: tokenText(operand) });
      return { type: "document", negated, value: operand.value, position: token.position };
    }

    const field = this.fields.get(token.value);
    if (!field) fail("unknown_field", token.position, { field: token.value });

    const opToken = this.next();
    let operator: string;
    if (opToken.kind === "op") operator = opToken.value;
    else if (isWord(opToken, "in")) operator = "in";
    else if (isWord(opToken, "not")) {
      const inToken = this.next();
      if (!isWord(inToken, "in"))
        fail("unknown_operator", inToken.position, { operator: tokenText(inToken) });
      operator = "not in";
    } else fail("unknown_operator", opToken.position, { operator: tokenText(opToken) });

    if (operator === "in" || operator === "not in") {
      const open = this.next();
      if (!(open.kind === "punct" && open.value === "("))
        fail("unexpected_token", open.position, { token: tokenText(open) });
      const values: FilterScalar[] = [];
      for (;;) {
        values.push(this.parseValue(field));
        const sep = this.next();
        if (sep.kind === "punct" && sep.value === ",") continue;
        if (sep.kind === "punct" && sep.value === ")") break;
        fail("unexpected_token", sep.position, { token: tokenText(sep) });
      }
      if (new Set(values.map((v) => typeof v)).size > 1)
        fail("mixed_list_types", token.position, { field: field.key });
      return {
        type: "predicate",
        field: field.key,
        operator: operator as "in" | "not in",
        value: values,
        position: token.position,
      };
    }

    const value = this.parseValue(field);
    if (
      [">", ">=", "<", "<="].includes(operator) &&
      (typeof value !== "number" || (field.type && !["number", "any"].includes(field.type)))
    )
      fail("type_mismatch", opToken.position, { field: field.key, expected: "number" });
    return {
      type: "predicate",
      field: field.key,
      operator: operator as PredicateOperator,
      value,
      position: token.position,
    };
  }

  private parseValue(field: ResearchFilterField): FilterScalar {
    const token = this.next();
    let value: FilterScalar;
    if (token.kind === "string" || token.kind === "number") value = token.value;
    else if (isWord(token, "true")) value = true;
    else if (isWord(token, "false")) value = false;
    else return fail("unexpected_token", token.position, { token: tokenText(token) });
    if (field.type && field.type !== "any" && typeof value !== field.type)
      fail("type_mismatch", token.position, { field: field.key, expected: field.type });
    return value;
  }
}

function flatten(node: FilterNode, operator: "and" | "or"): FilterNode[] {
  return node.type === "group" && node.operator === operator ? node.children : [node];
}

function tokenText(token: Token): string {
  return String(token.value);
}

const METADATA_OPERATORS: Record<string, string> = {
  "=": "$eq",
  "!=": "$ne",
  ">": "$gt",
  ">=": "$gte",
  "<": "$lt",
  "<=": "$lte",
  in: "$in",
  "not in": "$nin",
};

function compileMetadata(node: FilterNode): Record<string, unknown> {
  if (node.type === "group")
    return { [`$${node.operator}`]: node.children.map((child) => compileMetadata(child)) };
  if (node.type === "predicate")
    return { [node.field]: { [METADATA_OPERATORS[node.operator]]: node.value } };
  throw new Error("document predicate in metadata expression");
}

function compileDocument(node: FilterNode): Record<string, unknown> {
  if (node.type === "group")
    return { [`$${node.operator}`]: node.children.map((child) => compileDocument(child)) };
  if (node.type === "document")
    return { [node.negated ? "$not_contains" : "$contains"]: node.value };
  throw new Error("metadata predicate in document expression");
}

function kinds(node: FilterNode): Set<"metadata" | "document"> {
  if (node.type === "group") return new Set(node.children.flatMap((c) => [...kinds(c)]));
  return new Set([node.type === "document" ? "document" : "metadata"]);
}

function wrap(operator: "and" | "or", parts: Record<string, unknown>[]) {
  return parts.length === 1 ? parts[0] : { [`$${operator}`]: parts };
}

/** Compile an AST into the executable plan; document and metadata predicates may only be and-ed. */
export function compileResearchFilterPlan(ast: FilterNode | null): ResearchFilterPlanDraft {
  const plan: ResearchFilterPlanDraft = { metadata_filter: null, document_filter: null };
  if (!ast) return plan;
  const conjuncts = flatten(ast, "and");
  const metadata: Record<string, unknown>[] = [];
  const documents: Record<string, unknown>[] = [];
  for (const part of conjuncts) {
    const present = kinds(part);
    if (present.size > 1) {
      const position = firstPosition(part);
      fail("mixed_document_and_metadata", position);
    }
    if (present.has("document")) documents.push(compileDocument(part));
    else metadata.push(compileMetadata(part));
  }
  if (metadata.length) plan.metadata_filter = wrap("and", metadata);
  if (documents.length) plan.document_filter = wrap("and", documents);
  return plan;
}

function firstPosition(node: FilterNode): number {
  return node.type === "group" ? firstPosition(node.children[0]) : node.position;
}

function fieldMap(catalog: ResearchFilterField[]): Map<string, ResearchFilterField> {
  return new Map(catalog.map((field) => [field.key, field]));
}

/** Parse and compile an expression. Never throws; errors are positioned and localizable by code. */
export function parseResearchFilterExpression(
  text: string,
  catalog: ResearchFilterField[],
): ParseResult {
  try {
    const parser = new Parser(tokenize(text), fieldMap(catalog), text.length);
    const ast = parser.parse();
    return { ok: true, ast, plan: compileResearchFilterPlan(ast) };
  } catch (error) {
    if (error instanceof ParseFailure) return { ok: false, errors: [error.detail] };
    throw error;
  }
}

export type ResearchFilterExplanationClause = {
  field: string;
  operator: string;
  value: FilterScalar | FilterScalar[];
};

/** Flat, localizable description of a compiled metadata/document filter. */
export function explainResearchFilterPlan(
  plan: ResearchFilterPlanDraft,
): ResearchFilterExplanationClause[] {
  const out: ResearchFilterExplanationClause[] = [];
  const walk = (node: unknown) => {
    if (!node || typeof node !== "object") return;
    const [key, operand] = Object.entries(node as Record<string, unknown>)[0] ?? [];
    if (key === "$and" || key === "$or") {
      (operand as unknown[]).forEach(walk);
    } else if (key === "$contains" || key === "$not_contains") {
      out.push({ field: DOCUMENT_FIELD, operator: key, value: operand as string });
    } else if (key && operand && typeof operand === "object") {
      const [operator, value] = Object.entries(operand as Record<string, unknown>)[0];
      out.push({ field: key, operator, value: value as FilterScalar | FilterScalar[] });
    } else if (key) {
      out.push({ field: key, operator: "$eq", value: operand as FilterScalar });
    }
  };
  walk(plan.metadata_filter);
  walk(plan.document_filter);
  return out;
}

export type ResearchFilterCompletion = {
  kind: "field" | "operator" | "connective" | "value";
  text: string;
};

const OPERATOR_COMPLETIONS = ["=", "!=", ">", ">=", "<", "<=", "in", "not in"];

/**
 * Suggestions for the token being typed, using bounded server catalog values.
 */
export function suggestResearchFilterCompletions(
  text: string,
  catalog: ResearchFilterField[],
): ResearchFilterCompletion[] {
  let tokens: Token[];
  try {
    tokens = tokenize(text);
  } catch {
    return [];
  }
  const trailingSpace = /\s$/u.test(text) || text === "";
  const last = tokens[tokens.length - 1];
  const partial = !trailingSpace && last?.kind === "word" ? last.value.toLowerCase() : "";
  const settled = partial ? tokens.slice(0, -1) : tokens;
  const previous = settled[settled.length - 1];
  const fieldNames = [...catalog.map((f) => f.key), DOCUMENT_FIELD];

  const matches = (kind: ResearchFilterCompletion["kind"], options: string[]) =>
    options
      .filter(
        (option) => option.toLowerCase().startsWith(partial) && option.toLowerCase() !== partial,
      )
      .map((option) => ({ kind, text: option }));

  if (!previous || isWord(previous, "and") || isWord(previous, "or") || isOpenParen(previous))
    return matches("field", fieldNames);
  if (previous.kind === "word" && fieldNames.includes(previous.value))
    return previous.value === DOCUMENT_FIELD
      ? matches("operator", ["contains", "not contains"])
      : matches("operator", OPERATOR_COMPLETIONS);
  if (previous?.kind === "op") {
    const fieldToken = settled[settled.length - 2];
    const field = catalog.find((item) => item.key === fieldToken?.value);
    return (field?.values ?? [])
      .slice(0, 20)
      .map((value) => ({ kind: "value" as const, text: JSON.stringify(value) }));
  }
  if (isValueEnd(previous)) return matches("connective", ["and", "or"]);
  return [];
}

function isOpenParen(token: Token) {
  return token.kind === "punct" && token.value === "(";
}

function isValueEnd(token: Token) {
  return (
    token.kind === "string" ||
    token.kind === "number" ||
    (token.kind === "punct" && token.value === ")") ||
    isWord(token, "true") ||
    isWord(token, "false")
  );
}

/** Build the field catalog from a collection's declared filter fields. */
export function researchFilterCatalog(
  filterFields: string[] | undefined,
  indexed: ResearchFilterField[] = [],
): ResearchFilterField[] {
  const fields = new Map(
    (filterFields ?? []).map((key) => [key, { key, type: "any" as const } as ResearchFilterField]),
  );
  for (const field of indexed) fields.set(field.key, field);
  return [...fields.values()];
}
