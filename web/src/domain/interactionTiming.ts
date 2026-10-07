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

/**
 * Records a bounded interaction-to-next-frame User Timing measure.
 * Only one measurement per name can be pending and only the latest
 * completed measure is retained.
 */
const pending = new Set<string>();

export function measureInteractionToNextFrame(name: string): void {
  const perf = globalThis.performance;
  if (
    !name ||
    !perf ||
    typeof perf.mark !== "function" ||
    typeof perf.measure !== "function" ||
    typeof perf.clearMarks !== "function" ||
    typeof perf.clearMeasures !== "function"
  )
    return;
  if (pending.has(name)) return;

  const startMark = `${name}:start`;
  const endMark = `${name}:frame`;
  pending.add(name);
  perf.clearMarks(startMark);
  perf.clearMarks(endMark);
  perf.mark(startMark);

  const finish = () => {
    try {
      perf.mark(endMark);
      perf.clearMeasures(name);
      perf.measure(name, startMark, endMark);
    } finally {
      perf.clearMarks(startMark);
      perf.clearMarks(endMark);
      pending.delete(name);
    }
  };

  if (typeof globalThis.requestAnimationFrame === "function")
    globalThis.requestAnimationFrame(finish);
  else globalThis.setTimeout(finish, 0);
}


/**
 * Runs non-visual follow-up work only after the browser has had an opportunity
 * to paint the state produced by the current interaction.
 */
export function runAfterNextPaint(task: () => void): void {
  if (typeof globalThis.requestAnimationFrame !== "function") {
    globalThis.setTimeout(task, 0);
    return;
  }
  globalThis.requestAnimationFrame(() => {
    globalThis.requestAnimationFrame(task);
  });
}
