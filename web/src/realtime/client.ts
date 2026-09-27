/* Copyright 2026 Aaron John Schlosser, PhD. */
// The one realtime connection per browser session (docs/REALTIME.md). Views never open sockets:
// they subscribe to topics here. The socket only notifies; authoritative state is re-read over
// REST/GraphQL whenever the stream cannot guarantee continuity (onResync).
import {
  CLOSE_CODES,
  isResourceEvent,
  topicsForEvent,
  type ClientMessage,
  type RealtimeEvent,
  type ServerFrame,
} from "./protocol";

export type RealtimeStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "degraded"
  | "reconnecting"
  | "offline";

export interface SocketLike {
  readyState: number;
  onopen: ((event: unknown) => void) | null;
  onmessage: ((event: { data: unknown }) => void) | null;
  onclose: ((event: { code: number; reason?: string }) => void) | null;
  onerror: ((event: unknown) => void) | null;
  send(data: string): void;
  close(code?: number, reason?: string): void;
}

export interface RealtimeClientOptions {
  url?: () => string;
  createSocket?: (url: string) => SocketLike;
  random?: () => number;
  baseBackoffMs?: number;
  maxBackoffMs?: number;
  /** Consecutive failed attempts before fallback polling is declared. */
  fallbackAfterFailures?: number;
  /** A connection that stays up this long resets the backoff. */
  stableAfterMs?: number;
  onAuthExpired?: () => void;
  onPermissionsChanged?: () => void;
}

export type EventHandler = (event: RealtimeEvent) => void;
export type ResyncHandler = (reason: string) => void;
export type StatusHandler = (status: RealtimeStatus, fallbackActive: boolean) => void;

const OPEN = 1;

function defaultUrl(): string {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}/api/ws/events`;
}

export class RealtimeClient {
  status: RealtimeStatus = "idle";
  fallbackActive = false;
  lastEventId = 0;

  private readonly options: Required<
    Omit<RealtimeClientOptions, "onAuthExpired" | "onPermissionsChanged">
  > &
    Pick<RealtimeClientOptions, "onAuthExpired" | "onPermissionsChanged">;
  private socket: SocketLike | null = null;
  private running = false;
  private ready = false;
  private attempt = 0;
  private failures = 0;
  private revisions = new Map<string, number>();
  private handlers = new Map<string, Set<EventHandler>>();
  private resyncHandlers = new Set<ResyncHandler>();
  private statusHandlers = new Set<StatusHandler>();
  private reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  private pingTimer: ReturnType<typeof setInterval> | undefined;
  private stableTimer: ReturnType<typeof setTimeout> | undefined;
  private lastFrameAt = 0;
  private heartbeatMs = 20_000;

  constructor(options: RealtimeClientOptions = {}) {
    this.options = {
      url: options.url ?? defaultUrl,
      createSocket: options.createSocket ?? ((url) => new WebSocket(url) as unknown as SocketLike),
      random: options.random ?? Math.random,
      baseBackoffMs: options.baseBackoffMs ?? 1000,
      maxBackoffMs: options.maxBackoffMs ?? 30_000,
      fallbackAfterFailures: options.fallbackAfterFailures ?? 3,
      stableAfterMs: options.stableAfterMs ?? 10_000,
      onAuthExpired: options.onAuthExpired,
      onPermissionsChanged: options.onPermissionsChanged,
    };
  }

  /** Connect once an authenticated session exists. Idempotent. */
  start(): void {
    if (this.running) return;
    this.running = true;
    this.attempt = 0;
    this.failures = 0;
    this.connect("connecting");
  }

  /** Tear down on logout/session expiry; never reconnects until start() is called again. */
  stop(): void {
    this.running = false;
    this.clearTimers();
    const socket = this.socket;
    this.socket = null;
    this.ready = false;
    if (socket) {
      socket.onclose = null;
      socket.onmessage = null;
      try {
        socket.close(1000, "client stopped");
      } catch {
        /* already closed */
      }
    }
    this.lastEventId = 0;
    this.revisions.clear();
    this.fallbackActive = false;
    this.setStatus("idle");
  }

  /** Receive events for one topic ("jobs", "job:<id>", "corpus-builds", "corpus-build:<id>"). */
  subscribe(topic: string, handler: EventHandler): () => void {
    let set = this.handlers.get(topic);
    const isNew = !set;
    if (!set) {
      set = new Set();
      this.handlers.set(topic, set);
    }
    set.add(handler);
    if (isNew) this.send({ type: "subscribe", topics: [topic] });
    return () => {
      const current = this.handlers.get(topic);
      if (!current) return;
      current.delete(handler);
      if (!current.size) {
        this.handlers.delete(topic);
        this.send({ type: "unsubscribe", topics: [topic] });
      }
    };
  }

  /** Called whenever authoritative state must be re-read (reconnect gap, overflow, recovery). */
  onResync(handler: ResyncHandler): () => void {
    this.resyncHandlers.add(handler);
    return () => this.resyncHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    handler(this.status, this.fallbackActive);
    return () => this.statusHandlers.delete(handler);
  }

  /** Whether live events currently replace polling. */
  get live(): boolean {
    return this.status === "connected" || this.status === "degraded";
  }

  // -- connection lifecycle --------------------------------------------------------------------
  private connect(status: RealtimeStatus): void {
    if (!this.running) return;
    this.setStatus(status);
    let socket: SocketLike;
    try {
      socket = this.options.createSocket(this.options.url());
    } catch {
      this.onFailedAttempt();
      return;
    }
    this.socket = socket;
    this.ready = false;
    socket.onmessage = (event) => this.onFrame(event.data);
    socket.onclose = (event) => this.onClose(event.code, event.reason || "");
    socket.onerror = () => {
      /* onclose follows */
    };
  }

  private onClose(code: number, reason: string): void {
    const wasReady = this.ready;
    this.socket = null;
    this.ready = false;
    this.clearTimers();
    if (!this.running) return;
    if (code === CLOSE_CODES.unauthenticated) {
      // Never keep reconnecting with an expired cookie.
      this.running = false;
      this.setStatus("offline");
      this.options.onAuthExpired?.();
      return;
    }
    if (code === CLOSE_CODES.forbidden) {
      if (reason === "permissions changed") this.options.onPermissionsChanged?.();
      else {
        // Realtime is disabled, refused by origin policy, or unavailable to this role.
        this.fallbackActive = true;
        this.attempt = Math.max(this.attempt, 16);
      }
    }
    if (!wasReady) this.onFailedAttempt();
    else this.scheduleReconnect();
  }

  private onFailedAttempt(): void {
    this.failures += 1;
    if (this.failures >= this.options.fallbackAfterFailures) this.fallbackActive = true;
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (!this.running) return;
    this.setStatus(this.fallbackActive ? "offline" : "reconnecting");
    const exponential = this.options.baseBackoffMs * 2 ** Math.min(this.attempt, 16);
    const capped = Math.min(this.options.maxBackoffMs, exponential);
    const delay = Math.round(capped * (0.5 + this.options.random() * 0.5));
    this.attempt += 1;
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => this.connect(this.status), delay);
  }

  private clearTimers(): void {
    clearTimeout(this.reconnectTimer);
    clearInterval(this.pingTimer);
    clearTimeout(this.stableTimer);
    this.reconnectTimer = undefined;
    this.pingTimer = undefined;
    this.stableTimer = undefined;
  }

  private send(message: ClientMessage): void {
    if (!this.ready || !this.socket || this.socket.readyState !== OPEN) return;
    this.socket.send(JSON.stringify(message));
  }

  private setStatus(status: RealtimeStatus): void {
    this.status = status;
    for (const handler of this.statusHandlers) handler(status, this.fallbackActive);
  }

  private resync(reason: string): void {
    for (const handler of this.resyncHandlers) handler(reason);
  }

  // -- frames ----------------------------------------------------------------------------------
  private onFrame(data: unknown): void {
    let frame: ServerFrame;
    try {
      frame = JSON.parse(String(data)) as ServerFrame;
    } catch {
      return;
    }
    this.lastFrameAt = Date.now();
    if (this.status === "degraded") this.setStatus("connected");
    if (isResourceEvent(frame)) {
      this.deliver(frame);
      return;
    }
    switch (frame.type) {
      case "connection.ready":
        this.onReady(frame.payload);
        break;
      case "connection.resync_required":
        this.revisions.clear();
        this.lastEventId = Math.max(this.lastEventId, frame.payload.last_event_id || 0);
        this.resync(frame.payload.reason || "resync_required");
        break;
      case "auth.permissions_changed":
        this.options.onPermissionsChanged?.();
        break;
      default:
        break;
    }
  }

  private onReady(payload: { last_event_id: number; heartbeat_seconds: number }): void {
    const recovering = this.fallbackActive;
    const serverRestarted = payload.last_event_id < this.lastEventId;
    const resumeFrom = this.lastEventId;
    this.ready = true;
    this.failures = 0;
    this.fallbackActive = false;
    this.heartbeatMs = Math.max(1000, Number(payload.heartbeat_seconds || 20) * 1000);
    this.setStatus("connected");
    this.stableTimer = setTimeout(() => {
      this.attempt = 0;
    }, this.options.stableAfterMs);
    this.lastFrameAt = Date.now();
    this.pingTimer = setInterval(() => this.checkHealth(), Math.round(this.heartbeatMs * 0.75));

    const topics = [...this.handlers.keys()];
    if (serverRestarted || resumeFrom === 0) {
      // No replay is possible (fresh session or new server process): start from REST truth.
      this.revisions.clear();
      this.lastEventId = payload.last_event_id;
      if (topics.length) this.send({ type: "subscribe", topics });
      this.resync(serverRestarted ? "server_restarted" : recovering ? "recovered" : "connected");
      return;
    }
    // Resume: the server replays what we missed, or answers connection.resync_required.
    if (topics.length) this.send({ type: "subscribe", topics, last_event_id: resumeFrom });
    if (recovering) this.resync("recovered");
  }

  private checkHealth(): void {
    if (!this.socket) return;
    this.send({ type: "ping" });
    const silentFor = Date.now() - this.lastFrameAt;
    if (silentFor > this.heartbeatMs * 2.5) {
      // A half-open socket: give up on it and reconnect with backoff.
      try {
        this.socket.close(4000, "heartbeat timeout");
      } catch {
        /* ignore */
      }
      this.onClose(4000, "heartbeat timeout");
    } else if (silentFor > this.heartbeatMs * 1.5 && this.status === "connected") {
      this.setStatus("degraded");
    }
  }

  private deliver(event: RealtimeEvent): void {
    // Duplicate (replayed or re-sent) and stale lower-revision events are ignored.
    if (event.event_id <= this.lastEventId) return;
    this.lastEventId = event.event_id;
    const key = `${event.resource_type}:${event.resource_id}`;
    const known = this.revisions.get(key) ?? 0;
    if (event.revision <= known) return;
    this.revisions.set(key, event.revision);
    const seen = new Set<EventHandler>();
    for (const topic of topicsForEvent(event)) {
      for (const handler of this.handlers.get(topic) ?? []) {
        if (seen.has(handler)) continue;
        seen.add(handler);
        try {
          handler(event);
        } catch (error) {
          console.warn("Realtime handler failed", error);
        }
      }
    }
  }
}
