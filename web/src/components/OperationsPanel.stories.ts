import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { defineComponent, h } from "vue";
import OperationsPanel from "./OperationsPanel.vue";
import { useI18nStore } from "../stores/i18n";
import type { OperationView, OperationsBridge } from "../domain/operationsPanel";

const iso = (seconds: number) => new Date(Date.now() + seconds * 1000).toISOString();
const base: OperationView = {
  id: "x", type: "llm_tool", status: "completed", label: "Languages · Français", icon: "language", subtitle: "", facts: [{ name: "Provider", value: "ollama" }, { name: "Model", value: "gemma4:e2b" }],
  owner: "admin", createdAt: iso(-700), startedAt: iso(-600), finishedAt: iso(-300), total: 1, completed: 1, progressLabel: "1 of 1 (100%)", cancelRequested: false, error: "", result: { kind: "result" },
};
const op = (over: Partial<OperationView>): OperationView => ({ ...base, ...over });

function bridgeFor(jobs: OperationView[]): OperationsBridge {
  return {
    snapshot: () => jobs.map((job) => ({ ...job })),
    subscribe: () => () => {},
    refresh: async () => {},
    openDetails: () => {},
    openResult: () => {},
    cancel: async () => {},
    remove: async () => {},
    clearFinished: async () => {},
  };
}

const mixed = [
  op({ id: "b", type: "pdf_corpus", icon: "pdf", label: "PDF corpus build", status: "running", subtitle: "Derrida_ Jacques - On Cosmopolitanism and Forgiveness.pdf · Metadata: 54/180 settled", finishedAt: null, result: null, total: 307, completed: 92, progressLabel: "30% overall", facts: [{ name: "records", value: "60" }, { name: "need review", value: "21" }] }),
  op({ id: "u", type: "upsert", icon: "database", label: "Chroma upsert", status: "queued", subtitle: "derrida-primary · 0/400 committed", startedAt: null, finishedAt: null, result: null, total: 400, completed: 0, progressLabel: "0/400" }),
  op({ id: "f", label: "Languages · Français", status: "failed", result: null, error: "Provider unreachable: connection refused (http://host.docker.internal:11434)", startedAt: iso(-3690), finishedAt: iso(-3600) }),
  op({ id: "r", type: "llm", icon: "edit", label: "LLM review", status: "completed", result: { kind: "review" }, subtitle: "10/10 records", finishedAt: iso(-7000), startedAt: iso(-7290) }),
  op({ id: "o1", label: "Languages · English", finishedAt: iso(-90000), startedAt: iso(-90050) }),
  op({ id: "o2", type: "rag", icon: "spark", label: "RAG pipeline", subtitle: "complete", finishedAt: iso(-94900), startedAt: iso(-95000) }),
  op({ id: "c", type: "upsert", icon: "database", label: "Chroma upsert", status: "cancelled", result: null, finishedAt: iso(-199000), startedAt: iso(-200000) }),
];

const meta = {
  title: "Operations/Panel",
  component: OperationsPanel,
  args: { bridge: bridgeFor(mixed) },
  parameters: { layout: "padded" },
  // The i18n store is shared by every story; set its locale explicitly so one story cannot leak into the next.
  decorators: [
    (story, context) => defineComponent({
      setup() {
        useI18nStore().locale = String(context.parameters.locale || "en-US");
        return () => h(story());
      },
    }),
  ],
} satisfies Meta<typeof OperationsPanel>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Mixed: Story = {};
export const Empty: Story = { args: { bridge: bridgeFor([]) } };
export const ManyRunning: Story = {
  args: {
    bridge: bridgeFor(Array.from({ length: 5 }, (_, i) => op({ id: `r${i}`, type: "llm", icon: "edit", label: `Auto-improve ${i + 1}`, status: i === 4 ? "queued" : "running", finishedAt: null, startedAt: i === 4 ? null : iso(-120 - i * 40), result: { kind: "review-partial" }, total: 50, completed: 10 + i * 8, progressLabel: `${10 + i * 8} of 50` }))),
  },
};
export const FailuresOnly: Story = {
  args: { bridge: bridgeFor([op({ id: "f1", status: "failed", result: null, error: "Provider unreachable" }), op({ id: "f2", type: "pdf_corpus", icon: "pdf", label: "PDF corpus build", status: "blocked", result: { kind: "build" }, subtitle: "Segmentation needs a decision" })]) },
};
export const LongNames: Story = {
  args: { bridge: bridgeFor([op({ id: "l", type: "pdf_corpus", icon: "pdf", label: "PDF corpus build of a book with an extraordinarily long title that must wrap without clipping or overflowing the card", status: "running", finishedAt: null, result: null, subtitle: "Jacques_Derrida_-_Of_Grammatology_Corrected_Edition_Johns_Hopkins_University_Press_1997_scan_with_ocr_layer.pdf · Metadata: 54/180 settled", total: 100, completed: 45, progressLabel: "45% overall", facts: [{ name: "Source PDF", value: "Jacques_Derrida_-_Of_Grammatology_Corrected_Edition_Johns_Hopkins_University_Press_1997_scan_with_ocr_layer.pdf" }] })]) },
};
export const LongHistory: Story = {
  args: { bridge: bridgeFor(Array.from({ length: 14 }, (_, i) => op({ id: `h${i}`, label: `Languages · ${["Deutsch", "Español", "Italiano", "Nederlands"][i % 4]}`, finishedAt: iso(-3000 - i * 40000), startedAt: iso(-3100 - i * 40000) }))) },
};
export const Narrow: Story = {
  decorators: [() => ({ template: '<div style="width:360px"><story /></div>' })],
};
export const FrenchFormatting: Story = { parameters: { locale: "fr-CA" } };
