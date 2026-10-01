/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { SemanticAliasList } from "../../api/corpus";
import CorpusSemanticAliasPanel from "./CorpusSemanticAliasPanel.vue";

const aliases: SemanticAliasList = {
  items: [
    {
      alias_set_id: "alias-author",
      kind: "person",
      canonical_label: "Jane Author",
      aliases: ["J. Author", "Author, Jane"],
      reason: "Signed preface and title page.",
      reviewer: "reviewer-1",
      created_at: "2026-09-12T10:00:00Z",
      imported_from: {
        build_id: "build-grammatology",
        alias_set_id: "alias-7",
        build_title: "Of Grammatology",
      },
    },
    {
      alias_set_id: "alias-dingus-a",
      kind: "person",
      canonical_label: "J. P. Dingus",
      aliases: [],
      created_at: "2026-09-13T10:00:00Z",
    },
    {
      alias_set_id: "alias-dingus-b",
      kind: "person",
      canonical_label: "JP Dingus",
      aliases: ["Jean-Paul Dingus"],
      reason: "A different author of the same surname.",
      created_at: "2026-09-13T11:00:00Z",
    },
    {
      alias_set_id: "alias-difference",
      kind: "concept",
      canonical_label: "différance",
      aliases: ["differance"],
      created_at: "2026-09-14T09:30:00Z",
    },
  ],
  kinds: [
    { kind: "concept", mode: "lexical_phrase", fields: ["concepts"] },
    { kind: "person", mode: "entity_name", fields: ["speaker", "position_holder", "persons"] },
  ],
};

function stubFetch(list: SemanticAliasList) {
  const original = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input instanceof Request ? input.url : input);
    if (!url.includes("/semantic-aliases")) return original(input, init);
    const method = init?.method ?? "GET";
    const body = url.includes("/semantic-aliases/sources")
      ? {
          items: [
            {
              build_id: "build-grammatology",
              title: "Of Grammatology",
              alias_sets: 2,
              kinds: ["person"],
            },
          ],
        }
      : url.includes("/semantic-aliases/import")
        ? { imported: [list.items[0]], skipped: [] }
        : method === "GET"
          ? list
          : list.items[0];
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
}

const meta = {
  title: "Corpus Builder/Review/Reviewed identities",
  component: CorpusSemanticAliasPanel,
  args: { buildId: "build-story", disabled: false },
  decorators: [
    (story, context) => {
      stubFetch((context.parameters.aliases as SemanticAliasList) || aliases);
      return story();
    },
  ],
} satisfies Meta<typeof CorpusSemanticAliasPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Open the disclosure to load the reviewed identities. */
export const WithIdentities: Story = {};

export const Empty: Story = {
  parameters: { aliases: { items: [], kinds: aliases.kinds } },
};

export const NoComparableFields: Story = {
  parameters: { aliases: { items: [], kinds: [] } },
};

export const Disabled: Story = { args: { disabled: true } };

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
