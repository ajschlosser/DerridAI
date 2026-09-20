/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createProviderProfiles } from "../../src/domain/providerProfilesService";

// The snapshots were verified to be identical to the original legacy runtime.js functions (results, final
// state and the API/persist calls made) across these configurations and operations before they were recorded.
function world(appConfig: Record<string, unknown>, researcher: boolean) {
  const log: unknown[] = [];
  const state: Record<string, any> = {
    appConfig: structuredClone(appConfig),
    llmConfig: { model: "gemma", num_ctx: 4096 },
    researcherProviderProfiles: [{ id: "rp", type: "openai", name: "R" }],
    providerStatuses: {},
    providerWarmups: {},
    llmStatus: null,
  };
  let n = 0;
  const uid = () => `uid${++n}`;
  const api = async (path: string, opts?: { body?: string }) => {
    log.push(["api", path, opts?.body ?? null]);
    if (String(opts?.body ?? "").includes("boom")) throw new Error("boom");
    return { ok: true, models: [{ name: "m1" }], path };
  };
  const persistPrefs = () => log.push(["persist"]);
  const isResearcher = () => researcher;
  const warmupProviderProfile = async (p: unknown, o: unknown) => {
    log.push(["warm", p, o]);
  };
  const fns = createProviderProfiles({
    state,
    api,
    persistPrefs,
    uid,
    isResearcher,
    warmupProviderProfile,
  } as never) as unknown as Record<string, (...a: unknown[]) => unknown>;
  return { state, log, fns };
}
const settle = async (v: unknown) => {
  try {
    return { ok: JSON.parse(JSON.stringify(await v, (_k, x) => (x === undefined ? "__u" : x))) };
  } catch (e) {
    return { err: (e as Error).message };
  }
};

const configs: Array<Record<string, unknown>> = [
  {},
  { default_provider_profile: "", provider_profiles: [] },
  {
    provider_profiles: [
      { id: "a", type: "ollama", name: "A", model: "x" },
      { id: "b", type: "openai", name: "B", api_key: "k", model_mode: "auto" },
    ],
    default_provider_profile: "b",
  },
  {
    provider_profiles: [{ id: "a", type: "ollama" }],
    default_provider_profile: "zzz",
    ollama_base_url: "http://o",
    openai_base_url: "http://p/v1",
    openai_api_key: "sk",
    openai_model: "gpt",
    embedding_model: "e",
  },
  {
    ollama_base_url: "http://legacy",
    openai_model_mode: "manual",
    openai_model_kind: "coding",
    openai_temperature: 0.2,
    warm_default_provider_on_start: true,
    review_provider_profile: "a",
    background_llm: false,
  },
];

describe("provider profiles service", () => {
  it("behaves as recorded across configurations, roles and operations", async () => {
    const recorded: unknown[] = [];
    for (const cfg of configs) {
      for (const researcher of [false, true]) {
        const M = world(cfg, researcher);
        const ops: Array<[string, unknown[]]> = [
          ["ensureProviderProfiles", []],
          ["providerProfiles", []],
          ["getProviderProfilesForUi", []],
          ["getDefaultProviderProfileId", []],
          ["providerProfile", ["a"]],
          ["providerProfile", ["zzz"]],
          ["defaultProviderProfile", []],
          ["providerDisplayName", [{ name: "N", type: "ollama", model: "m" }]],
          ["providerDisplayName", [{ type: "openai" }]],
          ["getProviderRequestConfigForUi", ["a"]],
          ["getProviderRequestConfigForUi", ["b", { textReview: true }]],
          ["getProviderRequestConfigForUi", ["none"]],
          ["addProviderProfileForUi", ["ollama"]],
          ["addProviderProfileForUi", ["openai"]],
          ["getProviderProfilesForUi", []],
          ["setDefaultProviderProfileForUi", ["a"]],
          ["setDefaultProviderProfileForUi", ["nope"]],
          ["getDefaultProviderProfileId", []],
          [
            "saveProviderProfilesForUi",
            [
              [
                { id: "a", type: "ollama", name: "Renamed", model: "q", temperature: "0.3" },
                { id: "n2", type: "openai", model_mode: "auto", api_key: "z" },
              ],
            ],
          ],
          ["saveProviderProfilesForUi", [[]]],
          ["getWarmOnStartForUi", []],
          ["setWarmOnStartForUi", [true]],
          ["getWarmOnStartForUi", []],
          ["setWarmOnStartForUi", [""]],
          ["refreshProviderStatuses", []],
          ["getProviderStatusesForUi", []],
          ["testProviderProfileForUi", ["a"]],
          ["testProviderProfileForUi", ["missing"]],
          ["warmProviderProfileForUi", ["a"]],
          ["warmProviderProfileForUi", ["missing"]],
          ["getProviderWarmupsForUi", []],
          ["removeProviderProfileForUi", ["a"]],
          ["removeProviderProfileForUi", ["zzz"]],
          ["getProviderProfilesForUi", []],
          ["getDefaultProviderProfileId", []],
          ["providerProfiles", []],
        ];
        const results: unknown[] = [];
        for (const [name, args] of ops)
          results.push([name, await settle((async () => M.fns[name](...args))())]);
        recorded.push({
          researcher,
          results,
          state: JSON.parse(JSON.stringify(M.state)),
          log: M.log,
        });
      }
    }
    expect(recorded).toMatchSnapshot();
  });
  it("keeps a default profile after removing the current one", async () => {
    const M = world(
      {
        provider_profiles: [
          { id: "a", type: "ollama" },
          { id: "b", type: "openai" },
        ],
        default_provider_profile: "a",
      },
      false,
    );
    M.fns.ensureProviderProfiles();
    M.fns.removeProviderProfileForUi("a");
    expect(M.fns.getDefaultProviderProfileId()).toBe("b");
  });
});
