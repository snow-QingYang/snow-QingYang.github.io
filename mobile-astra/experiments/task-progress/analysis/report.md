# E03 · No task progress

按相同任务与 seed 比较 160 局。主比较使用网站当前的 11 月 1 日 GPT-6-Astra 重跑 baseline（55/160），两组均为 xhigh。

| 分组 | Baseline | No task progress | No task progress − Baseline |
|---|---:|---:|---:|
| Seen | 34/80（42.50%） | 24/80（30.00%） | -12.50 pp |
| Unseen | 21/80（26.25%） | 17/80（21.25%） | -5.00 pp |
| 全部 | 55/160（34.38%） | 41/160（25.63%） | -8.75 pp |

| 配对结果 | Seen | Unseen | 全部 |
|---|---:|---:|---:|
| 双方成功 | 14 | 10 | 24 |
| 仅 Baseline 成功 | 20 | 11 | 31 |
| 仅 No task progress 成功 | 10 | 7 | 17 |
| 双方失败 | 36 | 52 | 88 |

## 实际设置

No task progress 使用官方原始模拟器几何，未使用 DA3。`view_env_state` 及动作后的模型观测不返回 `task_progress`；`read_text_file` 限于当前允许的记忆文件，不能通过该工具读取`success_criteria.md` 或评分源码；prompt 中要求读取进度与评分规则的说明也相应修改。

顶层 `success`、`robocasa_terminated`、原生成功判定及 VLA 成功提前停止仍保留。几何工具、接触反馈、VLA 输入与权重、动作执行流程保持官方设置。这是移除任务进度与规则读取的实验，不是完全无真值实验。内部 states.json 仍可保存模拟器进度用于记录；本报告不导出这些进度值。

匹配配置：GPT-6-Astra / xhigh；RLDX-1-FT-RC365；Seen / Unseen 各 16 个任务、seeds 1–5；每局最多 100 个模型响应、3600 秒；每次 VLA 最多 40 chunks × 8 steps，settle patience 999。两组均使用 local / GPT_6_astra_high、同任务与全局记忆。

160 对结果的记忆选择完全相同；涉及 95 个唯一文件，均与 baseline 启动时保存的 SHA-256 一致。实际读取顺序由 agent 决定。

## 初始状态与结果核对

初始机器人状态最大绝对差超过 1e-6 的有 10 对；初始任务文本不同的有 4 对。只比较 step 0 的 robot state 与 task_language；不比较 task_progress，也不将模型观测中缺少该字段判为场景差异。机器人状态与任务文本不能覆盖所有场景物体，这些配对只是同任务与 seed，不保证所有布局完全相同。

主比较的 320 个 canonical result.json 均有效，并与各自 states.json 的原生成功信号核对。归档和中断尝试不计入。JSON 与 CSV 包含 160 对逐 seed 结果、耗时和两侧结果/状态文件 SHA-256；不包含原始轨迹、模型提示词或凭证。

## 与旧 baseline 的关系

10 月 28 日旧 baseline 为 53/160（33.13%）；No task progress 为 41/160，相差 -12 局、-7.50 个百分点。该旧批次仅作参考，页面主表与逐 seed 配对始终使用 11 月 1 日 55/160 批次。

## 逐任务结果

每个 seed 单元格表示 `Baseline/No task progress`，1 为原生成功，0 为失败。

| 分组 | 任务 | Baseline | No task progress | s1 | s2 | s3 | s4 | s5 |
|---|---|---:|---:|---|---|---|---|---|
| Seen | ScrubCuttingBoard | 5/5 | 2/5 | 1/1 | 1/0 | 1/0 | 1/0 | 1/1 |
| Seen | StackBowlsCabinet | 5/5 | 3/5 | 1/1 | 1/0 | 1/1 | 1/0 | 1/1 |
| Seen | WashLettuce | 4/5 | 5/5 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 |
| Seen | RinseSinkBasin | 3/5 | 3/5 | 1/0 | 1/0 | 1/1 | 0/1 | 0/1 |
| Seen | PreSoakPan | 3/5 | 3/5 | 0/0 | 1/0 | 1/1 | 0/1 | 1/1 |
| Seen | StirVegetables | 2/5 | 1/5 | 0/0 | 0/0 | 1/0 | 0/1 | 1/0 |
| Seen | LoadDishwasher | 3/5 | 2/5 | 1/1 | 1/0 | 1/0 | 0/1 | 0/0 |
| Seen | SteamInMicrowave | 2/5 | 0/5 | 0/0 | 0/0 | 1/0 | 0/0 | 1/0 |
| Seen | SetUpCuttingStation | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | GetToastedBread | 1/5 | 0/5 | 0/0 | 1/0 | 0/0 | 0/0 | 0/0 |
| Seen | DeliverStraw | 1/5 | 1/5 | 0/0 | 0/0 | 1/1 | 0/0 | 0/0 |
| Seen | KettleBoiling | 1/5 | 3/5 | 1/0 | 0/1 | 0/0 | 0/1 | 0/1 |
| Seen | PrepareCoffee | 2/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 1/0 |
| Seen | StoreLeftoversInBowl | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | SearingMeat | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | PackIdenticalLunches | 2/5 | 1/5 | 0/1 | 0/0 | 0/0 | 1/0 | 1/0 |
| Unseen | ArrangeBreadBasket | 1/5 | 2/5 | 0/1 | 0/0 | 1/1 | 0/0 | 0/0 |
| Unseen | ArrangeTea | 1/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | BreadSelection | 3/5 | 2/5 | 1/1 | 0/0 | 1/1 | 1/0 | 0/0 |
| Unseen | CategorizeCondiments | 0/5 | 2/5 | 0/1 | 0/0 | 0/0 | 0/1 | 0/0 |
| Unseen | CuttingToolSelection | 2/5 | 1/5 | 1/1 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | GarnishPancake | 3/5 | 2/5 | 0/0 | 1/0 | 0/0 | 1/1 | 1/1 |
| Unseen | GatherTableware | 1/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | HeatKebabSandwich | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Unseen | MakeIceLemonade | 1/5 | 0/5 | 0/0 | 1/0 | 0/0 | 0/0 | 0/0 |
| Unseen | PanTransfer | 1/5 | 1/5 | 0/1 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | PortionHotDogs | 2/5 | 4/5 | 0/1 | 0/1 | 1/1 | 1/1 | 0/0 |
| Unseen | RecycleBottlesByType | 2/5 | 0/5 | 1/0 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | SeparateFreezerRack | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Unseen | WaffleReheat | 2/5 | 2/5 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 |
| Unseen | WashFruitColander | 2/5 | 0/5 | 1/0 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | WeighIngredients | 0/5 | 1/5 | 0/0 | 0/0 | 0/1 | 0/0 | 0/0 |

## 数据来源与复现

主 baseline：`official_main_composite_astra_xhigh_20261101T150450Z`。
No task progress：`official_main_composite_notaskgt_astra_xhigh_20261103T152118Z`。
旧 baseline：`official_main_composite_astra_xhigh_20261028T135510Z`。

源码基线提交号分别保存在 JSON 的 sources 中；No task progress 在官方基线之上包含上述本地修改。每个设置仅运行一轮，结果同时包含任务随机性与 planner 执行差异，不能把观察差值当作稳定因果效应。

```sh
python extract.py --baseline-run <11月1日baseline目录> --notask-run <No task progress目录> \
  --legacy-baseline-run <10月28日baseline目录> --manifest <target50.json> \
  --memory-dir <No task progress初始记忆目录> --output <输出目录>
```
