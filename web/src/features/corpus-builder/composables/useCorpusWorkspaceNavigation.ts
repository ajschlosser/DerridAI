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

import { computed, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { CorpusBuild } from "../../../api/corpus";
import {
  isWorkspaceAvailable,
  parseCorpusWorkspace,
  resolveWorkspace,
  type CorpusWorkspace,
} from "../domain/workspace";

interface CorpusWorkspaceNavigationOptions {
  currentBuild: Ref<CorpusBuild | null>;
  hasRecordTopology: Readonly<Ref<boolean>>;
  /** Records are ready for people: the default landing workspace for an existing build. */
  reviewReady: Readonly<Ref<boolean>>;
}

/**
 * Top-level workspace routing (`?workspace=`): parsing, availability, fallback and query
 * synchronisation. Record and queue navigation stay with the review-navigation composables.
 */
export function useCorpusWorkspaceNavigation(options: CorpusWorkspaceNavigationOptions) {
  const route = useRoute();
  const router = useRouter();

  const context = computed(() => ({
    hasBuild: Boolean(options.currentBuild.value),
    hasRecordTopology: options.hasRecordTopology.value,
  }));
  const requestedWorkspace = computed(() => parseCorpusWorkspace(route.query.workspace));
  const defaultWorkspace = computed<CorpusWorkspace>(() => {
    if (!options.currentBuild.value) return "setup";
    return options.hasRecordTopology.value && options.reviewReady.value ? "review" : "build";
  });
  const workspaceMode = computed<CorpusWorkspace>(() =>
    resolveWorkspace(requestedWorkspace.value, context.value, defaultWorkspace.value),
  );

  async function switchWorkspace(
    workspace: CorpusWorkspace,
    navigation: "push" | "replace" = "push",
  ) {
    if (!isWorkspaceAvailable(workspace, context.value)) return;
    const review = workspace === "review";
    const location = {
      query: {
        ...route.query,
        workspace,
        build: options.currentBuild.value?.build_id || route.query.build,
        record: review ? route.query.record : undefined,
        queue: review ? route.query.queue : undefined,
      },
    };
    if (navigation === "replace") await router.replace(location);
    else await router.push(location);
  }

  return { requestedWorkspace, workspaceMode, defaultWorkspace, switchWorkspace };
}
