# Copyright 2026 Aaron John Schlosser, PhD.
"""Boundary-segmentation execution: LLM candidate batches and second-reader adjudication.

Moved verbatim out of PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's
module docstring for why a mixin, not free functions, and corpus_build_lifecycle.py's for
why every mixin's mypy stub block must be wrapped in `if TYPE_CHECKING:`).
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from .corpus_llm_helpers import _generation_options, _provider_roles, _stage_limits
from .corpus_models import (
    SEGMENTATION_PROMPT_VERSION,
    BoundaryAuditResponseModel,
    BoundaryBatchResponseModel,
)
from .corpus_record_quality import iso_now
from .corpus_segmentation import (
    _apply_boundary_adjudication_to_records,
    _boundary_audit_candidates,
    _candidate_route,
    _deterministic_boundary_candidates,
    _normalize_topology,
    _record_sizing_policy,
)
from .language_segmentation import profile_metadata
from .pipelines.corpus_segmentation import SegmentationSession


def _manifest_prompt_context(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return only source-document context that is appropriate for LLM boundary prompts."""
    return {
        key: manifest.get(key)
        for key in ("title", "document_author", "translator", "language", "document_type")
        if manifest.get(key) not in (None, "")
    }


class BuildSegmentationExecutionMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any

        def _append_warning(self, build_id: str, message: str) -> None: ...
        def _cancelled(self, build_id: str) -> bool: ...
        def _chat_json(self, request: dict[str, Any], prompt: str, *, response_model: type[Any], max_tokens: int = ..., schema_name: str = ..., attempts: int = ..., build_id: str = ..., roles: tuple[str, ...] = ..., escalated: bool = ...) -> dict[str, Any]: ...
        def _increment_metric(self, build_id: str, key: str, amount: int = 1) -> None: ...
        def _profile_for(self, build_id: str) -> dict[str, Any]: ...
        def _update(self, build_id: str, **changes: Any) -> dict[str, Any]: ...

    def _boundary_cache_fingerprint(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        manifest: dict[str, Any],
        request: dict[str, Any],
    ) -> str:
        generation = _generation_options(request)
        payload = {
            "prompt": SEGMENTATION_PROMPT_VERSION,
            "left_id": left.get("block_id"), "left_text": left.get("text"),
            "right_id": right.get("block_id"), "right_text": right.get("text"),
            "document_context": _manifest_prompt_context(manifest),
            "provider": request.get("provider"), "model": request.get("model"),
            "temperature": generation.temperature, "top_p": generation.top_p,
            "top_k": generation.top_k, "seed": generation.seed,
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


    def _boundary_call(
        self, session: SegmentationSession, request: dict[str, Any], prompt: str, *,
        response_model: type[Any], max_tokens: int, schema_name: str, build_id: str,
    ) -> dict[str, Any]:
        """Ask one boundary question through the corpus_segmentation pipeline, one provider role per stage."""

        def invoke(role: str, attempts: int, escalated: bool) -> dict[str, Any]:
            if role not in _provider_roles(request):
                raise LookupError("No review provider is configured for this build.")
            return self._chat_json(
                request, prompt, response_model=response_model, max_tokens=max_tokens,
                schema_name=schema_name, attempts=attempts, build_id=build_id,
                roles=(role,), escalated=escalated,
            )

        return session.run(invoke, response_contract=schema_name, providers=_provider_roles(request))


    def _segment_candidate_batch(
        self,
        batch: list[dict[str, Any]],
        blocks: list[dict[str, Any]],
        manifest: dict[str, Any],
        request: dict[str, Any],
        build_id: str,
        *,
        session: SegmentationSession,
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """Adjudicate a small set of already-filtered transitions in one call.

        The schema is intentionally binary. If the model cannot support SPLIT,
        returns malformed output, omits an item, or attempts an `uncertain` value,
        the transition deterministically remains KEEP.
        """
        items=[]
        for c in batch:
            i=int(c["index"])
            left,right=blocks[i],blocks[i+1]
            items.append(
                f"TRANSITION {left['block_id']} -> {right['block_id']}\n"
                f"Signals: {', '.join(c.get('signals') or [])}\n"
                f"LEFT:\n{str(left.get('text') or '')[-3200:]}\nRIGHT:\n{str(right.get('text') or '')[:3200]}"
            )
        context = _manifest_prompt_context(manifest)
        prompt=f"""You are a conservative semantic-boundary adjudicator for an auditable scholarly corpus.
Python has already filtered out ordinary prose and protected attribution-sensitive seams. For each listed transition choose SPLIT only when the right block clearly begins a new coherent discourse/argument unit because of a meaningful change in speaker, position holder, stance, target, quotation frame, discourse role, or argumentative move. Otherwise choose KEEP. Page changes and text length are never evidence. When in doubt, KEEP.

Document context: {json.dumps(context, ensure_ascii=False)}
When document_author is present, use it only as source-document authorship context. Do not assume it is the speaker or position holder, and do not invent an author or work when the document context does not supply one.

{"\n\n---\n\n".join(items)}

Return one compact decision per transition using its exact left-hand block ID in `after`. Do not return prose or source text."""
        limits=_stage_limits(request)
        try:
            result=self._boundary_call(session,request,prompt,response_model=BoundaryBatchResponseModel,max_tokens=min(limits["segmentation_num_predict"],1400),schema_name="derridai_boundary_batch_v6",build_id=build_id)
        except InterruptedError:
            raise
        except Exception as exc:
            return {},str(exc)
        valid_ids={str(c.get("after_block_id") or "") for c in batch}
        out={}
        for item in result.get("decisions") or []:
            after=str(item.get("after") or "")
            if after not in valid_ids:
                continue
            out[after]={
                "after_block_id":after,
                "decision":str(item.get("decision") or "keep"),
                "confidence":max(0.0,min(1.0,float(item.get("confidence") or 0))),
                "changes":list(item.get("changes") or []),
                "source":"local_batch_classifier",
            }
        return out,None


    def _boundary_editorial_examples(self, build_id: str, limit: int = 3) -> list[dict[str, Any]]:
        checkpoint = self.repo.load_checkpoint(build_id, "boundary_editorial_memory", {})
        if not isinstance(checkpoint, dict):
            return []
        examples = checkpoint.get("examples") if isinstance(checkpoint.get("examples"), list) else []
        return [dict(item) for item in examples[-max(0, limit):] if isinstance(item, dict)]


    def _record_boundary_editorial_example(
        self,
        build_id: str,
        *,
        left: dict[str, Any],
        right: dict[str, Any],
        action: str,
        transaction_id: str,
    ) -> None:
        checkpoint = self.repo.load_checkpoint(build_id, "boundary_editorial_memory", {})
        if not isinstance(checkpoint, dict):
            checkpoint = {}
        examples = list(checkpoint.get("examples") or [])
        examples.append({
            "at": iso_now(),
            "action": action,
            "transaction_id": transaction_id,
            "left_record_id": left.get("record_id"),
            "right_record_id": right.get("record_id"),
            "left_excerpt": str(left.get("text") or "")[-900:],
            "right_excerpt": str(right.get("text") or "")[:900],
            "source": "human_confirmed_boundary",
        })
        self.repo.save_checkpoint(build_id, "boundary_editorial_memory", {"examples": examples[-40:]})


    def _adjudicate_record_boundary_pair(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        manifest: dict[str, Any],
        request: dict[str, Any],
        build_id: str,
        *,
        session: SegmentationSession | None = None,
    ) -> dict[str, Any]:
        """Second-reader verdict on one record seam. Without ``session`` (a reviewer's request) the call gets its own trace."""
        left_ids = [str(value) for value in (left.get("source_block_ids") or []) if value]
        right_ids = [str(value) for value in (right.get("source_block_ids") or []) if value]
        if not left_ids or not right_ids:
            return {
                "decision": "uncertain", "confidence": 0.0,
                "reason": "The adjacent records do not expose source-block boundaries for adjudication.",
                "source": "llm_boundary_audit",
            }
        current_after = left_ids[-1]
        boundary_id = f"{left.get('record_id')}->{right.get('record_id')}"
        candidates = _boundary_audit_candidates(left, right)
        examples = self._boundary_editorial_examples(build_id, 3)
        examples_text = ""
        if examples:
            rendered=[]
            for example in examples:
                rendered.append(
                    f"HUMAN-CONFIRMED EXAMPLE ({example.get('action','boundary edit')}):\n"
                    f"LEFT END: {str(example.get('left_excerpt') or '')[-700:]}\n"
                    f"RIGHT START: {str(example.get('right_excerpt') or '')[:700]}"
                )
            examples_text = "\n\nRelevant editorial examples from this build:\n" + "\n---\n".join(rendered)
        context = _manifest_prompt_context(manifest)
        prompt = f"""You are the second-reader boundary adjudicator for an auditable scholarly corpus.
A deterministic segmentation system has already created two adjacent records. Decide whether the current boundary is semantically coherent.

Use KEEP when the left record ends a coherent discourse unit and the right record begins another.
Use MOVE_EARLIER only when material at the end of the left record clearly belongs with the right record.
Use MOVE_LATER only when material at the start of the right record clearly belongs with the left record.
Use UNCERTAIN when the evidence is genuinely ambiguous.

Strong signals include sentence/paragraph continuation, unfinished quotation framing, speaker or position-holder continuation, a heading stranded with the wrong unit, or an argumentative move that is visibly cut in half. Page boundaries and record length are never semantic evidence. Never rewrite, summarize, or invent text. If recommending a move, choose `suggested_after_block_id` only from the allowed seam IDs.

Document context: {json.dumps(context, ensure_ascii=False)}
When document_author is present, use it only as source-document authorship context. Do not assume it is the speaker or position holder, and do not invent an author or work when the document context does not supply one.
Boundary id: {boundary_id}
Current seam after block: {current_after}
Allowed seam IDs: {json.dumps(candidates, ensure_ascii=False)}

LEFT RECORD END:
{str(left.get('text') or '')[-4200:]}

RIGHT RECORD START:
{str(right.get('text') or '')[:4200]}
{examples_text}

Return one decision for the exact boundary id. `signals` should contain compact labels such as sentence_continuation, quotation_continuation, heading_attachment, attribution_continuation, argumentative_transition, or coherent_boundary."""
        limits = _stage_limits(request)
        opened: SegmentationSession | None = None
        try:
            if session is None:
                session = opened = SegmentationSession.open()
            result = self._boundary_call(
                session, request, prompt, response_model=BoundaryAuditResponseModel,
                max_tokens=min(int(limits.get("reconciliation_num_predict") or 1000), 1200),
                schema_name="derridai_boundary_second_reader_v1", build_id=build_id,
            )
        except InterruptedError:
            if opened is not None:
                opened.finish(cancelled=True)
            raise
        except Exception as exc:
            if opened is not None:
                opened.finish()
            return {
                "boundary_id": boundary_id, "decision": "uncertain", "confidence": 0.0,
                "reason": f"Boundary second-reader call failed: {exc}",
                "source": "llm_boundary_audit", "error": str(exc),
                **({"pipeline": session.identity()} if session is not None else {}),
            }
        if opened is not None:
            opened.finish()
        pipeline = session.identity()
        item = next((row for row in (result.get("decisions") or []) if str(row.get("boundary_id") or "") == boundary_id), None)
        if not isinstance(item, dict):
            return {
                "boundary_id": boundary_id, "decision": "uncertain", "confidence": 0.0,
                "reason": "The boundary second reader returned no usable decision.",
                "source": "llm_boundary_audit", "pipeline": pipeline,
            }
        decision = str(item.get("decision") or "uncertain")
        suggested = str(item.get("suggested_after_block_id") or "").strip() or None
        if decision == "move_earlier":
            valid = [value for value in candidates if value in left_ids and value != current_after]
            if suggested not in valid:
                decision, suggested = "uncertain", None
        elif decision == "move_later":
            valid = [value for value in candidates if value in right_ids[:-1] or value in right_ids[:2]]
            if suggested not in valid:
                decision, suggested = "uncertain", None
        else:
            suggested = current_after if decision == "keep" else None
        return {
            "boundary_id": boundary_id,
            "left_record_id": left.get("record_id"),
            "right_record_id": right.get("record_id"),
            "decision": decision,
            "suggested_after_block_id": suggested,
            "current_after_block_id": current_after,
            "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0.0))),
            "signals": list(item.get("signals") or []),
            "reason": str(item.get("reason") or "").strip(),
            "source": "llm_boundary_audit",
            "editorial_examples_used": len(examples),
            "adjudicated_at": iso_now(),
            "pipeline": pipeline,
        }


    def _audit_suspicious_record_boundaries(
        self, records: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str,
    ) -> dict[str, int]:
        threshold = float(self._profile_for(build_id).get("min_boundary_confidence") or 0.72)
        pairs=[]
        for index, (left, right) in enumerate(zip(records, records[1:])):
            left_flags = list(left.get("boundary_quality_issues") or [])
            right_flags = list(right.get("boundary_quality_issues") or [])
            heuristic = any(str(item.get("code") or "") == "boundary_suspect" and str(item.get("edge") or "") == "end" for item in left_flags) or any(str(item.get("code") or "") == "boundary_suspect" and str(item.get("edge") or "") == "start" for item in right_flags)
            unresolved = bool(left.get("boundary_review_after") or right.get("boundary_review_before"))
            if heuristic or unresolved:
                pairs.append((index, left, right))
        # This is a second-reader pass, not another book-scale segmentation pass.
        # Keep it bounded even on pathologically noisy extraction.
        pairs = pairs[:24]
        metrics = {"audited": 0, "keep": 0, "move": 0, "uncertain": 0, "failed": 0}
        decisions=[]
        # One trace for the pass. If the pipeline cannot be resolved, each pair tries on its
        # own and records that failure as an uncertain verdict without a model call.
        session: SegmentationSession | None = None
        if pairs:
            try:
                session = SegmentationSession.open()
            except RuntimeError:
                session = None
        try:
            for _, left, right in pairs:
                if self._cancelled(build_id):
                    raise InterruptedError("Corpus build cancelled")
                decision = self._adjudicate_record_boundary_pair(left, right, manifest, request, build_id, session=session)
                decisions.append(decision)
                metrics["audited"] += 1
                choice = str(decision.get("decision") or "uncertain")
                if decision.get("error"):
                    metrics["failed"] += 1
                if choice == "keep":
                    metrics["keep"] += 1
                elif choice in {"move_earlier", "move_later"}:
                    metrics["move"] += 1
                else:
                    metrics["uncertain"] += 1
                _apply_boundary_adjudication_to_records(left, right, decision, threshold=threshold)
        except InterruptedError:
            if session is not None:
                session.finish(cancelled=True)
            raise
        if session is not None:
            session.finish()
        self.repo.save_checkpoint(build_id, "boundary_second_reader", {"decisions": decisions, "metrics": metrics, "completed_at": iso_now()})
        return metrics


    def _segment(self, blocks: list[dict[str, Any]], manifest: dict[str, Any], request: dict[str, Any], build_id: str) -> list[dict[str, Any]]:
        """Build topology with deterministic-first routing and bounded LLM work.

        Human review is no longer an output of ordinary model uncertainty. The
        builder owns the topology: protected/weak seams KEEP, obvious structural
        seams SPLIT, and only a budgeted ambiguous subset reaches the LLM. The
        binary classifier's omission/failure/low confidence also means KEEP.
        """
        profile=self._profile_for(build_id)
        language = str(
            manifest.get("language")
            or manifest.get("document_language")
            or ""
        ).strip() or None
        threshold=float(profile.get("min_boundary_confidence") or 0.72)
        sizing_policy=_record_sizing_policy(request,profile)
        _=sizing_policy["absolute_record_chars"]
        index_by_id={str(block.get("block_id") or ""):i for i,block in enumerate(blocks)}
        candidates=_deterministic_boundary_candidates(blocks,profile,language)
        state=self.repo.load_checkpoint(build_id,"local_boundary_state",{})
        if not isinstance(state,dict): state={}
        decisions=state.get("decisions") if isinstance(state.get("decisions"),dict) else {}

        accepted=[]
        boundary_reviews=[]
        llm_candidates=[]
        deterministic_split_count=0
        deterministic_keep_count=0
        for candidate in candidates:
            i=int(candidate.get("index") or 0)
            route=_candidate_route(candidate,profile)
            if route=="split":
                accepted.append({**candidate,"decision":"split","confidence":1.0,"changes":[],"source":"deterministic_structural_split"})
                deterministic_split_count+=1
            elif route=="keep":
                deterministic_keep_count+=1
            else:
                llm_candidates.append(candidate)

        import math
        max_adjudications=min(16,max(4,int(math.ceil(max(1,len(blocks))*float(profile.get("max_llm_boundary_calls_per_100_atoms") or 6)/100.0))))
        llm_candidates=sorted(llm_candidates,key=lambda c:float(c.get("candidate_score") or 0),reverse=True)
        budget_skipped=max(0,len(llm_candidates)-max_adjudications)
        llm_candidates=llm_candidates[:max_adjudications]
        batch_size=max(1,min(12,int(profile.get("boundary_batch_size") or 6)))
        llm_split_count=0
        llm_keep_count=budget_skipped
        batch_call_count=0
        classifier_failures=0

        # Reuse only provenance-compatible local decisions. The fingerprint binds
        # the prompt version, evidence text, model, and relevant generation knobs.
        pending=[]
        for candidate in llm_candidates:
            i=int(candidate["index"])
            left,right=blocks[i],blocks[i+1]
            bid=str(candidate["after_block_id"])
            fingerprint=self._boundary_cache_fingerprint(left,right,manifest,request)
            cached=decisions.get(bid)
            if isinstance(cached,dict) and cached.get("fingerprint")==fingerprint and isinstance(cached.get("pair"),dict):
                pair=cached["pair"]
                if pair.get("decision")=="split" and float(pair.get("confidence") or 0)>=threshold:
                    accepted.append({**candidate,**pair,"source":"cached_local_classifier"}); llm_split_count+=1
                else: llm_keep_count+=1
            else:
                pending.append((candidate,fingerprint))

        completed=len(llm_candidates)-len(pending)
        # One pipeline trace for the pass's batch calls. Without a resolvable pipeline no
        # boundary question is asked: the ambiguous transitions stay KEEP, are counted as
        # classifier failures, and are not cached, so a later run asks them again.
        session: SegmentationSession | None = None
        if pending:
            try:
                session=SegmentationSession.open()
            except RuntimeError as exc:
                classifier_failures+=len(pending); llm_keep_count+=len(pending)
                self._increment_metric(build_id,"local_boundary_classifier_failures",len(pending))
                self._append_warning(build_id,f"{exc} {len(pending)} ambiguous boundary transition(s) were kept without a model call.")
                pending=[]
        try:
            for offset in range(0,len(pending),batch_size):
                if self._cancelled(build_id): raise InterruptedError("Corpus build cancelled")
                chunk=pending[offset:offset+batch_size]
                batch=[item[0] for item in chunk]
                results,failure=self._segment_candidate_batch(batch,blocks,manifest,request,build_id,session=session)
                batch_call_count+=1
                if failure:
                    classifier_failures+=len(batch)
                    self._increment_metric(build_id,"local_boundary_classifier_failures",len(batch))
                for candidate,fingerprint in chunk:
                    bid=str(candidate["after_block_id"])
                    pair=results.get(bid) or {"after_block_id":bid,"decision":"keep","confidence":0.0,"changes":[],"source":"deterministic_keep_after_omission"}
                    decisions[bid]={"pair":pair,"failure":failure,"fingerprint":fingerprint,"pipeline":session.identity()}
                    if pair.get("decision")=="split" and float(pair.get("confidence") or 0)>=threshold:
                        accepted.append({**candidate,**pair,"source":"local_batch_classifier"}); llm_split_count+=1
                    else:
                        llm_keep_count+=1
                self.repo.save_checkpoint(build_id,"local_boundary_state",{"decisions":decisions})
                completed+=len(chunk)
                self._update(build_id,stage="segmenting",progress=0.12+0.23*(completed/max(1,len(llm_candidates))),boundary_candidates_completed=min(len(candidates),deterministic_split_count+deterministic_keep_count+completed),boundary_candidate_count=len(candidates))
        except InterruptedError:
            if session is not None: session.finish(cancelled=True)
            raise
        if session is not None: session.finish()

        def grouped(boundaries:list[dict[str,Any]])->list[list[dict[str,Any]]]:
            split_ids={str(item.get("after_block_id") or "") for item in boundaries}
            out=[]; current=[]
            for block in blocks:
                current.append(block)
                if str(block.get("block_id") or "") in split_ids:
                    out.append(current); current=[]
            if current: out.append(current)
            return out

        # Semantic topology is now normalized deterministically toward the soft
        # retrieval-size policy. Existing semantic boundaries are preserved; new
        # size-optimized boundaries record that they are retrieval boundaries, not
        # claims that the argument itself ends there.
        accepted, normalization_reviews, normalization_metrics = _normalize_topology(
            blocks, accepted, sizing_policy, language
        )
        boundary_reviews.extend(normalization_reviews)
        provisional=[item for item in accepted if item.get("boundary_kind") in {"retrieval_size_optimized","absolute_size_safety"}]
        accepted.sort(key=lambda item:index_by_id.get(str(item.get("after_block_id") or ""),10**9))
        review_map={(str(i.get("after_block_id") or ""),str(i.get("next_block_id") or ""),str(i.get("kind") or "")):i for i in boundary_reviews}
        boundary_reviews=list(review_map.values())

        build=self.repo.get_build(build_id)
        build.update({
            "segmentation_blocked":False,
            "segmentation_unresolved_regions":boundary_reviews[:500],
            "segmentation_boundary_reviews":boundary_reviews[:500],
            "boundary_review_count":len(boundary_reviews),
            "segmentation_failed_windows":0,"segmentation_total_windows":0,"segmentation_recovered_windows":0,
            "segmentation_degraded":bool(boundary_reviews),
            "boundary_candidate_count":len(candidates),"boundary_count":len(accepted),
            "provisional_boundary_count":len(provisional),
            "size_optimized_boundary_count":int(normalization_metrics.get("size_optimized_splits") or 0),
            "absolute_safety_boundary_count":int(normalization_metrics.get("absolute_safety_splits") or 0),
            "long_exception_record_count":int(normalization_metrics.get("long_exception_records") or 0),
            "record_sizing_policy":sizing_policy,
            "segmentation_language_profile":profile_metadata(
                language,
                "\n".join(str(block.get("text") or "") for block in blocks[:8]),
            ),
            "boundary_deterministic_split_count":deterministic_split_count,
            "boundary_deterministic_keep_count":deterministic_keep_count,
            "boundary_llm_adjudication_count":len(llm_candidates),
            "boundary_llm_batch_call_count":batch_call_count,
            "boundary_llm_split_count":llm_split_count,
            "boundary_llm_keep_count":llm_keep_count,
            "boundary_budget_skipped_count":budget_skipped,
            "boundary_classifier_failure_count":classifier_failures,
        })
        self.repo.save_build(build)
        self.repo.save_checkpoint(build_id,"boundaries_partial",accepted)
        if boundary_reviews:
            self._append_warning(build_id,f"Corpus topology contains {len(boundary_reviews)} demonstrated provenance hazard(s) requiring boundary review. Ordinary uncertainty has already resolved conservatively to KEEP.")
        self._update(build_id,stage="reconciling",progress=0.40)
        return accepted

