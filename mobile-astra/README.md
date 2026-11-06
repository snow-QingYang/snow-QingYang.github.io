# HarnessVLA ground-truth study / Mobile Astra

Public work page: https://snow-qingyang.github.io/mobile-astra/

Keep this deployment entirely inside `mobile-astra/`. Do not modify or link from
personal Home, Research, Blog, shared navigation, styles, assets or templates.
All pages are standalone work interfaces. Public URLs are not access control.

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
- `experiments/task-progress/`: E03, completed NoTaskGT run, 41/160.
  - `analysis/`: Seen 24/80 and Unseen 17/80; all 160 matched pairs against
    E01's 55/160 rerun, initial-state and memory audits, CSV, JSON, report and
    a portable extractor. The old 53/160 baseline is a separate historical
    reference. It is not the primary comparison displayed on the site.
  - `cases/setup-cutting-station-s3/`: interrupted configuration-mismatch smoke
    run, 22 completed calls and 11 observations, 0 live task_progress fields.
    Actual geometry was DA3, while the requested setting was original depth.
    No result.json; do not label this episode successful or failed or include it
    in the benchmark denominator. Direct file checks are not Agent calls.
- `experiments/contact-feedback/`: E04, completed NoContactGT run, 46/160.
  - `analysis/`: Seen 26/80 and Unseen 20/80; all 160 pairs against E01,
    initial-state and memory audits, native-success checks, CSV, JSON, report
    and a portable extractor. One valid planner-timeout failure is included.
  - `cases/`: six selected Unseen gains, action comparisons, image montages,
    initial-image hashes and the earliest observed execution divergence.
    These examples do not establish that removing feedback caused improvement.
- `experiments/geometry-removed/`: E05, completed NoGeomTools run, 39/160.
  - `analysis/`: Seen 22/80 and Unseen 17/80; all 160 matched pairs against
    E01's 55/160, task/seed filters, native-success and memory checks,
    initial-state comparison, tool-call audit, CSV, JSON and portable extractor.
  - The experiment page compares original geometry, DA3 replacement and removal
    of the two geometry query tools. It does not claim all depth or geometry
    information was removed from the simulator or the agent's other channels.
- `reference/`: information categories, existing detailed ground-truth access
  guide, and the self-contained original method reference.
- `project-status.json`: provenance and structured snapshot for the overview.

## Interpretation

DA3 only replaces depth for back_project_batch and query_world_map. Known camera
calibration/pose, robot state, task progress, interaction feedback, success,
scoring-source access and memory remain. The current paired batches have 14
robot-state, five task-text and three initial-progress differences. They are not
proof of identical scenes or a causal per-episode attribution.

The completed NoTaskGT run uses original simulator depth. It hides task_progress
from Agent observations, restricts read_text_file to memory files, and updates
the corresponding prompt instructions. Success, termination, grasp/contact
feedback, native scoring and VLA early stopping remain. This setting combines
progress removal and file-access restrictions; it is not a pure task_progress
ablation or a ground-truth-free system. The 95 selected memory files match E01's
recorded hashes. Ten paired initial robot states and four task descriptions
differ; the audit does not establish identical complete scenes. The historical
DA3 smoke remains separate from the 160 valid episodes.

NoContactGT removes four VLA grasp/contact result fields and the corresponding
wrapper queries, plus 60 task/field entries across 25 tasks' contact-derived
progress. It retains the held_apart gripper-width heuristic, other progress,
geometry, success, native scoring, file access, memory and the baseline prompt.
It is independent of DA3 and NoTaskGT. All 148 launch memory hashes and 95 selected
files match E01. Eleven paired initial robot states differ above 1e-6 (17 differ
at exact precision), and two task descriptions differ. The 4,772-state output
scan does not establish isolation of all historical memory or shell/file channels.
Scene seeds do not fix independent VLA action sampling in this run; case-level
outcome flips cannot be attributed solely to contact-feedback removal.

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

The success/failure replay HTML embeds the original video, raw records, images,
prompt, all tool calls and full returns. Original data stays byte-identical during
this reorganization. Video boundaries are reconstructed from step counts and
verified returned images, not original per-frame tool timestamps. Empty reasoning
remains empty; runtime files are distinguished from files the Agent actually read.

## Maintenance

`../organize_ground_truth_site.py` (relative to site-publish) creates the overview,
catalogs, short experiment pages, comparison examples, smoke audit summary and
compatibility pages. It uses the existing detailed exports and the original local
smoke audit. Its assertions intentionally require review if source results change.
Canonical detailed exports live under their experiment's `analysis/` directory.
After regenerating a detailed export, rerun the overview generator to update
its experiment page and project-status.json. The E03, E04 and E05 detailed HTML and JS
use the same table/filter layout as E02; check their displayed summaries against the
new export when changing source runs.
The E04 case builder also uses the local six-case audit under
`analyses/nocontact_unseen_gains_20261104/`. It publishes only selected evidence
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
