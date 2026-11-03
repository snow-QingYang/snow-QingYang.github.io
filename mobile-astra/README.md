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
- `experiments/task-progress/`: E03, partial audit only; no valid benchmark result.
  - `cases/setup-cutting-station-s3/`: interrupted configuration-mismatch smoke
    run, 22 completed calls and 11 observations, 0 live task_progress fields.
    Actual geometry was DA3, while the requested setting was original depth.
    No result.json; do not label this episode successful or failed or include it
    in the benchmark denominator. Direct file checks are not Agent calls.
- `reference/`: information categories, existing detailed ground-truth access
  guide, and the self-contained original method reference.
- `project-status.json`: provenance and structured snapshot for the overview.

## Interpretation

DA3 only replaces depth for back_project_batch and query_world_map. Known camera
calibration/pose, robot state, task progress, interaction feedback, success,
scoring-source access and memory remain. The current paired batches have 14
robot-state, five task-text and three initial-progress differences. They are not
proof of identical scenes or a causal per-episode attribution.

The progress-removal smoke run retains success and historical memory. Its file
allowlist additionally restricts scoring-source access: a future single-variable
comparison must match file permissions or separately disclose that intervention.
The smoke audit does not validate a full experiment or a ground-truth-free system.

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
