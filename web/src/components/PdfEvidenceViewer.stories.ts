import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";

const meta: Meta<typeof PdfEvidenceViewer> = {
  title: "Corpus Builder/Source/PDF Evidence Viewer",
  component: PdfEvidenceViewer,
  args: { pdfUrl: "", page: 1, pageWidth: 612, pageHeight: 792, blocks: [], evidenceBlockIds: [] },
};
export default meta;
type Story = StoryObj<typeof PdfEvidenceViewer>;
export const Empty: Story = {};
export const EvidenceGeometry: Story = {
  args: {
    blocks: [
      {
        block_id: "p00001-b0001",
        page: 1,
        bbox: [72, 96, 540, 160],
        type: "paragraph",
        text: "Source block",
        extraction_method: "native",
        confidence: 1,
      },
    ],
    evidenceBlockIds: ["p00001-b0001"],
  },
};
