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

// A small reactive GraphQL read: re-executes when its variables change, skips entirely while
// variables are null, and — via createLatestRequest — never lets a slower, superseded response
// overwrite a newer one already applied.
import { type Ref, ref, watchEffect } from "vue";
import { execute } from "./client";
import type { TypedDocumentString } from "./generated";
import { createLatestRequest } from "./latestRequest";

export interface UseQueryOptions<TVariables> {
  /** Reactive variables; returning null skips the query (no request in flight). */
  variables: () => TVariables | null;
}

export interface UseQueryResult<TResult> {
  data: Ref<TResult | null>;
  loading: Ref<boolean>;
  error: Ref<Error | null>;
}

export function useQuery<TResult, TVariables>(
  document: TypedDocumentString<TResult, TVariables>,
  options: UseQueryOptions<TVariables>,
): UseQueryResult<TResult> {
  const data = ref<TResult | null>(null) as Ref<TResult | null>;
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const latest = createLatestRequest();

  watchEffect(async () => {
    const variables = options.variables();
    if (variables == null) {
      latest.cancel();
      return;
    }
    const ticket = latest.start();
    loading.value = true;
    try {
      const result = await execute(document, variables, { signal: ticket.signal });
      if (!ticket.current()) return;
      data.value = result;
      error.value = null;
    } catch (cause) {
      if (!ticket.current()) return;
      error.value = cause instanceof Error ? cause : new Error(String(cause));
      data.value = null;
    } finally {
      if (ticket.current()) loading.value = false;
    }
  });

  return { data, loading, error };
}
