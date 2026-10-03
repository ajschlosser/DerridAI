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
