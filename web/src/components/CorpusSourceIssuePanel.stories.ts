import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSourceIssuePanel from "./CorpusSourceIssuePanel.vue";

const meta: Meta<typeof CorpusSourceIssuePanel> = {
  title: "Corpus Builder/Review/Source Issue Panel",
  component: CorpusSourceIssuePanel,
};

export default meta;
type Story = StoryObj<typeof CorpusSourceIssuePanel>;

export const Fragmented: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "fragmented_glyph_layout",
        severity: "blocking",
        pages: [1, 2],
        micro_line_ratio: 0.63,
        message: "Extracted text appears fragmented into individual glyphs or punctuation lines.",
      },
    ],
  },
};

export const FrenchLength: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "source_quality_blocking",
        severity: "blocking",
        pages: [14],
        message:
          "La couche de texte du document contient des caractères de remplacement ou de contrôle et doit être vérifiée avant l’acceptation savante.",
      },
    ],
  },
};

export const NonPaginatedSource: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "source_quality_warning",
        severity: "warning",
        message:
          "The extracted transcript contains a low-confidence region that should be checked against the source.",
      },
    ],
  },
};

export const Resolved: Story = {
  args: {
    resolved: true,
    interactive: true,
    issues: [
      {
        code: "fragmented_glyph_layout",
        severity: "blocking",
        pages: [1, 2],
        message: "The extracted text was corrected during review.",
      },
    ],
  },
};

export const IllegibleText: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "illegible_text",
        severity: "blocking",
        pages: [24],
        noise: 66,
        message: "Extracted text does not look like words in a writing system.",
      },
    ],
  },
};

export const PixelatedScan: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "low_raster_quality",
        severity: "blocking",
        pages: [8],
        message: "Embedded page image resolution is too low to trust as a scholarly scan.",
      },
    ],
  },
};

export const IllegibleAndPixelated: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "illegible_text",
        severity: "blocking",
        pages: [8, 9],
        noise: 72,
        message: "Extracted text does not look like words in a writing system.",
      },
      {
        code: "low_raster_quality",
        severity: "blocking",
        pages: [8, 9],
        message: "Embedded page image resolution is too low to trust as a scholarly scan.",
      },
    ],
  },
};

export const NarrowActions: Story = {
  args: {
    interactive: true,
    issues: [
      {
        code: "source_quality_warning",
        severity: "warning",
        message:
          "Review this source region before publication because the extraction confidence is incomplete.",
      },
    ],
  },
  decorators: [
    () => ({
      template: '<div style="max-width: 320px"><story /></div>',
    }),
  ],
};
