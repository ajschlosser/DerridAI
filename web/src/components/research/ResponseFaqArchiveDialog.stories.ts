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
import ResponseFaqArchiveDialog from "./ResponseFaqArchiveDialog.vue";

const records = [
  {
    record_id: "cache-1",
    question: "What is responsibility after deconstruction?",
    provider: "Ollama",
    model: "qwen3:14b",
    created_at: "2026-09-14T18:30:00Z",
    evidence_count: 8,
    grade: { overall: 9 },
  },
  {
    record_id: "cache-2",
    question: "How does hospitality complicate sovereignty?",
    provider: "OpenAI-compatible",
    model: "gpt-oss:20b",
    created_at: "2026-09-14T16:10:00Z",
    evidence_count: 11,
  },
  {
    record_id: "cache-3",
    question: "Trace the role of undecidability in decision.",
    provider: "Ollama",
    model: "phi4:14b",
    created_at: "2026-09-13T22:15:00Z",
    evidence_count: 6,
    grade: { overall: 8 },
  },
];
const meta = {
  title: "Research/Response Library/Archive Dialog",
  component: ResponseFaqArchiveDialog,
  args: {
    open: true,
    records,
    selectedId: "cache-1",
    search: "",
    loading: false,
    count: 3,
    total: 42,
    page: 1,
    pages: 2,
  },
} satisfies Meta<typeof ResponseFaqArchiveDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Searching: Story = {
  args: { search: "hospitality", count: 1, records: [records[1]], selectedId: "cache-2" },
};
export const NoMatches: Story = { args: { search: "khôra and telepathy", count: 0, records: [] } };
export const InitialRead: Story = { args: { loading: true, ready: false, records: [] } };
export const Refreshing: Story = { args: { loading: true } };
export const FailedRead: Story = {
  args: { ready: false, records: [], error: "Service unavailable" },
};
export const FailedRefresh: Story = { args: { error: "Service unavailable" } };
