/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordsFileRail from "./RecordsFileRail.vue";
import type { RecordsFileTab } from "../../domain/recordsFiles";

const files: RecordsFileTab[] = [
  {
    id: "jsonl-abc",
    name: "glas.jsonl",
    count: 412,
    dirty: 0,
    active: true,
    origin: "imported",
    origin_detail: "",
  },
  {
    id: "subset-1",
    name: "glas-primary-subset.jsonl",
    count: 206,
    dirty: 3,
    active: false,
    origin: "subset",
    origin_detail: "glas.jsonl",
  },
  {
    id: "chroma-1",
    name: "derrida-primary.jsonl",
    count: 12840,
    dirty: 0,
    active: false,
    origin: "chroma",
    origin_detail: "derrida-primary",
  },
];

const meta = {
  title: "Records/File Rail",
  component: RecordsFileRail,
  args: {files, canManage: true},
} satisfies Meta<typeof RecordsFileRail>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Populated: Story = {};
export const EditedSubset: Story = {
  args: {files: files.map((file) => (file.origin === "subset" ? {...file, active: true} : {...file, active: false}))},
};
export const SingleImported: Story = {
  args: {files: [files[0]]},
};
