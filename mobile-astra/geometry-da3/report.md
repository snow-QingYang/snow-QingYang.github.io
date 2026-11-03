# RoboCasa composite：模拟器深度与 DA3 深度

按任务、seed 对齐比较 160 局。Baseline 为 11 月 1–2 日 Astra 重跑批次；两组均为 GPT-6-Astra / xhigh。

| 分组 | Baseline | DA3 | DA3 − Baseline |
|---|---:|---:|---:|
| Seen | 34/80（42.50%） | 33/80（41.25%） | -1.25 pp |
| Unseen | 21/80（26.25%） | 17/80（21.25%） | -5.00 pp |
| 全部 | 55/160（34.38%） | 50/160（31.25%） | -3.13 pp |

配对结果：双方成功 33 局，仅 Baseline 成功 22 局，仅 DA3 成功 17 局，双方失败 88 局。

Baseline 批次：`composite_main_astra_rerun_20261101T150450Z`；DA3 批次：`composite_da3_astra_20261103`。
初始状态核对：14 对机器人状态最大绝对差超过 1e-6；5 对任务文本不同，3 对初始任务进度不同。这些检查不覆盖全部场景物体；相同 seed 不保证场景完全一致，不能将全部差异归因于深度替换。

本实验仅将 `back_project_batch` 与 `query_world_map` 的几何来源替换为 DA3METRIC-LARGE 从 RGB 估计的米制深度。相机内参 K 与相机位姿仍为已知的模拟器数据；其他真值接口、任务进度与成功反馈、VLA 输入和权重、记忆、提示词与控制流程保留 baseline 设置。因此这是深度来源替换实验，并非完全无真值实验。

配置：Seen / Unseen 各 16 个任务，seeds 1–5；相同的 GPT_6_astra_high 初始记忆；每局最多 100 个模型响应、3600 秒；RLDX 每次最多 40 chunks × 8 steps，settle patience 999。

成功来自环境 `state.success`。320 个 canonical result.json 均有效，并与各自 states.json 交叉核对；归档、中断尝试不计入。CSV 与 JSON 包含 160 条配对记录及源文件 SHA-256。

每个设置仅运行一轮。上述差异是这两批相同任务与种子的观察结果，不能据此认定稳定收益或显著退化。

复现：运行 `extract.py --baseline-run <baseline目录> --da3-run <DA3目录> --manifest <target50.json> --output <输出目录>`。
