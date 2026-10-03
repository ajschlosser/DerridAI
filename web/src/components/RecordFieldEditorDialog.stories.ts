// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordFieldEditorDialog from "./RecordFieldEditorDialog.vue";
import { openRecordFieldEditorDialog } from "../composables/recordFieldEditorDialog";

const meta = {
  title: "Records/Record Field Editor Dialog",
  component: RecordFieldEditorDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { RecordFieldEditorDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><RecordFieldEditorDialog /></div>`,
    methods: {
      open() {
        openRecordFieldEditorDialog({
          title: "Edit record",
          subtitle: "rec-0001 · Of Grammatology",
          help: "",
          footerNote: "Changes stay local until you export or upsert them.",
          saveLabel: "Save changes",
          parseErrorTitle: "Could not save",
          sections: [
            {
              title: "Source",
              fields: [
                {
                  key: "work",
                  label: "Work",
                  kind: "string",
                  value: "Of Grammatology",
                  full: false,
                },
                { key: "year", label: "Year", kind: "number", value: 1967, full: false },
                {
                  key: "needs_review",
                  label: "Needs review",
                  kind: "boolean",
                  value: true,
                  full: false,
                },
              ],
            },
            {
              title: "Indexing",
              fields: [
                {
                  key: "concepts",
                  label: "Concepts",
                  kind: "json",
                  value: ["trace", "supplement"],
                  full: false,
                },
                {
                  key: "text",
                  label: "Text",
                  kind: "text",
                  value: "There is nothing outside the text.",
                  full: true,
                },
              ],
            },
          ],
          save: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof RecordFieldEditorDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const LocalRecord: Story = {};
