# DerridAI historical version map

This file maps the versioned project snapshots referenced in the DerridAI project history to the Git repository lineage.

The important finding is that the repository has two distinct historical sources:

1. the original GitHub DAG, continuous from the initial commit through the current 0.58.6 branch; and
2. a reconstructed release DAG preserved in the 0.58.0 build-candidate repository, covering the Vue-era release snapshots from 0.35.10 fixed2 through 0.58.0.

The reconstructed DAG is exact with respect to the archived release snapshots, but those Git objects are not yet present in GitHub's object database. The SHAs below identify the local reconstructed commits and must not be retagged onto unrelated GitHub commits.

## Current GitHub lineage

The default branch has been fast-forwarded to the 0.58.6 line. The current GitHub release lineage includes:

| Version / release | GitHub commit | Status |
|---|---|---|
| 0.58.5 — Radical Rex | `8cc054aad2803e1d07e96bcb8aedcd94e9e29169` | Exact |
| 0.58.5 compose fix | `0f62a862368ead1ff984673cfd23f085ffb80248` | Exact |
| 0.58.5 clean-clone startup fix | `9783504457c92705001559ad3d2307e5f18afc68` | Exact |
| 0.58.5 startup regression guard | `906f236794b3afd40cf0df01763e5fe2e40b3740` | Exact |
| 0.58.6 — Risky Rabbit | `4fc4fce3400d5348ae18dad45b6a7700e0ab92b8` | Exact |
| 0.58.6 historical-map update | `b0d369cffb5410ad8cb1bf0d5f7e7dc20b215785` | Exact |

The original repository ancestry remains continuous back to:

- `3366fa9e15658d941f4220a699624df2df174f3e` — `initial commit`
- Git timestamp: `2026-08-17T08:18:13Z`

The last pre-0.58.5 checkpoint is:

- `620f3033a7d1196bd241b38cf3342c324e04ddc4` — `checkpoint`
- Git timestamp: `2026-09-13T05:41:13Z`

## Reconstructed release DAG preserved in the 0.58.0 build candidate

The 0.58.0 build candidate contains a complete local Git lineage for the following release snapshots. These are exact local reconstructed commits, not speculative mappings:

| Release | Reconstructed commit |
|---|---|
| 0.35.10 fixed2 | `1a829d8` |
| 0.35.10 fixed3 | `2edca91` |
| 0.35.10 fixed4 | `aed33bb` |
| 0.35.12 — Tongue Twister | `864a560` |
| 0.35.16 — Tongue Tied Again | `a157a51` |
| 0.35.17 — Lingua Franca | `4c66b4e` |
| 0.36.0 — The SQL Prequel | `6799fbf` |
| 0.36.1 | `a7ae270` |
| 0.36.2 — Bugs in the Machine | `b64c68d` |
| 0.36.3 — All The Little Things | `9b79f82` |
| 0.36.4 — Oops You Did It Again | `3aa7a8e` |
| 0.36.10 — In Search of Lost Time | `e055c0f` |
| 0.36.11 — Peekaboo | `fb35d8d` |
| 0.37.0 — New Direction | `4a9f97b` |
| 0.37.1 — Disoriented | `14eb3c7` |
| 0.40.0 — Pdffffffffft. | `c103950` |
| 0.40.1 — Dorar the Explorah | `0bc63f3` |
| 0.40.5 — Record Extraction Pipeline Corrections | `98673cf` |
| 0.40.6 — Not Quite Building a Corpus | `9a5cccb` |
| 0.40.8 — Coming Around the Mountain | `c01dda0` |
| 0.40.9 — Enter Sandman | `7346855` |
| 0.40.10 — Corpus of Engineers | `06c18df` |
| 0.40.15 — The Record Scratch Moment | `3f37696` |
| 0.40.20 — You're Probably Wondering How I Got Here | `e75d7df` |
| 0.40.25 — Sensible Chuckles | `ae16673` |
| 0.41.0 — Aardvark | `d91ffba` |
| 0.42.0 — Bunny Rabbit | `0dd9927` / fixed `b979750` |
| 0.42.1 — Bunny Rabbit - Again | `df91f2b` |
| 0.43.0 — Crocodile | `2008be0` |
| 0.43.5 — Dundee | `1793d9d` / fixed `0deb690` |
| 0.44.0 — Dachshund | `ed07d38` / progressive-review fix `59fdbbd` |
| 0.47.1 — Fatso | `7ef720b` |
| 0.48.0 — Frightened Ferret | `9878a3f` |
| 0.48.1 — Gifted Grungus | `d718a9f` |
| 0.49.0 — Hungry Hippo | `7cd3fd2` |
| 0.50.0 — Ingenious Iguana | `25f7806` |
| 0.50.1 — Ignoble Insect | `bf3c41c` |
| 0.51.0 — Krazy Kangaroo | `264ea03` |
| 0.52.0 — Lazy Lizard | `8fc1be0` |
| 0.53.0 — Manic Monkey | `d1a03f3` |
| 0.54.0 — Neurotic Gnat | `8c96849` |
| 0.55.0 — Outrageous Orangutan | `417e89f` |
| 0.56.0 — Perilous Penguins | `b47a3b3` / scope hotfix `fddaa34` |
| 0.57.0 — Quiet Camel | `07e9b6b` |
| 0.57.5 — Quizzical Quacker | `8eb1f6a` |
| 0.57.6 — Quippy Quokka | `f757466` |
| 0.58.0 — Righteous Rhinoceros | `d80e5c3` |

The reconstructed DAG also contains intermediate non-release fixes between several of these release commits. Those commits should be preserved if the reconstructed object database is imported; importing only the release commits would lose part of the actual reconstructed ancestry.

## Earlier snapshot-only versions

The following versions are evidenced by project archives or conversations but do not have exact Git commits in either the original GitHub DAG or the reconstructed 0.35.10–0.58.0 DAG:

| Version / range | Evidence | Status |
|---|---|---|
| 0.10.1 | Uploaded archive `derridai_corpus_viewer_v0.10.1(1).zip` | Snapshot-only |
| 0.20.x–0.23.0 | Project lineage titled `DerridAI <=0.23.0` | Snapshot-only; microversion boundaries not recoverable from Git metadata |
| 0.30.3 | Explicit project version request | Snapshot-only |
| 0.30.5 | Explicit project version request | Snapshot-only |
| 0.30.11 — Big Packet Reduction | Explicit project version request | Placeholder GitHub branch exists, but its commit does not contain the snapshot |
| 0.36.15 | Project build output references the Vue application tree | Snapshot-only |

## Provenance rule

Do not tag an unrelated GitHub commit with one of the reconstructed release numbers merely to make the tag exist. The Vue-era snapshots have materially different trees from the pre-0.58.5 GitHub checkpoint. A false tag would destroy provenance rather than repair it.

For reconstructed historical commits:

1. preserve the reconstructed commit/tree when available;
2. preserve original archive timestamps when available;
3. otherwise record timestamps as reconstructed, not original;
4. preserve intermediate fix commits in the reconstructed DAG;
5. only mark a version `Exact` on GitHub once its actual reconstructed Git objects are present in GitHub's object database.
