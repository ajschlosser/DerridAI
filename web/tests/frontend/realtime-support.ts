/* Copyright 2026 Aaron John Schlosser, PhD. */
// A scriptable WebSocket stand-in for realtime client tests.
import type { SocketLike } from "../../src/realtime/client";

export class MockSocket implements SocketLike {
  static instances: MockSocket[] = [];
  readyState = 0;
  sent: Array<Record<string, unknown>> = [];
  closedWith: number | null = null;
  onopen: ((event: unknown) => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  onclose: ((event: { code: number; reason?: string }) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  constructor(public url: string) {
    MockSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(JSON.parse(data));
  }
  close(code = 1000) {
    this.closedWith = code;
    this.readyState = 3;
  }
  /** Server accepted and sent connection.ready. */
  ready(lastEventId = 0, heartbeatSeconds = 20) {
    this.readyState = 1;
    this.frame({
      type: "connection.ready",
      payload: {
        protocol_version: 1,
        connection_id: "c1",
        last_event_id: lastEventId,
        heartbeat_seconds: heartbeatSeconds,
        idle_timeout_seconds: 60,
      },
    });
  }
  frame(payload: Record<string, unknown>) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
  serverClose(code: number, reason = "") {
    this.readyState = 3;
    this.onclose?.({ code, reason });
  }
}

export function jobEvent(
  eventId: number,
  revision: number,
  job: Record<string, unknown>,
  type = "job.progress",
) {
  return {
    type,
    event_id: eventId,
    resource_type: "job",
    resource_id: String(job.id),
    revision,
    timestamp: "2026-09-27T00:00:00Z",
    payload: { job },
  };
}
