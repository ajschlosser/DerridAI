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

// Pausing the job transports (fallback polling, resync timer, realtime socket) on logout, session expiry and account
// switches. The jobs workspace owns those timers, so it registers its pause here; Vue code imports `pauseRuntime`
// without reaching into the legacy runtime. With nothing registered yet only the realtime socket needs closing.
import { realtime } from "../realtime";

let registered: (() => void) | null = null;

/** Called by the jobs workspace with the function that stops its timers and realtime client. */
export function registerJobsPause(pause: (() => void) | null) {
  registered = pause;
}

export function pauseRuntime() {
  if (registered) registered();
  else realtime.stop();
}
