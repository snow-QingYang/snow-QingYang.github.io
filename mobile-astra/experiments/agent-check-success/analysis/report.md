# E06 · No task progress and agent success

GPT-6-Astra / xhigh · RoboCasa composite · 32 tasks × seeds 1–5.

Score: native env.check_success after the planner returns. Agent declarations are separate.

| Split | E01 baseline | E03 No task progress | E06 |
| --- | ---: | ---: | ---: |
| seen | 34/80 (42.50%) | 24/80 (30.00%) | 18/80 (22.50%) |
| unseen | 21/80 (26.25%) | 17/80 (21.25%) | 11/80 (13.75%) |
| all | 55/160 (34.38%) | 41/160 (25.63%) | 29/160 (18.13%) |

## Agent declaration vs final native score

| Declaration | Native success | Native failure |
| --- | ---: | ---: |
| success | 28 | 15 |
| stuck | 0 | 90 |
| failure | 0 | 1 |
| no_finish | 1 | 25 |

134/160 episodes called finish; 26 returned without it. The sole native success without finish was WaffleReheat, seed 4 (Unseen).
43 success claims include 15 final native failures. All 160 valid episodes remain in the denominator.

## Settings and interpretation

No task_progress, success or robocasa_terminated in Agent observations; no native-success early VLA stop. No success_criteria.md is generated. The prompt asks the Agent to judge completion and call finish; runtime does not enforce that call.

Simulator geometry, camera calibration, robot state, contact feedback and selected memory remain. Private native predicate calls preserve simulator bookkeeping. Final scoring is not shown to the running Agent.

- Task/seed matching; initial scene and VLA sampling equivalence not audited for E06.
- Published E03 predates the later No task progress revision that stopped generating success_criteria.md.
- Native scoring happens after the planner returns; agent claims are reported separately.
- Prompt requests finish, but the planner can return without calling it.

## Task / seed results

Each seed cell is E01 / E03 / E06 followed by the E06 declaration; 1 = native success, 0 = failure.

| Split | Task | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Seed 5 |
| --- | --- | --- | --- | --- | --- | --- |
| seen | ScrubCuttingBoard | 1 / 1 / 0 · success | 1 / 0 / 1 · success | 1 / 0 / 1 · success | 1 / 0 / 0 · success | 1 / 1 / 1 · success |
| seen | StackBowlsCabinet | 1 / 1 / 1 · success | 1 / 0 / 0 · stuck | 1 / 1 / 0 · stuck | 1 / 0 / 0 · stuck | 1 / 1 / 1 · success |
| seen | WashLettuce | 1 / 1 / 0 · success | 0 / 1 / 0 · stuck | 1 / 1 / 1 · success | 1 / 1 / 1 · success | 1 / 1 / 0 · success |
| seen | RinseSinkBasin | 1 / 0 / 0 · stuck | 1 / 0 / 1 · success | 1 / 1 / 0 · stuck | 0 / 1 / 1 · success | 0 / 1 / 0 · stuck |
| seen | PreSoakPan | 0 / 0 / 0 · stuck | 1 / 0 / 0 · stuck | 1 / 1 / 1 · success | 0 / 1 / 0 · no_finish | 1 / 1 / 0 · no_finish |
| seen | StirVegetables | 0 / 0 / 0 · success | 0 / 0 / 0 · no_finish | 1 / 0 / 1 · success | 0 / 1 / 0 · success | 1 / 0 / 0 · stuck |
| seen | LoadDishwasher | 1 / 1 / 0 · success | 1 / 0 / 0 · success | 1 / 0 / 0 · stuck | 0 / 1 / 0 · success | 0 / 0 / 0 · no_finish |
| seen | SteamInMicrowave | 0 / 0 / 0 · stuck | 0 / 0 / 1 · success | 1 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 1 / 0 / 1 · success |
| seen | SetUpCuttingStation | 0 / 0 / 1 · success | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| seen | GetToastedBread | 0 / 0 / 0 · no_finish | 1 / 0 / 0 · success | 0 / 0 / 0 · no_finish | 0 / 0 / 1 · success | 0 / 0 / 0 · stuck |
| seen | DeliverStraw | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 1 / 1 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| seen | KettleBoiling | 1 / 0 / 0 · stuck | 0 / 1 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 1 / 0 · no_finish | 0 / 1 / 1 · success |
| seen | PrepareCoffee | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 1 / 0 / 0 · stuck | 1 / 0 / 0 · stuck |
| seen | StoreLeftoversInBowl | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| seen | SearingMeat | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| seen | PackIdenticalLunches | 0 / 1 / 1 · success | 0 / 0 / 0 · no_finish | 0 / 0 / 1 · success | 1 / 0 / 0 · no_finish | 1 / 0 / 0 · no_finish |
| unseen | ArrangeBreadBasket | 0 / 1 / 0 · stuck | 0 / 0 / 0 · stuck | 1 / 1 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| unseen | ArrangeTea | 0 / 0 / 0 · stuck | 0 / 0 / 1 · success | 0 / 0 / 0 · stuck | 1 / 0 / 0 · success | 0 / 0 / 0 · stuck |
| unseen | BreadSelection | 1 / 1 / 1 · success | 0 / 0 / 0 · stuck | 1 / 1 / 0 · no_finish | 1 / 0 / 0 · success | 0 / 0 / 0 · stuck |
| unseen | CategorizeCondiments | 0 / 1 / 0 · stuck | 0 / 0 / 0 · success | 0 / 0 / 0 · stuck | 0 / 1 / 0 · stuck | 0 / 0 / 0 · stuck |
| unseen | CuttingToolSelection | 1 / 1 / 1 · success | 0 / 0 / 1 · success | 0 / 0 / 0 · stuck | 1 / 0 / 1 · success | 0 / 0 / 0 · stuck |
| unseen | GarnishPancake | 0 / 0 / 0 · no_finish | 1 / 0 / 1 · success | 0 / 0 / 0 · stuck | 1 / 1 / 1 · success | 1 / 1 / 0 · stuck |
| unseen | GatherTableware | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 1 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| unseen | HeatKebabSandwich | 0 / 0 / 0 · no_finish | 0 / 0 / 0 · no_finish | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · no_finish |
| unseen | MakeIceLemonade | 0 / 0 / 0 · stuck | 1 / 0 / 1 · success | 0 / 0 / 0 · stuck | 0 / 0 / 0 · no_finish | 0 / 0 / 0 · stuck |
| unseen | PanTransfer | 0 / 1 / 0 · no_finish | 0 / 0 / 0 · failure | 1 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| unseen | PortionHotDogs | 0 / 1 / 0 · no_finish | 0 / 1 / 0 · no_finish | 1 / 1 / 0 · stuck | 1 / 1 / 0 · no_finish | 0 / 0 / 0 · no_finish |
| unseen | RecycleBottlesByType | 1 / 0 / 0 · success | 0 / 0 / 0 · no_finish | 0 / 0 / 0 · stuck | 1 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| unseen | SeparateFreezerRack | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck |
| unseen | WaffleReheat | 1 / 1 / 0 · success | 1 / 1 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 1 · no_finish | 0 / 0 / 0 · no_finish |
| unseen | WashFruitColander | 1 / 0 / 0 · stuck | 0 / 0 / 0 · no_finish | 1 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 0 / 0 · no_finish |
| unseen | WeighIngredients | 0 / 0 / 0 · stuck | 0 / 0 / 0 · stuck | 0 / 1 / 1 · success | 0 / 0 / 0 · stuck | 0 / 0 / 1 · success |

## Provenance

Run: `official_main_composite_agentstop_astra_xhigh_20261106T141106Z`.

Published commit: `412efe9c32e3cac630c77138da86def960968610` (documentation name update; runtime implementation `65f7e1b85eba219c28ccb75f94740d75071fca34`); branch `no_task_progress_and_agent_success`.

JSON and CSV contain per-result SHA-256 hashes. The extractor verifies all canonical cells, runtime/model settings, final summary and E01 reference agreement. It exports only selected structured fields; no raw transcripts or credentials.
