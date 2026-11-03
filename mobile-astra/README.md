# Mobile Astra deployment

Direct URL: https://snow-qingyang.github.io/mobile-astra/

This directory is only a deployment location. Its pages must use their own standalone work interface, with no personal-site avatar, name, background, navigation, footer, CSS, or JavaScript. Do not add links to it from the main website navigation, Home, Research, Blog, or generated-page templates.

- `index.html`: direct-link landing page.
- `geometry-da3/`: DA3 geometry experiment (50/160) compared with the November 1–2 Astra rerun (55/160), by task and seed. Includes split summaries, 160 pairs, CSV, JSON, source hashes and extractor. Initial-state checks flag 14 robot-state differences above 1e-6, five task-text differences and three progress differences; identical task/seed does not guarantee identical scenes. This only replaces depth for the two geometry queries; other simulator information remains available.
- `analysis/`: Astra rerun (55/160) and existing GPT-5.6-Sol run (45/160), 320 canonical episodes with split success paths, per-case evidence, CSV, Markdown and extractor. Astra successes: 19 VLA only, four preparation then VLA, 32 with intervention after VLA. Keep the memory-profile and scene-comparability caveats.
- `pan-transfer/`: complete successful interaction from the rerun, PanTransfer seed 3. Contains the original prompt, 94 public agent messages, all 90 method calls and full returns, 183 images, 3,337 raw events, and the original continuous 270.80-second video. 13 VLA calls and 47 analytic actions; first success at action 60. All 60 action endpoints checked against returned images.
- `pan-transfer-failure/`: complete failed interaction from the same rerun, PanTransfer seed 1. Contains 62 public agent messages, all 53 method calls, 84 images, 2,053 raw events and the original continuous 340.95-second video. 21 VLA calls and six analytic actions; all 27 action endpoints checked. No observation reports success; the agent ends with stuck after multiple recovery attempts.
- `pan-transfer-full/`: compatibility redirect to the updated successful full interaction at `pan-transfer/`.
- Both replay HTML files are standalone with embedded raw records and original video. Downloaded source files retain SHA-256 hashes. Frame boundaries are reconstructed from step counts and verified images, not logged per-frame tool timestamps; underlying action vectors are not invented. Empty reasoning events remain empty. Runtime files are distinguished from files the agent actually read.
- `methods.html`: self-contained tool reference.
- `perception-method-plan.html`: ground-truth access reference, including robot state, geometry, grasp/motion feedback, task criteria and scoring rules. Its example now points to rerun PanTransfer seed 3 (61 observations).

These published copies do not depend on local experiment directories or running servers. To remove this deployment later, delete `mobile-astra/`, commit, and push. No shared navigation, styles, or assets need to be removed.

The URL is publicly accessible to anyone who has it; absence of navigation is not access control. The older `snow-QingYang/astra-robocasa-replay` repository is separate and unchanged.
