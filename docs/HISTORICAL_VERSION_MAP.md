# DerridAI historical version map

This file maps the versioned project snapshots referenced in the DerridAI project history to the Git repository lineage.

The important finding is that the current Git DAG and the later versioned application snapshots are not the same historical record. The repository ancestry is continuous back to the initial commit, but several versioned snapshots were produced in project conversations without being committed into this Git repository.

## Mapping status

| Version / range | Project evidence date (America/Los_Angeles) | Snapshot evidence | Git mapping | Status |
|---|---:|---|---|---|
| 0.10.1 | 2026-09-11 | Uploaded archive named `derridai_corpus_viewer_v0.10.1(1).zip` | No matching versioned commit or tag in the Git DAG | Snapshot-only |
| 0.20.x–0.23.0 | 2026-09-09 | Project conversation lineage titled `DerridAI <=0.23.0` | No commits or tags whose messages identify 0.20.x, 0.21.x, 0.22.x, or 0.23.x | Snapshot-only; individual microversion boundaries are not recoverable from Git metadata |
| 0.30.3 | 2026-09-12 | Explicit version request in the project history | No exact Git commit | Snapshot-only |
| 0.30.5 | 2026-09-12 | Explicit version request in the project history | No exact Git commit | Snapshot-only |
| 0.30.11 — Big Packet Reduction | 2026-09-14 | Explicit version request in the project history | Branch `feature/0.30.11-big-packet-reduction` exists, but is identical to `master` at `620f3033a7d1196bd241b38cf3342c324e04ddc4` | Branch label exists; snapshot contents are not represented by that commit |
| 0.36.15 | 2026-09-14 | Project build output references Vue source such as `src/components/CitationMenu.vue` | No matching Git commit; `620f3033...` has the older static `web/index.html` / `web/scripts/derridai.js` layout | Snapshot-only |
| 0.37.0 — New Direction | 2026-09 (branch label) | Git branch name `release/0.37.0-new-direction` | Branch is identical to `master` at `620f3033a7d1196bd241b38cf3342c324e04ddc4` | Placeholder branch, not a distinct historical snapshot |
| 0.40.5 — Record Extraction Pipeline Corrections | 2026-09-15 | Explicit version request in the project history | No matching Git commit | Snapshot-only |
| 0.40.8 — Coming Around the Mountain | 2026-09-16 | Explicit version request; build output references `src/components/CorpusBuildProgress.vue` | No matching Git commit | Snapshot-only |
| 0.58.5 — Radical Rex | 2026-09-18 | Current implementation | `8cc054aad2803e1d07e96bcb8aedcd94e9e29169` | Exact |
| 0.58.5 compose fix | 2026-09-18 | Fix for unset `OLLAMA_MODELS_DIR` | `0f62a862368ead1ff984673cfd23f085ffb80248` | Exact |
| 0.58.5 clean-clone startup fix | 2026-09-18 | Removes untracked `api/data` startup dependency and lazy-loads NLP models | `9783504457c92705001559ad3d2307e5f18afc68` | Exact |
| 0.58.5 startup regression guard | 2026-09-18 | Prevents reintroduction of clean-clone startup dependency | `906f236794b3afd40cf0df01763e5fe2e40b3740` | Exact |
| 0.58.6 — Risky Rabbit | 2026-09-18 | Release identity for the clean-clone/container-startup fixes | `4fc4fce3400d5348ae18dad45b6a7700e0ab92b8` | Exact |

## Git ancestry actually present

The `release/0.58.6-risky-rabbit` branch contains the complete Radical Rex lineage plus the clean-clone/startup fixes and Risky Rabbit release commit. Its ancestry remains continuous back to:

- `3366fa9e15658d941f4220a699624df2df174f3e` — `initial commit`
- Git timestamp: `2026-08-17T08:18:13Z`
- Local equivalent: 2026-08-17 01:18:13 PDT

The repository's last pre-Radical-Rex checkpoint is:

- `620f3033a7d1196bd241b38cf3342c324e04ddc4` — `checkpoint`
- Git timestamp: `2026-09-13T05:41:13Z`
- Local equivalent: 2026-09-12 22:41:13 PDT

The Git history contains no chronology reversals among those 98 commits, and the author/committer timestamps match for every commit in that ancestry.

## Why the snapshot versions cannot be tagged onto the existing commits

The later snapshots demonstrably contain a different application structure from the repository checkpoint they would otherwise be mapped onto.

Examples from the project history include Vue build paths such as:

- `src/components/CitationMenu.vue`
- `src/components/CorpusBuildProgress.vue`

By contrast, the `620f3033...` tree contains the older static frontend structure:

- `web/index.html`
- `web/scripts/derridai.js`

and does not contain the Vue application tree reflected in the 0.36.x–0.40.x snapshots.

Therefore tagging `620f3033...` as `v0.30.11`, `v0.36.15`, `v0.37.0`, `v0.40.5`, or `v0.40.8` would create false provenance.

## Timestamp policy for historical reconstruction

Project-conversation timestamps establish when a snapshot/version was being worked on, but they are not automatically equivalent to a Git author timestamp.

For reconstructed historical commits:

1. preserve any original filesystem/archive timestamp when one is available;
2. otherwise use the version snapshot's actual generated/uploaded timestamp if recoverable;
3. if only the project-conversation timestamp survives, record it explicitly as a reconstructed timestamp rather than pretending it was an original Git commit time;
4. do not use the date on which the snapshot is imported into Git as the historical release date.

The 0.58.5 and 0.58.6 commits are not reconstructed; their Git timestamps are their actual creation timestamps.
