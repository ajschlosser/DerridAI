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
import AnnotationFeedItem from "./AnnotationFeedItem.vue";

const meta = {
  title: "Annotations/Annotation feed item",
  component: AnnotationFeedItem,
  args: {
    annotation: {
      id: "annotation-1",
      record_id: "record-12",
      work: "Writing and Difference",
      field: "text",
      quote: "A trace is not a presence.",
      note: "Review the distinction between trace and origin.",
      tags: ["trace", "provenance"],
      author: "researcher",
      source: "corpus.jsonl",
      created_at: "2026-09-14T20:30:00Z",
      server: false,
      removable: true,
      local_file_id: "file-1",
      local_index: 12,
      local_annotation_index: 0,
      shared_annotation_id: null,
    },
  },
} satisfies Meta<typeof AnnotationFeedItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Shared: Story = {
  args: {
    annotation: {
      ...meta.args.annotation,
      server: true,
      removable: false,
      source: "Corpus database",
    },
  },
};
