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
import ResearchThreadNavigation from "./ResearchThreadNavigation.vue";
import type { ResearchThreadDetail, ResearchThreadSummary } from "../../types/researchThreads";

const thread: ResearchThreadDetail = {
  thread_id: "thread-a",
  owner: "researcher",
  title: "Responsibility and the other",
  created_at: "2026-10-05T00:00:00Z",
  updated_at: "2026-10-05T00:00:00Z",
  archived_at: null,
  originating_response_record_id: null,
  turns: ["How does Derrida understand responsibility?", "What about Levinas?"].map(
    (question, index) => ({
      turn_id: `turn-${index}`,
      thread_id: "thread-a",
      ordinal: index + 1,
      user_question: question,
      user_instructions: null,
      status: index ? "failed" : "completed",
      job_id: index ? null : "job-a",
      research_run_id: null,
      response_record_id: null,
      parent_turn_id: index ? "turn-0" : null,
      contextualized_query: null,
      context_selection: null,
      error: index ? "Provider unavailable" : null,
      attempt: 1,
      created_at: "2026-10-05T00:00:00Z",
      updated_at: "2026-10-05T00:00:00Z",
    }),
  ),
};
const summary: ResearchThreadSummary = {
  ...thread,
  turn_count: 2,
  first_question: thread.turns[0].user_question,
  last_question: thread.turns[1].user_question,
  last_status: "failed",
};
const meta: Meta<typeof ResearchThreadNavigation> = {
  title: "Research/Thread Navigation",
  component: ResearchThreadNavigation,
  args: {
    threads: [summary],
    thread,
    selectedThreadId: thread.thread_id,
    selectedJobId: "job-a",
    offset: 0,
  },
};
export default meta;
type Story = StoryObj<typeof ResearchThreadNavigation>;
export const OrderedTurns: Story = {};
export const Empty: Story = { args: { threads: [], thread: null, selectedThreadId: "" } };
export const RefreshFailure: Story = { args: { error: "Thread refresh unavailable" } };
export const Narrow: Story = { parameters: { viewport: { defaultViewport: "mobile1" } } };

export const Archived: Story = {
  args: {
    includeArchived: true,
    thread: { ...thread, archived_at: "2026-10-05" },
    threads: [{ ...summary, archived_at: "2026-10-05" }],
  },
};

export const RetryPending: Story = { args: { retryDisabled: true } };

export const Library: Story = {
  args: { thread: null, selectedThreadId: "", showPreview: true, search: "responsibility" },
};

/**
 * Exercises the navigation/conversation split with a long question and enough
 * history to reveal horizontal overflow or an excessively tall thread rail.
 */
export const LongConversation: Story = {
  args: {
    threads: Array.from({ length: 30 }, (_, index) => ({
      ...summary,
      thread_id: `thread-${index}`,
      title: `Research inquiry ${index + 1}`,
    })),
    thread: {
      ...thread,
      turns: Array.from({ length: 12 }, (_, index) => ({
        ...thread.turns[0],
        turn_id: `turn-long-${index}`,
        ordinal: index + 1,
        user_question:
          index === 0
            ? "How does responsibility to the other resist being reduced to a decision procedure, and what does that mean for Derrida's interpretation of Levinas?"
            : `Follow-up question ${index + 1}: explain the relevant distinction.`,
      })),
    },
  },
};
export const WideDesktop: Story = {
  parameters: { viewport: { defaultViewport: "responsive" } },
};
