# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
import logging
import math
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from .chroma_store import ChromaStore
from .config import settings
from .models import OllamaTouchupOptions, RAGRunRequest
from .record_types import EvidenceItem, QueryDecomposition, RetrievalCandidate

logger = logging.getLogger(__name__)

QUERY_TEMPLATE = """
Your job is to extract query details from the user's research request.

Prompt:
{prompt}

Additional instructions supplied separately:
{instructions}

Return exactly one JSON object:
{{
  "prompt_query": "the actual research question in English",
  "prompt_query_fr": "the same research question in French",
  "prompt_instructions": "only instructions actually supplied by the user",
  "response_language": "en"
}}

Rules:
- Do not answer the research question.
- Do not invent instructions.
- Preserve philosophical terminology.
- prompt_query_fr is required even when the original prompt is English.
- response_language should be "fr" only when the user clearly requests a French answer or writes primarily in French; otherwise "en".
- Return JSON only.
""".strip()

_CROSS_ENCODER_CACHE: dict[str, Any] = {}


FOCUSED_PROMPT = """
You are DerridAI, an evidence-grounded scholarly research assistant.

<MASTER PROMPT>
{prompt_query}
</MASTER PROMPT>

<MASTER INSTRUCTIONS>
{prompt_instructions}
</MASTER INSTRUCTIONS>

<RESPONSE LANGUAGE>
{response_language}
</RESPONSE LANGUAGE>

<EVIDENCE>
{context}
</EVIDENCE>

Guidelines:
- Preserve speaker, quoted_speaker, quoted_author, quoted_work, position_holder, stance, target, discourse_role, and proposition_status.
- Distinguish Derrida's own claims from positions he quotes, describes, reconstructs, endorses, questions, or criticizes.
- Use the supplied EVIDENCE as the sole basis for substantive claims.
- Do not flatten quotation provenance.
- Preserve modality and negation.
- If evidence is insufficient, say so rather than inventing support.
- Respond in cohesive scholarly prose unless the user's instructions explicitly require another form.

Citation rules:
- Tag every substantive claim with one or more evidence IDs using double square
  brackets by default, such as [[E0]] or [[E0, E3]].
- Do not cite an evidence ID that does not support the claim.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    value = str(text or "").strip()
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*```$", "", value)
    candidates = [value]
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        candidates.append(value[start:end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("LLM did not return a valid JSON object.")


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error)
            return str(payload.get("detail") or payload.get("message") or "")
    except Exception:
        logger.debug("Could not parse provider error JSON; using response text", exc_info=True)
    return response.text[:1200]


def chat_complete(
    *,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    prompt: str,
    options: OllamaTouchupOptions | None = None,
    json_mode: bool = False,
    json_schema: dict[str, Any] | None = None,
    schema_name: str = "derridai_response",
    max_tokens: int | None = None,
    cancelled: Callable[[], bool] | None = None,
    timeout_seconds: float | None = None,
) -> str:
    tuning = options or OllamaTouchupOptions()
    provider = provider.strip().lower()

    if provider == "openai":
        url = (base_url or settings.openai_compat_base_url).rstrip("/")
        headers = {"Content-Type": "application/json"}
        key = api_key if api_key is not None else settings.openai_compat_api_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0 if tuning.temperature is None else tuning.temperature,
            "max_tokens": max_tokens or tuning.num_predict or 4096,
        }
        if tuning.top_p is not None:
            body["top_p"] = tuning.top_p
        if tuning.seed is not None:
            body["seed"] = tuning.seed
        if tuning.stop:
            body["stop"] = tuning.stop
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            }
        elif json_mode:
            body["response_format"] = {"type": "json_object"}
        for key_name, value in (tuning.extra_options or {}).items():
            if key_name not in {"model", "messages"}:
                body[key_name] = value

        timeout = httpx.Timeout(
            connect=settings.openai_connect_timeout_seconds,
            read=min(settings.openai_timeout_seconds, timeout_seconds) if timeout_seconds else settings.openai_timeout_seconds,
            write=min(settings.openai_timeout_seconds, timeout_seconds) if timeout_seconds else settings.openai_timeout_seconds,
            pool=settings.openai_connect_timeout_seconds,
        )
        if cancelled is not None:
            def stream_once(payload: dict[str, Any]) -> tuple[int, str, str]:
                started_clock = time.monotonic()
                streaming = dict(payload)
                streaming["stream"] = True
                chunks: list[str] = []
                with httpx.Client(timeout=timeout) as client:
                    with client.stream(
                        "POST",
                        f"{url}/chat/completions",
                        headers=headers,
                        json=streaming,
                    ) as response:
                        if response.status_code >= 400:
                            raw = response.read().decode("utf-8", errors="replace")
                            return response.status_code, "", raw[:2000]
                        for line in response.iter_lines():
                            if timeout_seconds and time.monotonic() - started_clock > timeout_seconds:
                                raise TimeoutError(f"LLM generation exceeded {timeout_seconds:.0f}s stage deadline.")
                            if cancelled():
                                raise InterruptedError("RAG generation cancelled.")
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                event = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            choices = event.get("choices") or []
                            delta = choices[0].get("delta") if choices else {}
                            piece = (delta or {}).get("content") or ""
                            if isinstance(piece, list):
                                piece = "".join(
                                    str(part.get("text") or "")
                                    for part in piece
                                    if isinstance(part, dict)
                                )
                            if piece:
                                chunks.append(str(piece))
                return 200, "".join(chunks).strip(), ""

            status, content, detail = stream_once(body)
            if status in {400, 422} and "response_format" in body:
                fallback = dict(body)
                # Some OpenAI-compatible routers support JSON mode but not JSON Schema.
                # Preserve structured output when possible before falling all the way
                # back to unconstrained text.
                if json_schema is not None:
                    fallback["response_format"] = {"type": "json_object"}
                else:
                    fallback.pop("response_format", None)
                status, content, detail = stream_once(fallback)
                if status in {400, 422} and "response_format" in fallback:
                    fallback.pop("response_format", None)
                    status, content, detail = stream_once(fallback)
            if status in {400, 422}:
                # Preserve compatibility with local OpenAI-compatible routers
                # that support Chat Completions but not streaming.
                fallback_body = dict(body)
                fallback_body.pop("stream", None)
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=fallback_body,
                    )
                if response.status_code < 400:
                    payload = response.json()
                    choices = payload.get("choices") or []
                    message = choices[0].get("message") if choices else {}
                    content = (message or {}).get("content") or ""
                    if isinstance(content, list):
                        content = "".join(
                            str(part.get("text") or "")
                            for part in content
                            if isinstance(part, dict)
                        )
                    if cancelled and cancelled():
                        raise InterruptedError("RAG generation cancelled.")
                    status = 200
            if status >= 400:
                raise RuntimeError(
                    f"OpenAI-compatible endpoint returned HTTP {status}: {detail}"
                )
            return str(content).strip()

        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{url}/chat/completions",
                headers=headers,
                json=body,
            )
            if response.status_code in {400, 422} and "response_format" in body:
                if json_schema is not None:
                    body["response_format"] = {"type": "json_object"}
                    response = client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                if response.status_code in {400, 422} and "response_format" in body:
                    body.pop("response_format", None)
                    response = client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenAI-compatible endpoint returned HTTP {response.status_code}: "
                f"{_response_detail(response)}"
            )
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI-compatible endpoint returned no choices.")
        content = (choices[0].get("message") or {}).get("content") or ""
        if isinstance(content, list):
            content = "".join(
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict)
            )
        return str(content).strip()

    url = (base_url or settings.ollama_base_url).rstrip("/")
    option_values: dict[str, Any] = dict(tuning.extra_options or {})
    for key_name, value in {
        "num_ctx": tuning.num_ctx,
        "num_predict": max_tokens or tuning.num_predict,
        "temperature": 0.0 if tuning.temperature is None else tuning.temperature,
        "top_k": tuning.top_k,
        "top_p": tuning.top_p,
        "min_p": tuning.min_p,
        "repeat_penalty": tuning.repeat_penalty,
        "seed": tuning.seed,
        "mirostat": tuning.mirostat,
        "mirostat_eta": tuning.mirostat_eta,
        "mirostat_tau": tuning.mirostat_tau,
        "stop": tuning.stop,
    }.items():
        if value is not None:
            option_values[key_name] = value

    body = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": option_values,
    }
    if json_schema is not None:
        # Ollama accepts a JSON Schema object in `format`; this materially reduces
        # malformed output from local models while remaining compatible with the
        # ordinary `format: json` fallback below.
        body["format"] = json_schema
    elif json_mode:
        body["format"] = "json"
    if tuning.think is not None:
        body["think"] = tuning.think
    keep_alive = tuning.keep_alive or settings.ollama_keep_alive
    if keep_alive:
        body["keep_alive"] = keep_alive

    timeout = httpx.Timeout(
        connect=settings.ollama_connect_timeout_seconds,
        read=min(settings.ollama_timeout_seconds, timeout_seconds) if timeout_seconds else settings.ollama_timeout_seconds,
        write=min(settings.ollama_timeout_seconds, timeout_seconds) if timeout_seconds else settings.ollama_timeout_seconds,
        pool=settings.ollama_connect_timeout_seconds,
    )
    if cancelled is not None:
        def ollama_stream_once(payload: dict[str, Any]) -> tuple[int, str, str]:
            started_clock = time.monotonic()
            streaming = dict(payload)
            streaming["stream"] = True
            chunks: list[str] = []
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", f"{url}/api/chat", json=streaming) as response:
                    if response.status_code >= 400:
                        raw = response.read().decode("utf-8", errors="replace")
                        return response.status_code, "", raw[:2000]
                    for line in response.iter_lines():
                        if timeout_seconds and time.monotonic() - started_clock > timeout_seconds:
                            raise TimeoutError(f"LLM generation exceeded {timeout_seconds:.0f}s stage deadline.")
                        if cancelled():
                            raise InterruptedError("RAG generation cancelled.")
                        if not line:
                            continue
                        payload_line = json.loads(line)
                        piece = ((payload_line.get("message") or {}).get("content") or "")
                        if piece:
                            chunks.append(str(piece))
                        if payload_line.get("done"):
                            break
            return 200, "".join(chunks).strip(), ""

        status, content, detail = ollama_stream_once(body)
        if status in {400, 422} and json_schema is not None:
            fallback = dict(body)
            fallback["format"] = "json"
            status, content, detail = ollama_stream_once(fallback)
        if status >= 400:
            raise RuntimeError(f"Ollama returned HTTP {status}: {detail}")
        return content

    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{url}/api/chat", json=body)
        if response.status_code in {400, 422} and json_schema is not None:
            # Older Ollama builds support JSON mode but not schema-valued format.
            # Keep the corpus builder compatible while Pydantic validation/retry
            # still enforces the contract after generation.
            fallback = dict(body)
            fallback["format"] = "json"
            response = client.post(f"{url}/api/chat", json=fallback)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Ollama returned HTTP {response.status_code}: "
            f"{_response_detail(response)}"
        )
    payload = response.json()
    return str((payload.get("message") or {}).get("content") or "").strip()


def _citation_strings(record: dict[str, Any]) -> tuple[str, str]:
    author = str(record.get("document_author") or record.get("speaker") or "Jacques Derrida")
    work = str(record.get("work") or "")
    edition = str(record.get("edition") or "")
    year = record.get("year") or ""
    page_start = record.get("page_start")
    page_end = record.get("page_end")
    translator = str(record.get("translator") or "")

    last = author.split()[-1] if author.split() else author
    if page_start is None:
        pages = ""
    elif page_end is None or page_end == page_start:
        pages = str(page_start)
    else:
        pages = f"{page_start}-{page_end}"
    inline = f"{last} {year}{': ' + pages if pages else ''}".strip()

    parts = author.split()
    reversed_name = (
        f"{parts[-1]}, {' '.join(parts[:-1])}"
        if len(parts) > 1 else author
    )
    full = (
        f"{reversed_name}. {work}."
        f"{f' {translator} trans.' if translator else ''}"
        f"{f' {edition}.' if edition else ''}"
        f"{f' {year}.' if year else ''}"
    )
    return inline.strip(), re.sub(r"\s+", " ", full).strip()


def _context_string(
    records: list[dict[str, Any]],
    *,
    record_char_limit: int,
    total_char_limit: int,
) -> tuple[str, dict[str, str], list[EvidenceItem]]:
    blocks: list[str] = []
    works: dict[str, str] = {}
    evidence: list[EvidenceItem] = []
    total_chars = 0

    for item in records:
        record = dict(item["record"])
        record.pop("updates", None)
        inline, full = _citation_strings(record)
        raw_text = " ".join(str(record.get("text") or "").split())
        text_truncated = len(raw_text) > record_char_limit
        compact_text = raw_text[:record_char_limit]
        if text_truncated:
            compact_text = compact_text.rstrip() + " …"

        tag = f"E{len(evidence)}"
        block = "\n".join([
            f"<BEGIN EVIDENCE_TAG {tag}>",
            f"evidence_tag=[[{tag}]]",
            f"record_id={record.get('record_id', '')}",
            f"work={record.get('work', '')}",
            f"document_author={record.get('document_author', '')}",
            f"speaker={record.get('speaker', '')}",
            f"quoted_speaker={json.dumps(record.get('quoted_speaker', []), ensure_ascii=False)}",
            f"quoted_author={json.dumps(record.get('quoted_author', []), ensure_ascii=False)}",
            f"quoted_work={json.dumps(record.get('quoted_work', []), ensure_ascii=False)}",
            f"quoted_position_holder={json.dumps(record.get('quoted_position_holder', []), ensure_ascii=False)}",
            f"position_holder={record.get('position_holder', '')}",
            f"stance={record.get('stance', '')}",
            f"position_status={record.get('proposition_status', '')}",
            f"target={record.get('target', '')}",
            f"role={record.get('discourse_role', '')}",
            f"citation={inline}",
            f"text={compact_text}",
            f"<END EVIDENCE_TAG {tag}>",
        ])

        projected = total_chars + len(block) + (2 if blocks else 0)
        if blocks and projected > total_char_limit:
            break

        total_chars = projected
        works[tag] = inline
        evidence.append({
            "evidence_id": tag,
            "collection": item.get("collection"),
            "distance": item.get("distance"),
            "rerank_score": item.get("rerank_score"),
            "rrf_score": item.get("rrf_score"),
            "retrieval_hits": item.get("retrieval_hits", []),
            "record": record,
            "inline_citation": inline,
            "full_citation": full,
            "text_truncated": text_truncated,
        })
        blocks.append(block)

    return "\n\n".join(blocks), works, evidence


def evidence_sufficiency_issues(evidence: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return deterministic provenance failures before generation can begin."""
    issues: list[dict[str, str]] = []
    for item in evidence:
        record = item.get("record") if isinstance(item.get("record"), dict) else {}
        evidence_id = str(item.get("evidence_id") or "unknown")
        missing = [
            field
            for field, value in {
                "record_id": record.get("record_id"),
                "work": record.get("work"),
                "document_author": record.get("document_author"),
                "exact_text": record.get("text"),
                "inline_citation": item.get("inline_citation"),
                "full_citation": item.get("full_citation"),
            }.items()
            if not str(value or "").strip()
        ]
        if missing:
            issues.append({"evidence_id": evidence_id, "missing": ", ".join(missing)})
    return issues


def _bind_sources(answer: str, evidence: list[EvidenceItem], include_works_cited: bool) -> str:
    citation_map = {
        item["evidence_id"]: item["inline_citation"]
        for item in evidence
    }

    def replace_group(match: re.Match[str]) -> str:
        inside = match.group(1)
        tags = re.findall(r"\bE\d+\b", inside)
        if not tags:
            return match.group(0)
        rendered = [
            citation_map.get(tag, tag)
            for tag in tags
        ]
        return "(" + "; ".join(dict.fromkeys(rendered)) + ")"

    used_ids = set(re.findall(r"\bE\d+\b", answer))
    # Generators do not always obey one citation wrapper exactly.  Accept the
    # six common forms while keeping [[E0]] as the prompt/default format.  Run
    # double wrappers before single wrappers so a valid [[E0]] token is not
    # partially consumed by the [E0] expression.
    tag_group = r"((?:E\d+)(?:\s*[,;]\s*E\d+)*)"
    bound = answer
    for pattern in (
        rf"\[\[\s*{tag_group}\s*\]\]",
        rf"\(\(\s*{tag_group}\s*\)\)",
        rf"\{{\{{\s*{tag_group}\s*\}}\}}",
        rf"\[\s*{tag_group}\s*\]",
        rf"\(\s*{tag_group}\s*\)",
        rf"\{{\s*{tag_group}\s*\}}",
    ):
        bound = re.sub(pattern, replace_group, bound)

    if include_works_cited:
        seen: set[str] = set()
        citations: list[str] = []
        for item in evidence:
            if used_ids and item["evidence_id"] not in used_ids:
                continue
            record = item["record"]
            canonical = str(
                record.get("canonical_work_id")
                or item["full_citation"]
            )
            if canonical in seen:
                continue
            seen.add(canonical)
            citations.append(item["full_citation"])
        if citations:
            bound += "\n\n**Works Cited**\n\n" + "\n".join(
                f"{index}. {citation}"
                for index, citation in enumerate(citations, start=1)
            )
    return bound


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    # Retrieval embeddings may arrive as NumPy arrays from Chroma. Explicit
    # length checks avoid ambiguous NumPy truth-value evaluation.
    if (
        a is None
        or b is None
        or len(a) == 0
        or len(b) == 0
        or len(a) != len(b)
    ):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _distance_similarity(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(0.0, float(distance)))


def _mmr_select(
    candidates: list[dict[str, Any]],
    *,
    k: int,
    lambda_mult: float,
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    remaining = list(candidates)
    selected: list[dict[str, Any]] = []

    while remaining and len(selected) < k:
        best_index = 0
        best_score = -float("inf")
        for index, candidate in enumerate(remaining):
            relevance = _distance_similarity(candidate.get("distance"))
            diversity = 0.0
            if selected:
                diversity = max(
                    _cosine(candidate.get("embedding"), chosen.get("embedding"))
                    for chosen in selected
                )
            score = lambda_mult * relevance - (1.0 - lambda_mult) * diversity
            if score > best_score:
                best_score = score
                best_index = index
        chosen = remaining.pop(best_index)
        chosen = dict(chosen)
        chosen["mmr_score"] = best_score
        selected.append(chosen)
    return selected


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\wÀ-ÿ'-]+", str(text).casefold())
        if len(token) > 2
    }


def _lexical_rerank(query: str, docs: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    q = _tokenize(query)
    scored: list[dict[str, Any]] = []
    for index, item in enumerate(docs):
        record = item["record"]
        text = " ".join([
            str(record.get("work") or ""),
            str(record.get("speaker") or ""),
            str(record.get("position_holder") or ""),
            str(record.get("topics") or ""),
            str(record.get("concepts") or ""),
            str(record.get("persons") or ""),
            str(record.get("text") or ""),
        ])
        tokens = _tokenize(text)
        overlap = len(q & tokens) / max(1, len(q))
        retrieval_bonus = 1.0 / (60.0 + index + 1.0)
        similarity = _distance_similarity(item.get("distance"))
        row = dict(item)
        row["rerank_score"] = overlap * 2.0 + similarity + retrieval_bonus
        scored.append(row)
    return sorted(
        scored,
        key=lambda item: item.get("rerank_score", 0.0),
        reverse=True,
    )[:top_n]


def _cross_encoder_rerank(
    query: str,
    docs: list[dict[str, Any]],
    top_n: int,
    model_name: str,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        from sentence_transformers import CrossEncoder
    except Exception as exc:
        return _lexical_rerank(query, docs, top_n), (
            f"Cross-encoder unavailable ({exc}); used lexical/vector fallback."
        )

    cache_dir = Path(settings.rag_model_cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        model = _CROSS_ENCODER_CACHE.get(model_name)
        if model is None:
            model = CrossEncoder(
                model_name,
                cache_dir=str(cache_dir),
            )
            _CROSS_ENCODER_CACHE[model_name] = model
        pairs = [
            [query, str(item["record"].get("text") or "")]
            for item in docs
        ]
        scores = model.predict(pairs)
        ranked = []
        for item, score in zip(docs, scores):
            row = dict(item)
            row["rerank_score"] = float(score)
            ranked.append(row)
        ranked.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )
        return ranked[:top_n], None
    except Exception as exc:
        return _lexical_rerank(query, docs, top_n), (
            f"Cross-encoder failed ({exc}); used lexical/vector fallback."
        )


def _resolve_search_collections(
    store: ChromaStore,
    source_name: str,
    locales: list[str],
) -> list[dict[str, Any]]:
    stores = store.list_stores()
    source = next((item for item in stores if item["name"] == source_name), None)
    if source is None:
        raise ValueError(f"Collection {source_name!r} does not exist.")

    requested = list(dict.fromkeys(locales or ["en", "fr"]))
    requested_set = set(requested)

    if source.get("collection_role") == "language":
        codes = set(source.get("language_codes") or [])
        if requested_set and not (codes & requested_set):
            return []
        row = dict(source)
        row["_rag_locales"] = list(codes & requested_set) or list(codes)
        return [row]

    resolved: list[dict[str, Any]] = []
    for locale in requested:
        derived = next((
            item
            for item in stores
            if item.get("collection_role") == "language"
            and (
                item.get("source_collection") == source_name
                or item.get("name") == f"{source_name}_{locale}"
            )
            and locale in set(item.get("language_codes") or [])
        ), None)
        if derived:
            row = dict(derived)
            row["_rag_locales"] = [locale]
            row["_rag_route"] = f"{locale}:derived"
            resolved.append(row)
        else:
            # Keep one source-collection route per requested language rather
            # than merging en/fr into one query. This preserves bilingual
            # retrieval even when derivative collections have not been built.
            row = dict(source)
            row["_rag_locales"] = [locale]
            row["_rag_route"] = f"{locale}:source_fallback"
            resolved.append(row)

    if not resolved:
        row = dict(source)
        row["_rag_locales"] = list(source.get("language_codes") or ["en", "fr"])
        row["_rag_route"] = "source"
        resolved.append(row)
    return resolved


def _selected_evidence_candidates(request: RAGRunRequest, store: ChromaStore) -> list[RetrievalCandidate]:
    """Resolve user-selected evidence to authoritative records.

    DB-backed researcher selections are sent as collection/id pairs so the full
    source stays server-side. Admin-only workspace selections may carry a record
    directly. The resulting candidate shape matches retrieval candidates and can
    therefore enter the existing context/citation pipeline unchanged.
    """
    resolved: list[RetrievalCandidate] = []
    seen: set[str] = set()
    for selection in request.selected_evidence or []:
        record: dict[str, Any] | None = None
        collection = selection.collection
        chroma_id = selection.chroma_id
        if collection and chroma_id:
            record = store.get_record(collection, chroma_id)
        elif selection.record:
            record = dict(selection.record)
            record.pop("updates", None)
        if not record:
            continue
        logical = str(record.get("record_id") or chroma_id or len(resolved))
        key = f"{collection or 'workspace'}::{logical}"
        if key in seen:
            continue
        seen.add(key)
        resolved.append({
            "id": chroma_id or logical,
            "collection": collection or "selected_workspace",
            "record": record,
            "distance": None,
            "rrf_score": 1.0,
            "rerank_score": 1.0,
            "retrieval_hits": [{"collection": collection or "workspace", "search_type": "selected", "rank": 0}],
            "selected_evidence": True,
        })
    return resolved


def _scope_rag_candidates(
    rows: list[dict[str, Any]],
    collection: dict[str, Any],
    locale_codes: set[str],
) -> list[dict[str, Any]]:
    if collection.get("collection_role") == "language":
        return rows
    scoped: list[dict[str, Any]] = []
    for candidate in rows:
        record = candidate.get("record") or {}
        language_value = record.get("document_language")
        if language_value is None:
            language_value = record.get("document_languages")
        codes = ChromaStore._record_language_codes(language_value)
        if not locale_codes or codes & locale_codes:
            scoped.append(candidate)
    return scoped


def run_rag_pipeline(
    request: RAGRunRequest,
    store: ChromaStore,
    *,
    progress: Callable[[str, int, int, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    stages: list[dict[str, Any]] = []
    warnings: list[str] = []

    def update(stage: str, current: int, total: int, detail: str = "") -> None:
        if progress:
            progress(stage, current, total, detail)

    def check_cancel() -> None:
        if cancelled and cancelled():
            raise InterruptedError("RAG job cancelled.")

    provider = request.provider
    model = (
        request.model
        or (
            settings.openai_compat_model
            if provider == "openai"
            else settings.ollama_model
        )
    )
    if not model:
        raise ValueError("No generation model selected.")

    # Step 1-2: query metadata/decomposition, adapted from the supplied pipeline.
    stage_start = time.perf_counter()
    update("query_metadata", 0, 1, "Decomposing the research prompt")
    parsed_query: dict[str, Any] = {}
    if request.query_decomposition:
        decomposition_prompt = QUERY_TEMPLATE.format(
            prompt=request.prompt,
            instructions=request.instructions or "",
        )
        raw = chat_complete(
            provider=provider,
            model=model,
            base_url=request.base_url,
            api_key=request.api_key,
            prompt=decomposition_prompt,
            options=request.generation,
            json_mode=True,
            max_tokens=request.query_decomposition_num_predict,
            cancelled=cancelled,
        )
        try:
            parsed_query = _extract_json(raw)
        except Exception as exc:
            warnings.append(
                f"Query decomposition failed ({exc}); using the original prompt."
            )
            parsed_query = {}
    query_metadata: QueryDecomposition = {
        "prompt_query": str(
            parsed_query.get("prompt_query")
            or request.prompt
        ).strip(),
        "prompt_query_fr": str(
            parsed_query.get("prompt_query_fr")
            or request.prompt
        ).strip(),
        "prompt_instructions": str(
            parsed_query.get("prompt_instructions")
            or request.instructions
            or ""
        ).strip(),
        # Retrieval/reranking limits are explicit pipeline controls, not LLM
        # decisions. Keeping them authoritative prevents decomposition defaults
        # from silently capping user-selected values (historically at 64/24).
        "limit_retrieval": int(request.k),
        "limit_reranking": int(request.rerank_top_n),
        "response_language": (
            request.response_language
            if request.response_language in {"en", "fr"}
            else str(parsed_query.get("response_language") or "en")
        ),
        "document_languages": [str(code) for code in request.locales],
    }
    stages.append({
        "name": "query_metadata",
        "seconds": time.perf_counter() - stage_start,
        "detail": query_metadata,
    })
    update("query_metadata", 1, 1, "Query decomposition complete")
    check_cancel()

    selected_candidates = _selected_evidence_candidates(request, store)
    if request.skip_retrieval and not selected_candidates:
        raise ValueError("Selected-evidence-only RAG requires at least one selected evidence record.")
    if not request.skip_retrieval and not str(request.source_collection or "").strip():
        raise ValueError("Select a source collection when retrieval is enabled.")

    # Step 3: semantic + lexical + MMR retrieval. Selected-evidence-only runs bypass
    # vector retrieval completely; ordinary runs pin selected evidence alongside
    # retrieved candidates so user-curated context cannot be dropped by reranking.
    stage_start = time.perf_counter()
    collections = [] if request.skip_retrieval else _resolve_search_collections(
        store,
        request.source_collection,
        list(request.locales),
    )
    if not request.skip_retrieval and not collections:
        raise ValueError(
            "No selected language collection matches the requested locale scope."
        )

    retrieve_k = max(1, int(request.k))
    fetch_k = max(retrieve_k, request.fetch_k)
    raw_results: list[dict[str, Any]] = []
    total_units = len(collections) * max(1, len(request.search_types))
    unit = 0

    if request.skip_retrieval:
        update("retrieval", 1, 1, f"Retrieval skipped · {len(selected_candidates)} selected evidence records")

    for collection in collections:
        check_cancel()
        locale_codes = set(collection.get("_rag_locales") or collection.get("language_codes") or [])
        query = (
            query_metadata["prompt_query_fr"]
            if "fr" in locale_codes and "en" not in locale_codes
            else query_metadata["prompt_query"]
        )

        semantic_candidates: list[dict[str, Any]] = []
        if {"similarity", "mmr"} & set(request.search_types):
            try:
                semantic_candidates = _scope_rag_candidates(
                    store.semantic_candidates(
                        collection["name"],
                        query,
                        min(fetch_k, max(1, collection["count"])),
                    ),
                    collection,
                    locale_codes,
                )
            except ValueError as exc:
                # Precomputed-vector collections remain useful through the lexical
                # route even though they cannot embed a new query.
                if "lexical" not in request.search_types:
                    raise
                update(
                    "retrieval",
                    unit,
                    total_units,
                    f"Semantic route unavailable for {collection['name']}: {exc}",
                )

        if "similarity" in request.search_types:
            unit += 1
            update(
                "retrieval",
                unit,
                total_units,
                f"Similarity · {collection['name']} · {collection.get('_rag_route', '')}",
            )
            for rank, candidate in enumerate(semantic_candidates[:retrieve_k], start=1):
                row = dict(candidate)
                row["search_type"] = "similarity"
                row["search_rank"] = rank
                raw_results.append(row)

        if "lexical" in request.search_types:
            unit += 1
            update(
                "retrieval",
                unit,
                total_units,
                f"Lexical · {collection['name']} · {collection.get('_rag_route', '')}",
            )
            lexical_candidates = _scope_rag_candidates(
                store.lexical_search(
                    collection["name"],
                    query,
                    min(fetch_k, max(1, collection["count"])),
                ),
                collection,
                locale_codes,
            )
            for rank, candidate in enumerate(lexical_candidates[:retrieve_k], start=1):
                row = dict(candidate)
                row["collection"] = collection["name"]
                row["search_type"] = "lexical"
                row["search_rank"] = rank
                raw_results.append(row)

        if "mmr" in request.search_types:
            unit += 1
            update(
                "retrieval",
                unit,
                total_units,
                f"MMR · {collection['name']} · {collection.get('_rag_route', '')}",
            )
            mmr = _mmr_select(
                semantic_candidates,
                k=retrieve_k,
                lambda_mult=request.lambda_mult,
            )
            for rank, candidate in enumerate(mmr, start=1):
                row = dict(candidate)
                row["search_type"] = "mmr"
                row["search_rank"] = rank
                raw_results.append(row)

    # Deduplicate by logical record ID, retaining a retrieval-rank fusion score.
    update("deduplicate", 0, 1, f"Fusing {len(raw_results)} retrieval hits")
    dedup: dict[str, dict[str, Any]] = {}
    for item in raw_results:
        record = item["record"]
        logical = str(
            record.get("record_id")
            or item.get("id")
        )
        rrf = 1.0 / (float(request.rrf_k) + float(item.get("search_rank") or 1))
        if logical not in dedup:
            row = dict(item)
            row["rrf_score"] = rrf
            row["retrieval_hits"] = [{
                "collection": item.get("collection"),
                "search_type": item.get("search_type"),
                "rank": item.get("search_rank"),
            }]
            dedup[logical] = row
        else:
            dedup[logical]["rrf_score"] += rrf
            dedup[logical]["retrieval_hits"].append({
                "collection": item.get("collection"),
                "search_type": item.get("search_type"),
                "rank": item.get("search_rank"),
            })
            old_distance = dedup[logical].get("distance")
            new_distance = item.get("distance")
            if new_distance is not None and (
                old_distance is None or new_distance < old_distance
            ):
                dedup[logical]["distance"] = new_distance

    for item in selected_candidates:
        record = item["record"]
        logical = str(record.get("record_id") or item.get("id"))
        # A selected source wins over the retrieved copy of the same logical
        # record and receives a deliberately dominant fusion score.
        item = dict(item)
        item["rrf_score"] = max(1.0, float((dedup.get(logical) or {}).get("rrf_score") or 0.0))
        dedup[logical] = item

    deduped = sorted(
        dedup.values(),
        key=lambda item: (
            item.get("rrf_score", 0.0),
            _distance_similarity(item.get("distance")),
        ),
        reverse=True,
    )
    update("deduplicate", 1, 1, f"{len(deduped)} unique records after rank fusion")
    stages.append({
        "name": "retrieval",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "collections": list(dict.fromkeys(
            [item["name"] for item in collections]
            + [str(item.get("collection")) for item in selected_candidates if item.get("collection")]
        )),
            "retrieval_skipped": bool(request.skip_retrieval),
            "selected_evidence_count": len(selected_candidates),
            "routes": [
                {
                    "collection": item["name"],
                    "route": item.get("_rag_route"),
                    "languages": item.get("_rag_locales", []),
                }
                for item in collections
            ],
            "raw_results": len(raw_results),
            "deduplicated_results": len(deduped),
        },
    })
    check_cancel()

    # Step 4: rerank.
    stage_start = time.perf_counter()
    update("rerank", 0, 1, request.reranker)
    rerank_query = (
        query_metadata["prompt_query"]
        + "\n"
        + query_metadata["prompt_query_fr"]
    ).strip()
    # ``rerank_top_n`` is the single source of truth. Query decomposition may
    # transform the wording of the query, but it must not alter pipeline limits.
    # User-selected evidence is pinned: it is never allowed to disappear merely
    # because a reranker prefers retrieved neighbors.  Selected records consume
    # slots first, then the reranker fills the remaining requested slots.
    requested_top_n = len(deduped) if request.skip_retrieval else max(1, int(request.rerank_top_n))
    selected_pool = [item for item in deduped if item.get("selected_evidence")]
    retrieved_pool = [item for item in deduped if not item.get("selected_evidence")]
    effective_top_n = (
        len(deduped)
        if request.skip_retrieval
        else min(max(requested_top_n, len(selected_pool)), max(1, len(deduped)))
    )
    remaining_slots = max(0, effective_top_n - len(selected_pool))

    if request.skip_retrieval:
        reranked = selected_pool or deduped
        for item in reranked:
            item["rerank_score"] = item.get("rerank_score", 1.0)
    else:
        selected_ranked = []
        for item in selected_pool:
            row = dict(item)
            row["rerank_score"] = max(1.0, float(item.get("rerank_score") or 0.0))
            selected_ranked.append(row)

        reranked_retrieved: list[dict[str, Any]] = []
        if remaining_slots and retrieved_pool:
            if request.reranker == "cross_encoder":
                reranked_retrieved, rerank_warning = _cross_encoder_rerank(
                    rerank_query,
                    retrieved_pool,
                    remaining_slots,
                    request.cross_encoder_model,
                )
                if rerank_warning:
                    warnings.append(rerank_warning)
            elif request.reranker == "lexical":
                reranked_retrieved = _lexical_rerank(
                    rerank_query, retrieved_pool, remaining_slots
                )
            else:
                reranked_retrieved = retrieved_pool[:remaining_slots]
                for item in reranked_retrieved:
                    item["rerank_score"] = item.get("rrf_score", 0.0)
        reranked = selected_ranked + reranked_retrieved

    stages.append({
        "name": "rerank",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "mode": request.reranker,
            "requested_top_n": requested_top_n,
            "effective_top_n": len(reranked),
            "selected_evidence_pinned": len(selected_pool),
            "cross_encoder_model": request.cross_encoder_model,
        },
    })
    update("rerank", 1, 1, f"{len(reranked)} evidence records retained")
    check_cancel()

    # Step 5: build compact evidence context.
    stage_start = time.perf_counter()
    retrieval_context, works, evidence = _context_string(
        reranked,
        record_char_limit=request.evidence_record_char_limit,
        total_char_limit=request.evidence_total_char_limit,
    )
    sufficiency_issues = evidence_sufficiency_issues(evidence)
    stages.append({
        "name": "retrieval_context",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "evidence_count": len(evidence),
            "characters": len(retrieval_context),
            "sufficiency_issues": sufficiency_issues,
        },
    })
    update("context", 1, 1, f"{len(evidence)} evidence records packaged")
    if not evidence:
        raise ValueError("RAG evidence sufficiency failed: retrieval produced no evidence records.")
    if sufficiency_issues:
        detail = "; ".join(
            f"{item['evidence_id']} missing {item['missing']}"
            for item in sufficiency_issues
        )
        raise ValueError(f"RAG evidence sufficiency failed: {detail}")
    check_cancel()

    # Step 6: generate answer.
    stage_start = time.perf_counter()
    update("generation", 0, 1, f"Invoking {provider} · {model}")
    generation_prompt = FOCUSED_PROMPT.format(
        prompt_query=query_metadata["prompt_query"],
        prompt_instructions=query_metadata["prompt_instructions"],
        response_language=("French" if query_metadata.get("response_language") == "fr" else "English"),
        context=retrieval_context,
    )
    raw_answer = chat_complete(
        provider=provider,
        model=model,
        base_url=request.base_url,
        api_key=request.api_key,
        prompt=generation_prompt,
        options=request.generation,
        json_mode=False,
        max_tokens=(
            request.generation.num_predict
            if request.generation and request.generation.num_predict
            else 8192
        ),
        cancelled=cancelled,
    )
    stages.append({
        "name": "generation",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "provider": provider,
            "model": model,
            "characters": len(raw_answer),
        },
    })
    update("generation", 1, 1, "Draft generated")
    check_cancel()

    # Step 7: bind evidence IDs to bibliographic citations.
    stage_start = time.perf_counter()
    answer = (
        _bind_sources(
            raw_answer,
            evidence,
            request.include_works_cited,
        )
        if request.bind_citations
        else raw_answer
    )
    stages.append({
        "name": "bind_sources",
        "seconds": time.perf_counter() - stage_start,
        "detail": {
            "bound": request.bind_citations,
            "works": works,
        },
    })
    update("bind_sources", 1, 1, "Citations bound")

    return {
        "prompt": request.prompt,
        "query_metadata": query_metadata,
        "answer": answer,
        "raw_answer": raw_answer,
        "evidence": evidence,
        "works": works,
        "collections": [item["name"] for item in collections],
        "warnings": warnings,
        "stages": stages,
        "provider": provider,
        "model": model,
        "elapsed_seconds": time.perf_counter() - started,
        "retrieval": {
            "raw_count": len(raw_results),
            "deduplicated_count": len(deduped),
            "reranked_count": len(reranked),
            "search_types": list(request.search_types),
            "k": request.k,
            "fetch_k": request.fetch_k,
            "lambda_mult": request.lambda_mult,
            "rrf_k": request.rrf_k,
            "reranker": request.reranker,
            "rerank_top_n": request.rerank_top_n,
            "effective_rerank_top_n": len(reranked),
            "query_decomposition": request.query_decomposition,
            "query_decomposition_num_predict": request.query_decomposition_num_predict,
            "skip_retrieval": request.skip_retrieval,
            "selected_evidence_count": len(selected_candidates),
            "response_language": request.response_language,
            "evidence_record_char_limit": request.evidence_record_char_limit,
            "evidence_total_char_limit": request.evidence_total_char_limit,
            "evidence_sufficiency": {"passed": True, "issues": []},
        },
    }
