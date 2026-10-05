# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Bounded, server-owned advisory history; never documentary evidence.

Selection pins the preceding turn and can rank older turns with an already
loaded local model. Recent fallback is explicit; generation consumption is separate.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .research_thread_store import ResearchThreadStore, ThreadNotFound


class ContextBudgetExceeded(ValueError):
    """The preceding turn cannot fit without silently losing its meaning."""


@dataclass(frozen=True)
class ThreadContextPolicy:
    max_turns: int = 4
    max_characters: int = 24000
    max_answer_characters: int = 12000
    include_answers: bool = True

    def __post_init__(self) -> None:
        for name, upper in (
            ("max_turns", 16),
            ("max_characters", 128000),
            ("max_answer_characters", 64000),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError(f"{name} must be an integer between 1 and {upper}")
        if type(self.include_answers) is not bool:
            raise ValueError("include_answers must be boolean")


@dataclass(frozen=True)
class ThreadContextItem:
    turn_id: str
    ordinal: int
    role: Literal["user", "assistant"]
    text: str
    source: Literal["immediate_previous", "recent_fallback", "semantic"]
    response_id: str | None = None


@dataclass(frozen=True)
class ThreadContextPacket:
    items: tuple[ThreadContextItem, ...]
    warnings: tuple[str, ...]
    policy: ThreadContextPolicy
    strategy: str = "previous_and_recent_fallback"
    ranking_model: str | None = None
    prior_turn_count: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": "research-thread-context-v2",
            "strategy": self.strategy,
            "ranking_model": self.ranking_model,
            "prior_turn_count": self.prior_turn_count,
            "advisory": True,
            "evidentiary": False,
            "policy": asdict(self.policy),
            "items": [asdict(item) for item in self.items],
            "selected_turn_ids": list(
                dict.fromkeys(item.turn_id for item in self.items)
            ),
            "warnings": list(self.warnings),
            "character_count": sum(len(item.text) for item in self.items),
        }


def select_thread_context(
    store: ResearchThreadStore,
    turn_id: str,
    owner: str,
    read_job: Callable[[str], dict[str, Any]],
    *,
    policy: ThreadContextPolicy | None = None,
    read_saved: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    rank_older: Callable[[str, list[str]], tuple[list[float] | None, str | None]] | None = None,
) -> ThreadContextPacket:
    """Load only the owned thread and verified completed answer artifacts.

    The job reader is supplied by the server, never the HTTP client. Missing
    answers retain their exact question with an explicit warning. Unexpected
    reader failures propagate instead of masquerading as empty history.
    """
    policy = policy or ThreadContextPolicy()
    current = store.get_turn(turn_id, owner)
    thread = store.get_thread(current["thread_id"], owner)
    previous = [
        turn
        for turn in thread["turns"]
        if turn["ordinal"] < current["ordinal"] and turn["status"] == "completed"
    ]
    warnings: list[str] = []
    selected: list[ThreadContextItem] = []
    characters = 0
    selected_count = 0
    candidates: list[list[ThreadContextItem]] = []
    if len(previous) > 1 and policy.max_turns > 1:
        warnings.append("semantic_selection_unavailable_using_recent_turns")
    # Bound artifact reads even when a long thread contains many oversized turns.
    for index, turn in enumerate(reversed(previous[-32:])):
        if index > 0 and policy.max_turns == 1:
            break
        source: Literal["immediate_previous", "recent_fallback", "semantic"] = (
            "immediate_previous" if index == 0 else "recent_fallback"
        )
        items = [
            ThreadContextItem(
                turn["turn_id"], turn["ordinal"], "user", turn["user_question"], source
            )
        ]
        if policy.include_answers:
            job = None
            if turn["job_id"]:
                try:
                    job = read_job(turn["job_id"])
                except KeyError:
                    pass
            # Never accept another owner's run or an unrelated run as this answer.
            valid = (
                isinstance(job, dict)
                and job.get("id") == turn["job_id"]
                and job.get("owner") == owner
                and job.get("turn_id") == turn["turn_id"]
                and job.get("status") == "completed"
            )
            result = job.get("result") if valid else None
            answer = result.get("answer") if isinstance(result, dict) else None
            if (job is None or valid) and not answer and read_saved and turn.get("response_record_id"):
                try:
                    recovered = read_saved(turn, owner)
                except (KeyError, ThreadNotFound):
                    recovered = None
                if isinstance(recovered, dict):
                    answer = (recovered.get("result") or {}).get("answer")
                    warnings.append(f"prior_answer_recovered:{turn['turn_id']}")

            if isinstance(answer, str) and answer.strip():
                if len(answer) > policy.max_answer_characters:
                    if index == 0:
                        raise ContextBudgetExceeded(
                            "Immediate previous answer exceeds the context answer budget"
                        )
                    warnings.append(
                        f"older_turn_exceeds_answer_budget:{turn['turn_id']}"
                    )
                    continue
                items.append(
                    ThreadContextItem(
                        turn["turn_id"], turn["ordinal"], "assistant", answer, source, turn.get("research_run_id")
                    )
                )
            else:
                warnings.append(f"prior_answer_unavailable:{turn['turn_id']}")
        candidates.append(items)
    # Pin the preceding completed turn before any relevance ranking. Limit the
    # ranking input independently; the selected packet always keeps exact text.
    strategy = "previous_and_recent_fallback"
    ranking_model = None
    if candidates and len(candidates) > 1 and policy.max_turns > 1 and rank_older:
        scores, ranking_model = rank_older(current["user_question"], [
            "\n".join(item.text for item in items)[:2000] for items in candidates[1:]
        ])
        if scores is not None:
            if len(scores) != len(candidates) - 1 or not all(
                isinstance(score, (int, float)) and not isinstance(score, bool) and math.isfinite(score)
                for score in scores
            ):
                warnings.append("semantic_selection_invalid_scores_using_recent_turns")
            else:
                ordered = sorted(zip(candidates[1:], scores), key=lambda row: (-row[1], -row[0][0].ordinal))
                candidates = [candidates[0]] + [[
                    ThreadContextItem(item.turn_id, item.ordinal, item.role, item.text, "semantic")
                    for item in items
                ] for items, _ in ordered]
                strategy = "previous_and_semantic"
                warnings.remove("semantic_selection_unavailable_using_recent_turns")
    for items in candidates:
        if selected_count >= policy.max_turns:
            break
        size = sum(len(item.text) for item in items)
        if characters + size > policy.max_characters:
            if items[0].source == "immediate_previous":
                raise ContextBudgetExceeded("Immediate previous turn exceeds the context budget")
            warnings.append(f"older_turn_exceeds_context_budget:{items[0].turn_id}")
            continue
        selected.extend(items)
        selected_count += 1
        characters += size
    selected.sort(key=lambda item: (item.ordinal, item.role == "assistant"))
    return ThreadContextPacket(tuple(selected), tuple(warnings), policy, strategy, ranking_model, len(previous))


def rank_cached_thread_context(query: str, texts: list[str], model: str) -> tuple[list[float] | None, str]:
    """Use only an already loaded local model: no download or remote inference."""
    from .cross_encoder import predict_scores

    scores, _ = predict_scores(
        [(query, text) for text in texts], model_name=model,
        timeout_seconds=2.0, cached_only=True,
    )
    return scores, model
