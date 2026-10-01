# Copyright 2026 Aaron John Schlosser, PhD.
"""WS /api/ws/events: one authenticated realtime connection per browser session."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from ..auth import SESSION_COOKIE
from ..config import settings
from .auth import capabilities_for, origin_allowed, revalidate, session_user
from .resources import follows_any_resource
from .broker import EventBroker, Subscriber, broker
from .protocol import (
    CLOSE_FORBIDDEN,
    CLOSE_INTERNAL,
    CLOSE_NORMAL,
    CLOSE_POLICY,
    CLOSE_UNAUTHENTICATED,
    MAX_TOPICS_PER_CONNECTION,
    PROTOCOL_VERSION,
    ClientMessage,
    Event,
    ProtocolError,
    parse_client_message,
)
from .subscriptions import authorize_topic

logger = logging.getLogger("derridai.realtime")
router = APIRouter()

# Client message rate limit (token bucket): sustained rate and burst.
CLIENT_MESSAGES_PER_SECOND = 10.0
CLIENT_MESSAGE_BURST = 30.0


class _Close(Exception):
    def __init__(self, code: int, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


def _now() -> str:
    return datetime.now(UTC).isoformat()


class RealtimeSession:
    """Protocol state machine for one accepted socket."""

    def __init__(self, websocket: WebSocket, user: Any, event_broker: EventBroker) -> None:
        self.websocket = websocket
        self.broker = event_broker
        self.cookie = websocket.cookies.get(SESSION_COOKIE)
        self.user = user
        self.subscriber = Subscriber(
            username=str(user.username),
            role=str(user.role),
            capabilities=capabilities_for(user),
            connection_id=uuid.uuid4().hex[:12],
            user_id=getattr(user, "id", None),
        )
        self.last_client_message = time.monotonic()
        self._tokens = CLIENT_MESSAGE_BURST
        self._token_at = time.monotonic()
        self._send_lock = asyncio.Lock()

    async def send(self, frame: dict[str, Any]) -> None:
        async with self._send_lock:
            await self.websocket.send_json(frame)

    async def send_events(self, events: list[Event]) -> None:
        for event in events:
            await self.send(event.envelope())

    async def resync_required(self, reason: str) -> None:
        await self.send({
            "type": "connection.resync_required",
            "timestamp": _now(),
            "payload": {"reason": reason, "last_event_id": self.broker.last_event_id},
        })

    # -- inbound -------------------------------------------------------------
    def _rate_limited(self) -> bool:
        now = time.monotonic()
        self._tokens = min(CLIENT_MESSAGE_BURST, self._tokens + (now - self._token_at) * CLIENT_MESSAGES_PER_SECOND)
        self._token_at = now
        if self._tokens < 1:
            return True
        self._tokens -= 1
        return False

    async def handle(self, message: ClientMessage) -> None:
        if message.type == "ping":
            await self.send({"type": "pong", "timestamp": _now(), "payload": {"last_event_id": self.broker.last_event_id}})
            return
        if message.type == "unsubscribe":
            self.subscriber.topics.difference_update(message.topics)
            await self._subscription_updated([])
            return
        if message.type == "subscribe":
            rejected = []
            accepted: set[str] = set()
            for topic in message.topics:
                if topic in self.subscriber.topics or topic in accepted:
                    continue
                if len(self.subscriber.topics) + len(accepted) >= MAX_TOPICS_PER_CONNECTION:
                    raise ProtocolError(CLOSE_POLICY, "too many topics")
                decision = await asyncio.to_thread(authorize_topic, self.subscriber, topic)
                if decision.allowed:
                    accepted.add(topic)
                else:
                    rejected.append({"topic": topic, "code": decision.code, "reason": decision.reason})
            self.broker.add_topics(self.subscriber, accepted)
            await self._subscription_updated(rejected)
        if message.last_event_id is not None and message.type in {"subscribe", "resync"}:
            await self._replay(message.last_event_id)
        elif message.type == "resync":
            await self.resync_required("client_requested")

    async def _subscription_updated(self, rejected: list[dict[str, Any]]) -> None:
        await self.send({
            "type": "subscription.updated",
            "timestamp": _now(),
            "payload": {"topics": sorted(self.subscriber.topics), "rejected": rejected},
        })

    async def _replay(self, last_event_id: int) -> None:
        # Replayed events go through the outgoing queue so they are delivered in
        # event_id order ahead of anything published afterwards.
        if not self.broker.resume(self.subscriber, last_event_id):
            await self.resync_required("replay_unavailable")

    async def reader(self) -> None:
        while True:
            message = await self.websocket.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", CLOSE_NORMAL))
            raw = message.get("text")
            if raw is None:
                raw = message.get("bytes") or b""
            self.last_client_message = time.monotonic()
            if self._rate_limited():
                raise _Close(CLOSE_POLICY, "rate limit exceeded")
            try:
                parsed = parse_client_message(raw, max_bytes=settings.realtime_max_client_message_bytes)
                await self.handle(parsed)
            except ProtocolError as exc:
                raise _Close(exc.code, exc.reason) from exc

    # -- outbound ------------------------------------------------------------
    async def writer(self) -> None:
        wake = self.subscriber.wake
        assert wake is not None
        while True:
            await wake.wait()
            wake.clear()
            events, overflowed = self.subscriber.queue.drain()
            if overflowed:
                await self.resync_required("backpressure")
            await self.send_events(events)

    async def heartbeat(self) -> None:
        interval = max(1.0, float(settings.realtime_heartbeat_seconds))
        idle_timeout = max(interval, float(settings.realtime_idle_timeout_seconds))
        while True:
            await asyncio.sleep(interval)
            user = await revalidate(self.cookie)
            if user is None or not getattr(user, "active", True):
                raise _Close(CLOSE_UNAUTHENTICATED, "session expired")
            if user.role != self.user.role or user.username != self.user.username:
                await self.send({"type": "auth.permissions_changed", "timestamp": _now(), "payload": {}})
                raise _Close(CLOSE_FORBIDDEN, "permissions changed")
            if time.monotonic() - self.last_client_message > idle_timeout:
                raise _Close(CLOSE_POLICY, "idle timeout")
            await self.send({
                "type": "connection.heartbeat",
                "timestamp": _now(),
                "payload": {"last_event_id": self.broker.last_event_id},
            })


@router.websocket("/api/ws/events")
async def realtime_events(websocket: WebSocket) -> None:
    await run_realtime_session(websocket, broker)


async def run_realtime_session(websocket: WebSocket, event_broker: EventBroker) -> None:
    await websocket.accept()
    if not settings.realtime_enabled:
        await websocket.close(code=CLOSE_FORBIDDEN, reason="realtime disabled")
        return
    if not origin_allowed(websocket):
        await websocket.close(code=CLOSE_FORBIDDEN, reason="origin not allowed")
        return
    user = await session_user(websocket)
    if user is None or not getattr(user, "active", True):
        await websocket.close(code=CLOSE_UNAUTHENTICATED, reason="authentication required")
        return
    session = RealtimeSession(websocket, user, event_broker)
    subscriber = session.subscriber
    if (
        not subscriber.is_admin
        and not ({"rag.jobs.own", "rag.run"} & subscriber.capabilities)
        and not follows_any_resource(subscriber)
    ):
        # No topic is available to this role.
        await websocket.close(code=CLOSE_FORBIDDEN, reason="no realtime topics available")
        return
    subscriber.loop = asyncio.get_running_loop()
    subscriber.wake = asyncio.Event()
    event_broker.register(subscriber)
    close_code = CLOSE_NORMAL
    close_reason = ""
    logger.info(
        "realtime connected id=%s user_id=%s role=%s",
        subscriber.connection_id, subscriber.user_id, subscriber.role,
    )
    tasks: list[asyncio.Task[None]] = []
    try:
        await session.send({
            "type": "connection.ready",
            "timestamp": _now(),
            "payload": {
                "protocol_version": PROTOCOL_VERSION,
                "connection_id": subscriber.connection_id,
                "last_event_id": event_broker.last_event_id,
                "heartbeat_seconds": settings.realtime_heartbeat_seconds,
                "idle_timeout_seconds": settings.realtime_idle_timeout_seconds,
            },
        })
        tasks = [
            asyncio.create_task(session.reader()),
            asyncio.create_task(session.writer()),
            asyncio.create_task(session.heartbeat()),
        ]
        done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            exc = task.exception()
            if isinstance(exc, _Close):
                close_code, close_reason = exc.code, exc.reason
            elif isinstance(exc, WebSocketDisconnect):
                close_code = exc.code
            elif exc is not None:
                logger.warning("realtime connection %s failed: %s", subscriber.connection_id, type(exc).__name__)
                close_code, close_reason = CLOSE_INTERNAL, "internal error"
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(BaseException):
                await task
        event_broker.unregister(subscriber)
        if websocket.application_state != WebSocketState.DISCONNECTED and websocket.client_state != WebSocketState.DISCONNECTED:
            with contextlib.suppress(Exception):
                await websocket.close(code=close_code, reason=close_reason)
        logger.info(
            "realtime disconnected id=%s user_id=%s role=%s subscriptions=%d queue=%d coalesced=%d dropped=%d code=%s",
            subscriber.connection_id, subscriber.user_id, subscriber.role, len(subscriber.topics),
            len(subscriber.queue), subscriber.queue.coalesced, subscriber.queue.dropped, close_code,
        )
