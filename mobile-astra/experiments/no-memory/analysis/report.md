# E07 · NoMemory

GPT-6-Astra / xhigh · RLDX-1-FT-RC365 · 32 RoboCasa composite tasks × seeds 1–5.

| Split | E01 baseline | E07 NoMemory | Difference |
| --- | ---: | ---: | ---: |
| seen | 34/80 (42.50%) | 24/80 (30.00%) | -12.50 pp |
| unseen | 21/80 (26.25%) | 17/80 (21.25%) | -5.00 pp |
| all | 55/160 (34.38%) | 41/160 (25.63%) | -8.75 pp |

## Matched task/seed outcomes

| Split | Both succeed | Baseline only | NoMemory only | Neither |
| --- | ---: | ---: | ---: | ---: |
| seen | 15 | 19 | 9 | 37 |
| unseen | 6 | 15 | 11 | 48 |
| all | 21 | 34 | 20 | 85 |

## Settings and verification

Removed: Historical task and global memory selection/supply; prompt states no historical memory; read_text_file rejects memory files.

Retained: Current-episode history, geometry, contact, task progress, success, scoring source access, VLA inputs/control and native-success early stopping.

All 320 result scores agree with their final saved native success signal. All 160 NoMemory CLI exits are zero. Smoke episodes are excluded.

All 160 recorded Agent trajectories, including native shell commands, were audited: no historical task/global memory reads or attempts were observed. Source/AGENTS/current-episode reads occurred. Internal corpus validation is retained; this is not an OS-level non-access guarantee.

Initial robot state differs above 1e-6 in 14/160 pairs (23 differ by exact comparison); task instructions differ in 5/160 pairs. Full object states were not audited.

- One batch per setting and five seeds per task; no causal claim from individual outcome changes.
- Initial robot state and task text checked; full object state and independent VLA sampling are not matched.
- E07 and NoTaskGT both score 41/160 but remove different information.

## Task and seed results

Each cell shows baseline / NoMemory; 1 = success, 0 = failure.

| Split | Task | Baseline | NoMemory | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Seed 5 |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| seen | ScrubCuttingBoard | 5/5 | 2/5 | 1 / 1 | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 1 |
| seen | StackBowlsCabinet | 5/5 | 3/5 | 1 / 1 | 1 / 0 | 1 / 1 | 1 / 0 | 1 / 1 |
| seen | WashLettuce | 4/5 | 5/5 | 1 / 1 | 0 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| seen | RinseSinkBasin | 3/5 | 1/5 | 1 / 0 | 1 / 0 | 1 / 1 | 0 / 0 | 0 / 0 |
| seen | PreSoakPan | 3/5 | 3/5 | 0 / 0 | 1 / 1 | 1 / 1 | 0 / 0 | 1 / 1 |
| seen | StirVegetables | 2/5 | 1/5 | 0 / 0 | 0 / 0 | 1 / 0 | 0 / 1 | 1 / 0 |
| seen | LoadDishwasher | 3/5 | 1/5 | 1 / 1 | 1 / 0 | 1 / 0 | 0 / 0 | 0 / 0 |
| seen | SteamInMicrowave | 2/5 | 1/5 | 0 / 0 | 0 / 1 | 1 / 0 | 0 / 0 | 1 / 0 |
| seen | SetUpCuttingStation | 0/5 | 2/5 | 0 / 0 | 0 / 0 | 0 / 1 | 0 / 0 | 0 / 1 |
| seen | GetToastedBread | 1/5 | 1/5 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 1 | 0 / 0 |
| seen | DeliverStraw | 1/5 | 0/5 | 0 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 |
| seen | KettleBoiling | 1/5 | 2/5 | 1 / 0 | 0 / 0 | 0 / 1 | 0 / 0 | 0 / 1 |
| seen | PrepareCoffee | 2/5 | 1/5 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 1 / 0 |
| seen | StoreLeftoversInBowl | 0/5 | 0/5 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| seen | SearingMeat | 0/5 | 0/5 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| seen | PackIdenticalLunches | 2/5 | 1/5 | 0 / 0 | 0 / 0 | 0 / 1 | 1 / 0 | 1 / 0 |
| unseen | ArrangeBreadBasket | 1/5 | 2/5 | 0 / 1 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 1 |
| unseen | ArrangeTea | 1/5 | 2/5 | 0 / 0 | 0 / 1 | 0 / 0 | 1 / 1 | 0 / 0 |
| unseen | BreadSelection | 3/5 | 3/5 | 1 / 0 | 0 / 1 | 1 / 1 | 1 / 1 | 0 / 0 |
| unseen | CategorizeCondiments | 0/5 | 0/5 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| unseen | CuttingToolSelection | 2/5 | 2/5 | 1 / 0 | 0 / 1 | 0 / 1 | 1 / 0 | 0 / 0 |
| unseen | GarnishPancake | 3/5 | 1/5 | 0 / 0 | 1 / 0 | 0 / 0 | 1 / 1 | 1 / 0 |
| unseen | GatherTableware | 1/5 | 0/5 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 0 | 0 / 0 |
| unseen | HeatKebabSandwich | 0/5 | 0/5 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| unseen | MakeIceLemonade | 1/5 | 3/5 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 1 | 0 / 1 |
| unseen | PanTransfer | 1/5 | 0/5 | 0 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 |
| unseen | PortionHotDogs | 2/5 | 1/5 | 0 / 1 | 0 / 0 | 1 / 0 | 1 / 0 | 0 / 0 |
| unseen | RecycleBottlesByType | 2/5 | 0/5 | 1 / 0 | 0 / 0 | 0 / 0 | 1 / 0 | 0 / 0 |
| unseen | SeparateFreezerRack | 0/5 | 0/5 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| unseen | WaffleReheat | 2/5 | 1/5 | 1 / 0 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 |
| unseen | WashFruitColander | 2/5 | 1/5 | 1 / 0 | 0 / 0 | 1 / 0 | 0 / 1 | 0 / 0 |
| unseen | WeighIngredients | 0/5 | 1/5 | 0 / 0 | 0 / 1 | 0 / 0 | 0 / 0 | 0 / 0 |

## Recorded memory access audit

Audited 160 streams and 337,744 JSONL events with zero parse errors. Found 364 native shell commands across 84 episodes (340 completed, 24 failed). No historical memory reads or attempts were observed.

All 160 memory-read logs total 0 bytes. Source searches/reads occurred in 24 episodes; these retained permissions are separate from historical memory.

The source audit notes 2 VLA tool items without a completion event and 1 retryable stream error. All 160 planner turns have completion events. This is a recorded-trajectory audit, not an OS syscall trace.

Private source audit SHA-256: `8b4bad55bb1d92c1a6a4fca5be5448b0a56a1fae78d371634b4deda42233b17f`.

## Provenance

Run: `official_main_composite_nomemory_astra_xhigh_20261108T155013Z`. Finished 2026-11-09 08:57 HKT.

Official base: `a744bd5f128ebef3cb8c6736cf7cd98adff681f1` plus the archived NoMemory patch. NoMemory branch is not yet published.

JSON/CSV include per-episode result and states SHA-256 hashes. JSON also records the source-file hashes, patch, manifest, validation and public baseline data hashes. Only selected public fields are exported.
