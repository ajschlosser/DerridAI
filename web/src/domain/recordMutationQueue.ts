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

export interface RecordMutationContext {
  rebase: boolean;
  attempt: number;
}

export type RecordMutation = (context: RecordMutationContext) => Promise<unknown>;

/**
 * Serializes mutations by logical record identity. Review saves carry an
 * expected revision, so concurrent requests for one record must not overtake
 * one another; unrelated records remain fully independent.
 */
export class RecordMutationQueue {
  private readonly pending = new Map<string, Promise<void>>();
  private readonly queued = new Map<string, number>();

  enqueue(
    recordIds: string | readonly string[],
    mutation: RecordMutation,
    onError: (error: unknown) => void,
    options: { retryOnFailure?: boolean } = {},
  ): void {
    const keys = Array.from(new Set(typeof recordIds === "string" ? [recordIds] : recordIds));
    if (!keys.length) return;
    // A later mutation for the same record must rebase even when the earlier
    // mutation succeeds. Its caller captured an older optimistic revision before
    // the preceding request reached the server.
    keys.forEach((recordId) => this.queued.set(recordId, (this.queued.get(recordId) || 0) + 1));
    const hadPending = keys.some((recordId) => this.pending.has(recordId));
    const previous = Promise.all(
      keys.map((recordId) => this.pending.get(recordId) || Promise.resolve()),
    );
    const settle = () =>
      keys.forEach((recordId) => {
        const left = (this.queued.get(recordId) || 1) - 1;
        if (left > 0) this.queued.set(recordId, left);
        else this.queued.delete(recordId);
      });
    const current = previous
      .catch(() => undefined)
      .then(async () => {
        const rebase = hadPending || keys.some((recordId) => this.rebaseRequired.has(recordId));
        try {
          await mutation({ rebase, attempt: 1 });
          keys.forEach((recordId) => this.rebaseRequired.delete(recordId));
        } catch (error) {
          if (options.retryOnFailure) {
            try {
              await mutation({ rebase: true, attempt: 2 });
              keys.forEach((recordId) => this.rebaseRequired.delete(recordId));
              return;
            } catch (retryError) {
              keys.forEach((recordId) => this.rebaseRequired.add(recordId));
              onError(retryError);
              return;
            }
          }
          keys.forEach((recordId) => this.rebaseRequired.add(recordId));
          onError(error);
        }
      });
    keys.forEach((recordId) => this.pending.set(recordId, current));
    void current.finally(() => {
      settle();
      keys.forEach((recordId) => {
        if (this.pending.get(recordId) === current) this.pending.delete(recordId);
      });
    });
  }

  private readonly rebaseRequired = new Set<string>();

  async waitFor(recordIds: string | readonly string[]): Promise<void> {
    const keys = Array.from(new Set(typeof recordIds === "string" ? [recordIds] : recordIds));
    while (true) {
      const waits = keys
        .map((recordId) => this.pending.get(recordId))
        .filter((pending): pending is Promise<void> => Boolean(pending));
      if (!waits.length) return;
      await Promise.all(waits.map((pending) => pending.catch(() => undefined)));
      // Let the finally handlers remove completed entries before checking again.
      await Promise.resolve();
    }
  }

  /** True when a mutation for this record is queued behind the one currently running. */
  hasQueuedBehind(recordId: string): boolean {
    return (this.queued.get(recordId) || 0) > 1;
  }

  hasPending(recordId: string): boolean {
    return this.pending.has(recordId);
  }
}
