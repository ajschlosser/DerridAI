import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSetupDocumentMetadata from "./CorpusSetupDocumentMetadata.vue";

const meta = {
  title: "Corpus Builder/Setup/Early Manifest",
  component: CorpusSetupDocumentMetadata,
  args: {
    mediaKind: "text",
    missingRequiredCount: 0,
    reviewerOverrideCount: 0,
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
