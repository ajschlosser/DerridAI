// Copyright 2026 Aaron John Schlosser, PhD.
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
