import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordPdfLinks from "./RecordPdfLinks.vue";
const meta = {
  title: "Record Workspace/PDF Links",
  component: RecordPdfLinks,
  args: {
    links: [
      { pdf_file: "adieu.pdf", pdf_page: 33 },
      { pdf_file: "adieu.pdf", pdf_page: 34 },
    ],
    canManage: true,
    canOpen: true,
    pdfLoaded: true,
    currentPdf: "adieu.pdf",
  },
} satisfies Meta<typeof RecordPdfLinks>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
