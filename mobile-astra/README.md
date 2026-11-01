# Mobile Astra deployment

Direct URL: https://snow-qingyang.github.io/mobile-astra/

This directory is only a deployment location. Its pages must use their own standalone work interface, with no personal-site avatar, name, background, navigation, footer, CSS, or JavaScript. Do not add links to it from the main website navigation, Home, Research, Blog, or generated-page templates.

- `index.html`: direct-link landing page.
- `analysis/`: two-run RoboCasa report, 320 manifest episodes, per-case action evidence, CSV, Markdown, and reproducible extraction script. Read only canonical result/states/transcript files; do not count archived attempts or substitute the reference screenshot's Baiyajing statistics. Attribution is observational and must retain the memory-profile caveat.
- `baiyajing-analysis/`: separate 160-episode Baiyajing report from the canonical `baiyajing_composite_8gpu_20261022` manifest. GPT-6-Sol / medium: 28 initial full-task VLA successes, 33 planner-stage successes (20 vla/pick programs, 13 with explicit control), 99 failures. Keep plan output, executed steps, automatic fallback, attempt records, and final environment success distinct. The executor includes automatic control inside vla/pick; this is not a model-only comparison with the RPent runs. Local 61/160 and repository-reported 59/160 must remain separate.
- `baiyajing-replay/?case=success` and `?case=failure`: GetToastedBread seeds 5 and 3, each with two Planner outputs. Publishes all 8 original VLA clips, associated attempt snapshots, planner input images, final observations, and the actual programs/step results. The replay now uses the same continuous player, chapters, search/filter controls, and synchronized expandable timeline as the PanTransfer pages. The composed videos are 86.0 s and 89.2 s, with each planner-observation, missing-video, and final-result card explicitly labelled and held for four presentation seconds. These card durations are not original wall-clock time. The source recorder only captures VLA actions; carry, put_down, preparation and lift/retract lack continuous video. Never fill those gaps with unrelated frames or label a grasped attempt as global success. Seed 5 succeeds after put_down; seed 3 loses the bread during the carry step and replans to unrecoverable=true. Build script validates frame naming order, media frame counts, and source hashes.
- `methods.html`: self-contained tool-call reference.
- `pan-transfer/`: replay page with all videos, JSON, and images.
- `pan-transfer-failure/`: Astra PanTransfer seed 1 failure, 34 tool calls, 12 VLA calls, 4 analytic actions (3 preparation, 1 after VLA), original video and camera images. The task remains unsuccessful throughout; do not label completed tool calls as task success.

These published copies do not depend on local experiment directories or running servers. To remove this deployment later, delete `mobile-astra/`, commit, and push. No shared navigation, styles, or assets need to be removed.

The URL is publicly accessible to anyone who has it; absence of navigation is not access control. The older `snow-QingYang/astra-robocasa-replay` repository is separate and unchanged.
