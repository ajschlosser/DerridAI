/* Copyright 2026 Aaron John Schlosser, PhD. */
// Race safety for GraphQL reads: when the reviewer moves on before a slow response lands, that
// response must never overwrite what is now shown. Each `start()` aborts the previous in-flight
// request and mints a ticket; only the ticket from the most recent `start()` reports `current()`
// as true, so a superseded response can be dropped instead of applied.
export interface LatestRequestTicket {
  /** Pass to `execute(..., { signal })` so a superseded request is aborted, not just ignored. */
  signal: AbortSignal;
  /** True only for the ticket from the most recent `start()`; a stale response should not apply itself. */
  current(): boolean;
}

export interface LatestRequest {
  start(): LatestRequestTicket;
  /** Abort whatever is in flight without starting a new one (call on unmount). */
  cancel(): void;
}

export function createLatestRequest(): LatestRequest {
  let ticketNumber = 0;
  let controller: AbortController | null = null;

  function start(): LatestRequestTicket {
    controller?.abort();
    const mine = ++ticketNumber;
    controller = new AbortController();
    return {
      signal: controller.signal,
      current: () => mine === ticketNumber,
    };
  }

  function cancel() {
    ticketNumber += 1;
    controller?.abort();
    controller = null;
  }

  return { start, cancel };
}
