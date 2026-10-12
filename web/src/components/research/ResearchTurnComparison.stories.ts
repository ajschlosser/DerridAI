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
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { QueryClient, VUE_QUERY_CLIENT } from "@tanstack/vue-query";
import { provide } from "vue";
import { useAuthStore } from "../../stores/auth";
import type { ResearchTurn } from "../../types/researchThreads";
import ResearchTurnComparison from "./ResearchTurnComparison.vue";

const turn = (ordinal: number, question: string): ResearchTurn => ({
  turn_id: `turn-${ordinal}`,
  thread_id: "rt_story",
  ordinal,
  user_question: question,
  user_instructions: null,
  status: "completed",
  job_id: `run-${ordinal}`,
  research_run_id: `run-${ordinal}`,
  response_record_id: null,
  parent_turn_id: null,
  contextualized_query: null,
  context_selection: null,
  error: null,
  attempt: 1,
  created_at: "2026-10-12T00:00:00Z",
  updated_at: "2026-10-12T00:00:00Z",
});
const turns = [turn(1, "What is différance?"), turn(2, "How does it relate to the trace?")];
const evidence = (revision: number) => [
  {
    evidence_id: "E1",
    collection: "corpus",
    inline_citation: "Author 1972: 3",
    record: { record_id: "r1", work: "Example Work", record_revision: revision },
  },
];
const results = [
  { answer: "It is neither a word nor a concept (Author 1972: 3).", evidence: evidence(2) },
  { answer: "The trace names what différance leaves (Author 1972: 3).", evidence: evidence(3) },
];

// Seeds the per-turn result cache under the story user so no request is made.
const withSeededResults = (story: () => unknown) => ({
  components: { story },
  setup() {
    const auth = useAuthStore();
    auth.user = {
      id: 1,
      username: "story",
      role: "researcher",
      capabilities: ["rag.run"],
    } as never;
    const client = new QueryClient();
    turns.forEach((item, index) =>
      client.setQueryData(
        [
          "research-turn-result",
          1,
          "researcher",
          item.thread_id,
          item.turn_id,
          item.attempt,
          item.job_id,
          item.response_record_id,
        ],
        {
          id: item.research_run_id,
          status: "completed",
          result: { provider: "ollama", model: "example-model", ...results[index] },
        },
      ),
    );
    provide(VUE_QUERY_CLIENT, client);
    return {};
  },
  template: "<story />",
});

const meta: Meta<typeof ResearchTurnComparison> = {
  title: "Research/Turn Comparison",
  component: ResearchTurnComparison,
  parameters: { layout: "padded" },
  decorators: [withSeededResults],
};
export default meta;
type Story = StoryObj<typeof ResearchTurnComparison>;

/** The shared Record is cited at different revisions, which the table flags. */
export const RevisionMismatch: Story = { args: { turns } };
