import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DocumentManifestEditor from "../DocumentManifestEditor.vue";

const meta = {
  title: "Corpus Builder/Setup/Early Manifest",
  component: DocumentManifestEditor,
  args: {
    mediaKind: "text",
    showReanalyze: false,
    manifest: {
      title: "Of Grammatology",
      document_author: "Jacques Derrida",
      translator: "Gayatri Chakravorty Spivak",
      publication_year: 1976,
      language: "en",
      original_language: "fr",
      document_is_translation: true,
      deterministic_ingest: {
        applied: {
          title: {
            value: "Of Grammatology",
            derivation: "computed",
            method: "title_page",
            confidence: 0.99,
          },
          document_author: {
            value: "Jacques Derrida",
            derivation: "nlp_derived",
            method: "title_page_entities",
            confidence: 0.96,
          },
        },
      },
    },
  },
} satisfies Meta<typeof DocumentManifestEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const EditableBeforeBuild: Story = {};
