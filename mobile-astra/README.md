# HarnessVLA ground-truth study / Mobile Astra

Public work page: https://snow-qingyang.github.io/mobile-astra/

Keep this deployment entirely inside `mobile-astra/`. Do not modify or link from
personal Home, Research, Blog, shared navigation, styles, assets or templates.
All pages are standalone work interfaces. Public URLs are not access control.

## Completed checklist · 2026-11-14

Ten primary GPT-6-Astra / xhigh experiments are complete: 160 valid episodes
per setting, 1,600 total. Each setting has 80 Seen and 80 Unseen episodes.

- [x] [E01 · Baseline](experiments/baseline/): Seen 34/80, Unseen 21/80; **55/160**.
- [x] [E02 · DA3 depth replacement](experiments/geometry-da3/): Seen 33/80, Unseen 17/80; **50/160**.
- [x] [E03 · No task progress](experiments/task-progress/): Seen 24/80, Unseen 17/80; **41/160**.
- [x] [E04 · VLA contact-feedback removal, full task progress](experiments/contact-feedback/): Seen 29/80, Unseen 15/80; **44/160**.
- [x] [E05 · Geometry-query removal](experiments/geometry-removed/): Seen 22/80, Unseen 17/80; **39/160**.
- [x] [E06 · No task progress and agent success](experiments/agent-check-success/): Seen 18/80, Unseen 11/80; **29/160**.
- [x] [E07 · NoMemory](experiments/no-memory/): Seen 24/80, Unseen 17/80; **41/160**.
- [x] [E08 · Combined information removal, Planner pose coordinates provided](experiments/no-privileged-info/): Seen 27/80, Unseen 14/80; **41/160**.
- [x] [E09 · Combined information removal, Planner pose coordinates withheld](experiments/no-planner-pose/): Seen 17/80, Unseen 10/80; **27/160**.

- [x] [E10 · VLM task progress + native success](experiments/vlm-progress-native-success/): Seen 26/80, Unseen 18/80; **44/160**.

The 1,600-episode total excludes the auxiliary Sol run and interrupted smoke runs.
E05 removes the two active geometry-query tools; internal depth and other feedback
remain. E06 completes removal of live task-progress/success/termination feedback
and VLA native-success early stopping; the evaluator keeps independent final
scoring. Visual or tactile contact estimation remains pending. E10 completes a four-view visual task-progress run with native
completion feedback; visual judgment reliability remains an open issue.
E08 provides robot EEF/base pose coordinates to the Planner; E09 withholds them
and also removes gripper-width, held_apart and action-execution statistics.
Both retain VLA/controller proprioception and native-success early stopping.

## Published experiment code

Repository: [https://github.com/snow-QingYang/RPent](https://github.com/snow-QingYang/RPent). Machine-readable mapping: [source-publication.json](source-publication.json).

| Experiment | Branch | Immutable commit | Instructions |
| --- | --- | --- | --- |
| E01 · Baseline | [baseline_composite](https://github.com/snow-QingYang/RPent/tree/baseline_composite) | [eebdfcd7](https://github.com/snow-QingYang/RPent/commit/eebdfcd79b6f292003093be5dd1ce8fe639a4f82) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/eebdfcd79b6f292003093be5dd1ce8fe639a4f82/EXPERIMENT.md) |
| E02 · DA3 深度替代 | [da3](https://github.com/snow-QingYang/RPent/tree/da3) | [bc35d937](https://github.com/snow-QingYang/RPent/commit/bc35d93728e3678404b63f9cc78e5e98764dbbb7) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/bc35d93728e3678404b63f9cc78e5e98764dbbb7/EXPERIMENT.md) |
| E03 · No task progress | [no_task_progress](https://github.com/snow-QingYang/RPent/tree/no_task_progress) | [b7333814](https://github.com/snow-QingYang/RPent/commit/b7333814fcb1178442057b231e267d4dcfba4554) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/b7333814fcb1178442057b231e267d4dcfba4554/EXPERIMENT.md) |
| E04 · 接触反馈移除，完整进度 | [no_contact_gt](https://github.com/snow-QingYang/RPent/tree/no_contact_gt) | [092d8b8d](https://github.com/snow-QingYang/RPent/commit/092d8b8d344a7a0b2f8b6d5dd3bfae6a81342804) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/092d8b8d344a7a0b2f8b6d5dd3bfae6a81342804/NO_CONTACT_GT.md) |
| E05 · 几何查询移除 | [no_geometry_tools](https://github.com/snow-QingYang/RPent/tree/no_geometry_tools) | [19a9ea93](https://github.com/snow-QingYang/RPent/commit/19a9ea934810999428715324507021db51ec06bf) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/19a9ea934810999428715324507021db51ec06bf/NO_GEOMETRY_TOOLS.md) |
| E06 · No task progress and agent success | [no_task_progress_and_agent_success](https://github.com/snow-QingYang/RPent/tree/no_task_progress_and_agent_success) | [412efe9c](https://github.com/snow-QingYang/RPent/commit/412efe9c32e3cac630c77138da86def960968610) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/412efe9c32e3cac630c77138da86def960968610/EXPERIMENT.md) |
| E07 · NoMemory | [no_memory](https://github.com/snow-QingYang/RPent/tree/no_memory) | [a640f320](https://github.com/snow-QingYang/RPent/commit/a640f3202d092b0803540dff35521f7996ce0945) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/a640f3202d092b0803540dff35521f7996ce0945/EXPERIMENT.md) |
| E08 · Combined removal · Planner pose provided | [no_privileged_info_with_planner_pose](https://github.com/snow-QingYang/RPent/tree/no_privileged_info_with_planner_pose) | [5e612e91](https://github.com/snow-QingYang/RPent/commit/5e612e916c011bcc76431efd1775040f86563fef) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/cb24eb7c8664e46e6ca50497cc9f77e23282ebea/EXPERIMENT.md) |
| E09 · Combined removal · Planner pose withheld | [no_privileged_info_no_planner_pose](https://github.com/snow-QingYang/RPent/tree/no_privileged_info_no_planner_pose) | [f2d62d21](https://github.com/snow-QingYang/RPent/commit/f2d62d21104f412b5e020931d11d7054b6ef3818) | [Run instructions](https://github.com/snow-QingYang/RPent/blob/f2d62d21104f412b5e020931d11d7054b6ef3818/EXPERIMENT.md) |

E03 immutable commit `b7333814` is the evaluated snapshot: all 350 archived tracked
runtime, test, requirements and pyproject files match. All 160 episodes generated
`success_criteria.md`, while the file tool restricted reads to selected memory.

The later variant [no_task_progress](https://github.com/snow-QingYang/RPent/tree/no_task_progress), commit [26d8665d3d394dc77ce90a68d266d370d2384f98](https://github.com/snow-QingYang/RPent/commit/26d8665d3d394dc77ce90a68d266d370d2384f98), also stops generating that file. It was not used for the published E03 result.

Nine published experiment settings have nine primary branch links. E08's evaluated
commit remains [5e612e91](https://github.com/snow-QingYang/RPent/commit/5e612e916c011bcc76431efd1775040f86563fef); publication commit
[cb24eb7c](https://github.com/snow-QingYang/RPent/commit/cb24eb7c8664e46e6ca50497cc9f77e23282ebea) changes only `EXPERIMENT.md` to clarify
that Planner pose coordinates are provided. Its runtime implementation is unchanged.
E09's published and evaluated commit is [f2d62d21](https://github.com/snow-QingYang/RPent/commit/f2d62d21104f412b5e020931d11d7054b6ef3818).
The E03 branch also contains a later variant; use its immutable evaluated commit
for the 160-episode result.

Publication commits may include documentation or launch instructions added after
evaluation. Runtime source-file, patch and result hashes remain unchanged in each
analysis export. Branch tips may move; immutable commit links identify this release.

## Page hierarchy

- `index.html`: research objective, current work, completed results, next steps.
- `experiments/index.html`: experiment catalog with completed and partial work separated.
- `experiments/baseline/`: E01, current Astra rerun, 55/160.
  - `analysis/`: detailed 320-episode Astra / Sol analysis, data, CSV, report,
    extractor, and all individual JSON evidence. The Sol run remains an auxiliary
    reference; its different memory profile prevents a pure model ablation.
  - `cases/`: case directory.
  - `cases/pan-transfer-success/`: rerun seed 3, 90 calls, 183 images,
    60 environment actions and the original continuous 270.80-second video.
  - `cases/pan-transfer-failure/`: rerun seed 1, 53 calls, 84 images,
    27 environment actions and the original continuous 340.95-second video.
- `experiments/geometry-da3/`: E02, 50/160, compared to E01's 55/160.
  - `analysis/`: all 160 matched pairs, initial-state audit, CSV, JSON and extractor.
  - `cases/`: two paired-outcome examples (PanTransfer seed 3 and
    SetUpCuttingStation seed 4). These pages are result comparisons, not DA3 video
    replays. Each includes source hashes and links to baseline evidence.
- `experiments/task-progress/`: E03, completed No task progress run, 41/160.
  - `analysis/`: Seen 24/80 and Unseen 17/80; all 160 matched pairs against
    E01's 55/160 rerun, initial-state and memory audits, CSV, JSON, report and
    a portable extractor. The old 53/160 baseline is a separate historical
    reference. It is not the primary comparison displayed on the site.
  - `cases/setup-cutting-station-s3/`: interrupted configuration-mismatch smoke
    run, 22 completed calls and 11 observations, 0 live task_progress fields.
    Actual geometry was DA3, while the requested setting was original depth.
    No result.json; do not label this episode successful or failed or include it
    in the benchmark denominator. Direct file checks are not Agent calls.
- `experiments/contact-feedback/`: E04, full native task progress retained, 44/160.
  - `analysis/`: Seen 29/80, Unseen 15/80; 160 task/seed pairs against E01,
    current native-score and memory audits, CSV, JSON, report and extractor.
    Baseline reference uses existing public exports; full initial states were not compared.
  - `downloads/`: all 160 results/native states/memory audits, production source and analysis ZIP.
  - `archive/`: old 46/160 filtered-progress result and original 13 published files.
    `cases/` explicitly labels its examples as historical, not current E04 evidence.
- `experiments/geometry-removed/`: E05, completed NoGeomTools run, 39/160.
  - `analysis/`: Seen 22/80 and Unseen 17/80; all 160 matched pairs against
    E01's 55/160, task/seed filters, native-success and memory checks,
    initial-state comparison, tool-call audit, CSV, JSON and portable extractor.
  - The experiment page compares original geometry, DA3 replacement and removal
    of the two geometry query tools. It does not claim all depth or geometry
    information was removed from the simulator or the agent's other channels.
- `experiments/agent-check-success/`: E06, completed No task progress and agent success run, 29/160.
  - `analysis/`: Seen 18/80 and Unseen 11/80; native final scores and Agent
    declarations for all 160 episodes, with E01/E03 comparisons.
  - 134 episodes call `finish`, 26 return without it. Of 43 success claims,
    28 match the native score and 15 are false positives. WaffleReheat seed 4
    succeeds natively without `finish`; native scores, not claims, give 29/160.
- `experiments/no-memory/`: E07, completed historical-memory removal, 41/160.
  - `analysis/`: Seen 24/80 and Unseen 17/80; all 160 matched outcomes against
    E01, task/seed filters, CSV, JSON, report and portable extractor.
  - Current-episode history and baseline simulator feedback remain. E03 has
    the same aggregate score but is a separate setting.
- `experiments/no-privileged-info/`: E08, combined information removal with
  Planner pose coordinates provided, 41/160 (Seen 27/80, Unseen 14/80).
  - `analysis/`: all 160 outcomes against E01 and E05, success-path filters,
    initial-state comparisons, context audit, JSON, CSV, report and extractor.
  - The scope and camera tables distinguish Agent-visible information, removed
    outputs and internally retained artifacts. Source branch and evaluated commit are linked above.
- `experiments/no-planner-pose/`: E09, combined information removal with
  Planner pose coordinates withheld, 27/160 (Seen 17/80, Unseen 10/80).
  - `analysis/`: all 160 outcomes against E08 and E01, JSON, CSV and report.
  - E09 also removes gripper width, held_apart, motion feedback and action
    execution status/steps/timing; it is not a pose-only ablation.
  - Native simulator success and early stopping, VLA/controller proprioception,
    RGB, task language and current-episode history remain. Published source and run instructions are linked above.
- `reference/`: information categories, existing detailed ground-truth access
  guide, and the self-contained original method reference.
- `project-status.json`: provenance and structured snapshot for the overview.
- `source-publication.json`: published branch/commit mapping, including E03 version notes.

## Interpretation

DA3 only replaces depth for back_project_batch and query_world_map. Known camera
calibration/pose, robot state, task progress, interaction feedback, success,
scoring-source access and memory remain. The current paired batches have 14
robot-state, five task-text and three initial-progress differences. They are not
proof of identical scenes or a causal per-episode attribution.

The completed No task progress run uses original simulator depth. It hides task_progress
from Agent observations, restricts read_text_file to memory files, and updates
the corresponding prompt instructions. Success, termination, grasp/contact
feedback, native scoring and VLA early stopping remain. This setting combines
progress removal and file-access restrictions; it is not a pure task_progress
ablation or a ground-truth-free system. The 95 selected memory files match E01's
recorded hashes. Ten paired initial robot states and four task descriptions
differ; the audit does not establish identical complete scenes. The historical
DA3 smoke remains separate from the 160 valid episodes.

E04 now removes only four explicit VLA grasp/contact reports and their wrapper
queries. All native task_progress remains, including contact-derived conditions.
The 2026-11-14 batch is 44/160: Seen 29/80, Unseen 15/80, versus E01 55/160.
The evaluated commit is 092d8b8d344a7a0b2f8b6d5dd3bfae6a81342804 on no_contact_gt.
All 160 results match native final state and have exit0. The scan covers 4,343
observations and 1,869 VLA action records; four removed labels have zero occurrences.
Three interrupted VLA action records are retained within normally completed episodes.
All 493 frozen source and 148 original memory hashes match. There are three task-text
differences against published E01; robot/full-scene initial equality was not audited.
Do not reuse the old E04 initial-state, memory-selection or case metrics.
The old 46/160 batch additionally filtered 60 progress entries across 25 tasks;
its original public snapshot is preserved in archive/, outside the current denominator.

NoGeomTools removes back_project_batch and query_world_map from the registered
Agent tools and removes their instructions from the evaluation prompt and view
tool description. It retains simulator depth/world-map generation, robot state,
task_progress including distances, contact feedback, success, native scoring,
VLA execution, baseline file permissions and historical memory. It is independent
of E02/E03/E04. The paired result is 23 both-success, 32 baseline-only,
16 NoGeomTools-only and 89 both-failure episodes, for a net decrease of 16/160
(10 percentage points). The run finished on 2026-11-06 at 00:51 Hong Kong time.
Its scheduler resumed on eight GPUs after initially running on six; completed
valid episodes were preserved. See the detailed export for audit scope and
initial-state differences. Removing registered tools is not filesystem isolation.

No task progress and agent success is based on No task progress commit `26d8665`. It hides ordinary
observation fields `success`, `robocasa_terminated` and `task_progress`, removes
native-success VLA early stopping and does not generate `success_criteria.md`.
Geometry, contact feedback and historical memory remain. Final native scoring
runs after the planner returns, independently of the Agent's `finish` declaration.
Private predicate bookkeeping and state records remain; this is not a sandbox.
The experiment is evaluation-only and has no added actuator guard after `finish`.
The result schema retains the legacy `agent_stop` variant for compatibility;
the display name is "No task progress and agent success"; the published branch
is `no_task_progress_and_agent_success`; the earlier `agent_check_success` branch is retained.
The run completed on 2026-11-07 at 19:26 Hong Kong time. Source:
[no_task_progress_and_agent_success branch](https://github.com/snow-QingYang/RPent/tree/no_task_progress_and_agent_success),
published commit `412efe9c` (runtime implementation `65f7e1b`). Compared with E01 it has 26 fewer native successes; compared
with E03 it has 12 fewer. These totals do not establish per-episode causality.

NoMemory starts from the official baseline and removes historical task/global
memory selection, prompt exposure and permission to read memory files through
the file tool. It retains current-episode history, geometry, contact feedback,
task progress, success, scoring-source access and VLA native-success early
stopping. All 160 result records pass the no-memory validator. The recorded-trajectory
audit covers 337,744 events and 364 native shell commands across 84 episodes;
no historical task/global memory read attempt was observed. Source/AGENTS and
current-episode artifact reads occurred. The harness still validates the corpus
internally before returning an empty selection; this is not OS isolation. Source is official
`a744bd5` plus the recorded three-file experiment patch, published as
[no_memory](https://github.com/snow-QingYang/RPent/tree/no_memory), commit [a640f3202d092b0803540dff35521f7996ce0945](https://github.com/snow-QingYang/RPent/commit/a640f3202d092b0803540dff35521f7996ce0945).
All ten recorded runtime source-file hashes match; tests and documentation are
additional publication artifacts. It finished on 2026-11-09 at 08:57
Hong Kong time. The launcher logged a trailing shell EOF after all episodes
and validation completed; an independent post-run validator passed all 160.
The saved runner exit marker alone is not proof of clean shell termination.

The success/failure replay HTML embeds the original video, raw records, images,
prompt, all tool calls and full returns. Original data stays byte-identical during
this reorganization. Video boundaries are reconstructed from step counts and
verified returned images, not original per-frame tool timestamps. Empty reasoning
remains empty; runtime files are distinguished from files the Agent actually read.

## E08 · Planner pose coordinates provided

E08 combines geometry-query, historical-memory, task-progress and contact-label
removal while keeping native simulator success and early stopping. It also stops
generating success_criteria.md and denies RPent text-file reads. RGB, task language,
robot EEF/base poses, gripper state, current-episode history, VLA and manual motion
controllers remain. move_to still uses simulator robot proprioception for servo
control; this is not removal of all simulator state.

The Planner sees agentview (the left observation camera), navview (base camera)
and wrist RGB, with names and qualitative roles. It receives no numeric camera
intrinsics, extrinsics/pose or FOV. The calibration_frame role is only a label.
The VLA uses 256×256 left/right/wrist RGB, a different three-view selection.
Depth, world maps, camera metadata and the floor overlay are generated internally;
depth/world-map NPZ files use the existing 25-step retention window. RGB PNGs and
camera metadata are not pruned by this window. The recorded Agent
trajectories did not read these artifacts. These restrictions are
not an operating-system sandbox.

All 160 results passed validation; 4,632 completed tool returns and 4,327 stored
states were audited without removed progress/contact fields. Geometry-query,
file-read and native shell calls were all zero. All 41 successes match saved
native success. Of those successes, 22 use only VLA actions and 19 include manual
intervention; 13 of the latter still finish through VLA, six through a manual
step. Every successful episode used VLA. These are trajectory categories, not
proof of manual causation.

The 41/160 score is two above E05's 39/160, with 18 added and 16 lost successes.
Among 132 strictly matching initial observations, the diagnostic totals are
31/132 versus 32/132. That selected subset is not a replacement benchmark score.
Some same-seed initial conditions differ, and VLA inference samples noise; one
batch per configuration does not establish an improvement from removing more
information. The run completed on 2026-11-10 at 06:07 Hong Kong time.

## E09 · Planner pose coordinates withheld

E09 builds on E08 and hides robot EEF/base poses, robot-motion feedback, gripper
width, held_apart and action execution status, steps and timing from the Planner.
Both E08 and E09 keep RGB, task language, current-episode interaction history,
native simulator success, native-success early stopping and internal robot
proprioception used by VLA and the motion controllers. Withheld Planner poses do
not mean that the VLA is deprived of its normal robot-state input.

The completed run is **27/160 (16.875%)**, with Seen **17/80** and Unseen **10/80**.
E08 remains a separate **41/160** result (Seen 27/80, Unseen 14/80). The difference
is 14 successes, or 8.75 percentage points; multiple feedback fields changed,
and independent runs can have different initial states and action samples, so
this result does not isolate the causal effect of pose coordinates. The original
baseline is 55/160 (Seen 34/80, Unseen 21/80).

E09 completed on **2026-11-12 at 01:57:18 Hong Kong time**. Its run identifier is
`official_main_composite_no_planner_feedback_astra_xhigh_20261110T055737Z`.
The public name distinguishes Planner pose exposure; the run identifier retains
its original no_planner_feedback wording. E08 data and provenance remain intact.

The final audit checked all 160 accepted episodes and 640 logs. Across 4,353
completed MCP returns, the 43 checked hidden-feedback fields had zero occurrences;
geometry-query, file-read and native-command calls were zero. Two saved cancellation
markers at the planner budget limit are documented separately from completed
returns. The audit covers recorded boundaries, not operating-system isolation.

## Maintenance

The NoMemory export reads `source-publication.json` (or `--source-publication`)
so regenerated data and reports retain the published branch and commit. Keep this
mapping consistent with the homepage code table, experiment pages and status JSON.

`../organize_ground_truth_site.py` (relative to site-publish) creates the overview,
catalogs, short experiment pages, comparison examples, smoke audit summary and
compatibility pages. It uses the existing detailed exports and the original local
smoke audit. Its assertions intentionally require review if source results change.
Canonical detailed exports live under their experiment's `analysis/` directory.
The legacy overview generator predates E06–E10. Do not use it to regenerate the
current overview or project-status.json until it supports E06–E10: it would restore
the older five-group checklist and drop the newer entries. After adding that support,
verify the ten-group, 1,600-episode total whenever rebuilding a detailed export
and the overview. The E03, E04 and E05 detailed HTML and JS
use the same table/filter layout as E02; check their displayed summaries against the
new export when changing source runs.
The historical E04 case builder used the local six-case audit under
`analyses/nocontact_unseen_gains_20261104/`. It published only selected evidence
fields and images; incomplete snapshot totals and local server paths are omitted.
Replay builder source is `presentations/rpent-interaction-record/` in the local
workspace; pass the new canonical output directory when rebuilding.

Old HTML URLs `/analysis/`, `/geometry-da3/`, `/pan-transfer/`,
`/pan-transfer-failure/`, `/pan-transfer-full/`, `methods.html` and
`perception-method-plan.html` forward to the corresponding canonical page,
preserving query strings and hashes. Main CSV/JSON/report/extractor download URLs
are retained as compatibility copies. Per-episode JSON lives under E01.

`codex-token-cost-plan.html` is an older, unlinked proposal. It is not part of the
current experiment results. The local-only expanded ground-truth and real-robot
planning documents have not been published here.

To remove this deployment, delete only `mobile-astra/`, commit and push. No shared
navigation, assets or templates need cleanup. The separate historical
`snow-QingYang/astra-robocasa-replay` repository is unaffected.

## E10 · VLM task progress with native success

Completed 2026-11-13 15:13:19 UTC+8: **44/160**, Seen **26/80**, Unseen **18/80**.
Astra / xhigh retains original memory, geometry/contact tools and native success.
Terra / medium supplies cached four-camera visual condition judgments. Native
success stops VLA calls and authorizes finish(success); final scoring is native.

All 160 results match final recorded native state; memory audits pass. All 44
successes call finish(success) without additional actions after the first recorded
success. In 41 of them the final VLM judgment does not confirm completion.
4059 VLM request audits include 9 API errors; 6 more observations were cancelled
before requesting a judgment. Those valid failed episodes remain in the denominator.

The overview, interactive 160-pair analysis, a real video/four-camera case, CSV,
JSON, report, portable extractor and downloadable result/audit ZIP live under
`experiments/vlm-progress-native-success/`. The public ZIP includes all native
states, results, memory audits, VLM judgments/request audits and production source.
The separately delivered full local ZIP also retains saved RGB, videos, depth/world
maps, raw Planner traces and logs. Credentials, worker configuration and downloaded
weights/memory corpus are excluded. ZIP member and archive SHA-256 checks are supplied.

E10 is +3 successes against E03 and -11 against baseline. Task/seed pairing
is provided for both existing references. Initial-state equality against these
references was not fully audited, and VLA random samples were not fixed.
Fixed condition knowledge and extra model compute are additional differences
against E03. This update publishes only the native-success E10 batch.

E10 source is a frozen working tree based on `fee5dfac` plus recorded changes.
The branch has not been separately published. `source-publication.json` tracks
10 experiments but still 9 published branches; E10 has `snapshot_available` status.
Do not label the base commit as the evaluated implementation or link to a nonexistent
published branch. Keep the 9 pre-existing experiment entries and their artifacts intact.

## E04 replacement maintenance

The current E04 extractor reads the completed dynamic controller state and the
original run manifest separately. The original three-GPU manifest was superseded
by dynamic scheduling; do not infer incompletion from that historical marker.
Never regenerate current E04 from the old filtered-progress source or old case builder.
The main experiment count remains ten and the current valid-episode total remains
1,600; the historical E04 archive is not an eleventh experiment.
