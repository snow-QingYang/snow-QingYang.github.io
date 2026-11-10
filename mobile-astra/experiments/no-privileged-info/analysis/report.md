# E08 · 组合信息移除（保留 success）

Completed 2026-11-10 06:07, Hong Kong time. GPT-6-Astra / xhigh, RLDX-1-FT-RC365, 32 RoboCasa composite tasks × seeds 1–5. All 160 episodes are valid and scored using simulator success. Task failures remain in the denominator.

| Split | Baseline | Geometry queries removed | Combined removal |
| --- | ---: | ---: | ---: |
| Seen | 34/80 · 42.50% | 22/80 · 27.50% | 27/80 · 33.75% |
| Unseen | 21/80 · 26.25% | 17/80 · 21.25% | 14/80 · 17.50% |
| All | 55/160 · 34.38% | 39/160 · 24.38% | 41/160 · 25.63% |

Combined removal is 14 successes below baseline and 2 above geometry removal. The latter difference consists of +5 Seen and −3 Unseen successes. One run with five seeds per task does not establish a benefit from removing additional information.

## Information boundary

| Information | Agent exposure | Internal or saved state |
| --- | --- | --- |
| Active object geometry | `back_project_batch` and `query_world_map` are unregistered. No SceneGraph or DA3 replacement. Agent-specified XYZ/XY actions remain. | Simulator geometry, depth, world maps and camera metadata remain available internally. Depth/world-map NPZ artifacts retain the original rolling window of 25 steps; RGB and camera metadata are not cleaned up by this window. |
| Historical task/global memory | Policy is `none`; selected and read memory lists are empty. | Existing memory corpus remains on disk and may be validated during startup. Current episode conversation and action history remain. |
| Task progress | Observation construction no longer queries `task_progress`; it is absent from current, historical and post-action returns and saved states. | Simulator task subconditions still exist; physics and native task criteria are not removed. |
| Contact/grasp labels | VLA wrapper no longer queries the contact report; `grasp_contact`, `grasp_obj`, `grasped`, `grasp_detected` are absent. | Simulator contact physics continues to run. The four labels are absent from saved action results. |
| Success criteria source | `success_criteria.md` is not generated; evaluation file tools deny all text reads. | Runtime source still exists on disk. `write_text_file` can save Agent-written episode notes. |
| Native success | `success`, `robocasa_terminated` and native VLA success early stopping remain. | Final result is scored using native simulator success. |
| Robot state | Exact EEF, base and gripper state remain. `held_apart`, `peak_lift`, `base_drift` remain. | `held_apart` is a command/finger-width heuristic, not the removed simulator contact label. |
| Action feedback | Agent targets, step counts and execution errors such as `final_dist` remain. | These describe controller execution, not task-subcondition distance. |
| Fixed priors/control | Counter height ≈0.9 m and arm reach ≈0.8 m remain in the prompt. | VLA weights, inputs, history, controller and budgets retain baseline behavior. |
| Episode records | Only the permitted observation fields enter the recorded Agent context. | RGB, observations, actions, full Agent streams and results are archived locally. Only depth/world-map NPZ artifacts are subject to the 25-step cleanup window. This site publishes only derived, sanitized records and hashes. |

This is not an all-ground-truth removal or an operating-system sandbox. Runtime source and internal artifacts were not deleted from disk. The audit below describes observed Agent context, not OS-level access prevention.

## Camera information

Planner RGB views are `agentview` = `robot0_agentview_left`, `navview` = `mobilebase0_navview`, and `wrist` = `robot0_eye_in_hand`. Camera/role labels and their visual-use descriptions are visible. Numeric K, R/t, camera pose and FOV are not returned to the Agent. `calibration_frame` is a role label, not a calibration matrix. “Primary global view” in the prompt describes its role; it is not an extra independent global camera.

VLA receives its original 256×256 left/right/wrist RGB images, task text and proprioception. This differs from the Planner's agentview/navview/wrist set. Camera metadata, depth, world maps and `navview_floor.png` remain internal artifacts. Only the depth/world-map NPZ files retain the most recent 25 steps by default; this cleanup does not remove RGB or camera metadata. Exact robot base/EEF poses are still exposed; these are different from numeric camera calibration.

## Success paths

| Split | VLA actions only | Manual intervention, then VLA success | First success after manual action |
| --- | ---: | ---: | ---: |
| Seen | 15 | 9 | 3 |
| Unseen | 7 | 4 | 3 |
| All | 22 | 13 | 6 |

VLA actions include `rldx_skill` and `rldx_arm`. Manual actions are physical primitives issued by the Planner, excluding observation, file writing and `finish`. All 41 successful episodes use VLA. Of the 19 with manual intervention, 13 first become successful after VLA and 6 after a manual action (`move_delta`: 4, `scripted_grasp`: 1, `set_gripper`: 1). These are trajectory classifications, not causal estimates. VLA-only actions do not mean a Planner-free VLA experiment.

## Paired comparison and initial conditions

Against geometry removal, 23 pairs both succeed, 18 succeed only with combined removal, 16 only with geometry removal, and 103 both fail. Thus 34 episodes flip outcome behind the net +2 successes. Against baseline the corresponding counts are 27, 14, 28 and 91.

132/160 combined-versus-geometry pairs match exactly on saved initial robot state, task text, all three RGB PNGs and recorded camera metadata. Combined removal succeeds in 31/132 and geometry removal in 32/132. This is a post-hoc diagnostic subset, not the full benchmark or a causal estimate. Of the 34 outcome flips, 25 have this exact match (12 gains, 13 losses).

140 robot states match exactly. Another 5 differ by no more than 1e-6 and 15 have material position differences. Task language differs in five episodes:

| Task / seed | Combined | Geometry removal |
| --- | --- | --- |
| SteamInMicrowave s2 | bell pepper | lime |
| SteamInMicrowave s5 | onion | lemon |
| WashFruitColander s3 | peach, tangerine, orange | kiwi, orange |
| WashFruitColander s4 | tangerine | apple × 3 |
| WashFruitColander s5 | banana, apple | tangerine |

A differing PNG hash alone does not prove a changed scene: some images differ by one intensity level in only a few pixels. Complete scene XML, every object's initial state and RNG state were not saved. The environment seeds its own generator; the available logs do not establish the specific cause of the remaining initial-condition differences.

VLA inference also contains random action sampling without matched per-call noise. In `StackBowlsCabinet_s2`, the initial records and first four VLA instructions match, but the EEF differs by approximately 0.199 m after the first VLA call, before manual intervention. This difference cannot be attributed to fewer manual actions or a memory recommendation.

## Context and scoring audit

- 160 valid episodes, all processes exited normally; final native success agrees with every result.
- 4,632 completed tool returns and 4,327 saved observation snapshots audited.
- Removed task-progress/contact field hits: 0. Geometry-tool calls: 0.
- File-read calls: 0. Native shell calls: 0. Empty selected/read memory lists: 160/160.
- Generated `success_criteria.md` files: 0. Scoring mismatches: 0.
- No object/fixture coordinates, bounding boxes, depth or world-map arrays were found in returned JSON. Position numbers describe robot state or Agent-issued action targets.

## Provenance

Branch: `no_privileged_info`; commit: `5e612e916c011bcc76431efd1775040f86563fef`. **Code status: recorded locally, pending publication.** No GitHub commit link is claimed. Official base: `a744bd5f128ebef3cb8c6736cf7cd98adff681f1`.

Run IDs:

- Combined: `official_main_composite_no_privileged_info_astra_xhigh_20261109T151754Z`
- Geometry removal: `official_main_composite_nogeomtools_astra_xhigh_20261104T093002Z`
- Baseline: `official_main_composite_astra_xhigh_20261101T150450Z`

Environment split `target`; 100 Planner responses, 3,600 s per episode; VLA 40 chunks × 8 actions; settle patience 999. [data.json](data.json) contains sanitized outcomes, action counts, initial-evidence hashes, source-file hashes and audit-evidence hashes. [episodes.csv](episodes.csv) is the flat numerical export. [extract.py](extract.py) regenerates both from local archived run roots and verifies counts. Raw model streams, credentials, absolute machine paths and complete runtime source are not published.
