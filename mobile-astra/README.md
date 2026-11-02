# Mobile Astra deployment

Direct URL: https://snow-qingyang.github.io/mobile-astra/

This directory is only a deployment location. Its pages must use their own standalone work interface, with no personal-site avatar, name, background, navigation, footer, CSS, or JavaScript. Do not add links to it from the main website navigation, Home, Research, Blog, or generated-page templates.

- `index.html`: direct-link landing page.
- `pan-transfer-full/`: self-contained Astra PanTransfer seed 2 interaction record. Includes the original initial prompt, all 79 tool calls with full arguments and returns, 77 public agent messages, 147 returned images, the continuous episode video, and all 2,379 raw stream events. Downloads preserve source-file SHA-256 hashes. Distinguishes actual context from merely existing artifacts, retains the original memory truncation, and does not invent reasoning or per-simulator-step action logs. Video alignment uses the previously verified PanTransfer frame boundaries. The entry appears only on this Mobile Astra landing page.
- `analysis/`: two-run RoboCasa report, 320 manifest episodes, per-case action evidence, CSV, Markdown, and reproducible extraction script. Read only canonical result/states/transcript files from the official RPent runs; do not count archived attempts. Attribution is observational and must retain the memory-profile caveat.
- `methods.html`: self-contained tool-call reference.
- `pan-transfer/`: replay page with all videos, JSON, and images.
- `pan-transfer-failure/`: Astra PanTransfer seed 1 failure, 34 tool calls, 12 VLA calls, 4 analytic actions (3 preparation, 1 after VLA), original video and camera images. The task remains unsuccessful throughout; do not label completed tool calls as task success.

These published copies do not depend on local experiment directories or running servers. To remove this deployment later, delete `mobile-astra/`, commit, and push. No shared navigation, styles, or assets need to be removed.

The URL is publicly accessible to anyone who has it; absence of navigation is not access control. The older `snow-QingYang/astra-robocasa-replay` repository is separate and unchanged.
