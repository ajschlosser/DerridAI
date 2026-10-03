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

"""Per-topic subscription authorization.

Every topic is authorized independently at subscribe time; events are also
filtered by audience at delivery. A private job that is not the caller's is
reported as not found (4404), exactly like a missing one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .broker import Subscriber
from .protocol import CLOSE_FORBIDDEN, CLOSE_MALFORMED, CLOSE_NOT_FOUND, valid_topic
from .resources import DATA_RESOURCES

# Background work that is not a tracked job, followable on ``activity:<kind>``.
# Every kind is administrator-only today (its REST status route is too).
ACTIVITY_KINDS = frozenset({"gutenberg"})


@dataclass(frozen=True)
class TopicDecision:
    topic: str
    allowed: bool
    code: int = 0
    reason: str = ""


def _job_managers() -> tuple[Any, ...]:
    from ..services import (
    capture_jobs,
    document_nlp_pack_jobs,
    llm_jobs,
    llm_tool_jobs,
    rag_jobs,
    upsert_jobs,
)

    return (llm_jobs, llm_tool_jobs, rag_jobs, upsert_jobs, capture_jobs, document_nlp_pack_jobs)


def find_job_summary(job_id: str) -> dict[str, Any] | None:
    for manager in _job_managers():
        summary = manager.realtime_job_summary(job_id)
        if summary is not None:
            return summary
    return None


def corpus_build_exists(build_id: str) -> bool:
    from ..corpus_builder import pdf_corpus_repository

    try:
        pdf_corpus_repository.get_build(build_id)
    except (KeyError, OSError, ValueError):
        return False
    return True


def can_follow_own_jobs(subscriber: Subscriber) -> bool:
    return subscriber.is_admin or bool({"rag.jobs.own", "rag.run"} & subscriber.capabilities)


def authorize_topic(subscriber: Subscriber, topic: str) -> TopicDecision:
    if not valid_topic(topic):
        return TopicDecision(topic, False, CLOSE_MALFORMED, "invalid topic")
    if topic == "jobs":
        if can_follow_own_jobs(subscriber):
            return TopicDecision(topic, True)
        return TopicDecision(topic, False, CLOSE_FORBIDDEN, "forbidden")
    if topic.startswith("job:"):
        job_id = topic.split(":", 1)[1]
        summary = find_job_summary(job_id)
        if subscriber.is_admin:
            if summary is not None or corpus_build_exists(job_id):
                return TopicDecision(topic, True)
            return TopicDecision(topic, False, CLOSE_NOT_FOUND, "not found")
        if (
            summary is not None
            and summary.get("type") == "rag"
            and summary.get("owner") == subscriber.username
            and can_follow_own_jobs(subscriber)
        ):
            return TopicDecision(topic, True)
        return TopicDecision(topic, False, CLOSE_NOT_FOUND, "not found")
    if topic.startswith("activity:"):
        if topic.split(":", 1)[1] not in ACTIVITY_KINDS:
            return TopicDecision(topic, False, CLOSE_NOT_FOUND, "not found")
        if subscriber.is_admin:
            return TopicDecision(topic, True)
        return TopicDecision(topic, False, CLOSE_FORBIDDEN, "forbidden")
    if topic.startswith("data:"):
        spec = DATA_RESOURCES.get(topic.split(":", 1)[1])
        if spec is None:
            return TopicDecision(topic, False, CLOSE_NOT_FOUND, "not found")
        if spec.allows(subscriber):
            return TopicDecision(topic, True)
        return TopicDecision(topic, False, CLOSE_FORBIDDEN, "forbidden")
    # Corpus Builder is an administrator workspace.
    if not subscriber.is_admin:
        return TopicDecision(topic, False, CLOSE_FORBIDDEN, "forbidden")
    if topic == "corpus-builds":
        return TopicDecision(topic, True)
    build_id = topic.split(":", 1)[1]
    if corpus_build_exists(build_id):
        return TopicDecision(topic, True)
    return TopicDecision(topic, False, CLOSE_NOT_FOUND, "not found")
