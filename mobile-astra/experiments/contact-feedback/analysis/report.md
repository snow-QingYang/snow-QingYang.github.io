# RoboCasa composite：接触反馈移除对照

官方 RPent · GPT-6-Astra / xhigh · RLDX-1-FT-RC365。主对照为网站 E01 的 11 月 1 日 baseline 重跑；两组各 160 个有效 episode。

| 任务组 | Baseline | NoContactGT | 成功率差 |
|---|---:|---:|---:|
| Seen | 34/80 · 42.50% | 26/80 · 32.50% | -10.00 pp |
| Unseen | 21/80 · 26.25% | 20/80 · 25.00% | -1.25 pp |
| 总计 | 55/160 · 34.38% | 46/160 · 28.75% | -5.63 pp |

| 配对结果 | Seen | Unseen | 总计 |
|---|---:|---:|---:|
| 双方成功 | 20 | 9 | 29 |
| 仅 baseline 成功 | 14 | 12 | 26 |
| 仅 NoContactGT 成功 | 6 | 11 | 17 |
| 双方失败 | 40 | 48 | 88 |

## 实际移除与保留

两个 RLDX 技能不再返回 `grasp_contact`、`grasp_obj`、`grasped`、`grasp_detected`，执行封装也不再为这些字段查询模拟器接触。`task_progress` 按任务过滤接触派生标量：25 个任务、60 个任务—字段条目。过滤发生在保存状态之前，其他进度保留。

保留 `held_apart`（闭合命令与夹爪开度启发式）、`gripper_qpos`、末端高度变化 `peak_lift`，以及原版模拟器深度和世界坐标图、相机标定、本体状态、顶层成功与终止信号、评分规则访问和历史记忆。Prompt、VLA 输入与权重、动作转换、历史连续性和预算不变。没有叠加 DA3 或 NoTaskGT。

`PrepareCoffee.contact_check` 是几何距离判据，因此仍保留。相反，`ScrubCuttingBoard.sweep_range` 来自接触位置，因此被过滤。过滤按已审核来源，不按字段名是否含 contact。完整任务—字段表保存在 JSON 的 protocol 中。

顶层成功仍可能依赖接触；评分源码、历史记忆、原生 Planner 能力仍保留。这是显式接触反馈的消融，不是完全无真值或文件／RPC 隔离。

## 数据与比较核验

320 个结果均有效，逐一与末条保存观测的原生 success 核对一致。NoContactGT 有 159 局正常完成及 1 局有效超时失败（PortionHotDogs seed 2，3631.6 秒）；超时局保留在分母中。只统计 canonical 目录，归档与中断重试不重复计入。

检查 NoContactGT 的 4772 条保存观测，未发现上述 4 个结果字段，也未发现各任务应过滤的实时进度字段。此检查不覆盖历史记忆内容或所有原生 Planner 通道。

两组的 148 个启动记忆文件 SHA-256 一致；160 对结果的记忆选择相同，涉及 95 个唯一文件，其当前 SHA-256 也一致。实际读取顺序可以不同。

初始机器人状态最大绝对差 >1e-6 的有 11 对，任务文本不同的有 2 对。逐值完全相等口径下有 17 对机器人状态不同，其中部分差异低于阈值。检查仅覆盖 step 0 的本体状态和任务文本，未覆盖所有物体；不比较按实验设置过滤的进度。

每个任务只有 5 个 seed，每种设置只运行一轮；VLA 动作采样未随场景 seed 固定。这些同任务、同 seed 的结果变化不等于稳定的因果效应；不能从单个失败反推某条被移除信息必不可少。

## 代表案例

以下动作数来自 states.json 的动作记录，不包括读图、读文件等只读工具调用。[六个新增成功的动作过程与图片](../cases/)。

| 任务 / seed | Baseline | NoContactGT | NoContactGT 动作 | 首次原生成功 |
|---|---|---|---|---|
| WeighIngredients s5 | 失败，1879.7 s | 成功，790.9 s | 9 VLA + 3 其他动作 | step 12 / move_to |
| MakeIceLemonade s3 | 失败，1336.4 s | 成功，474.4 s | 7 VLA + 0 其他动作 | step 7 / rldx_skill |
| PackIdenticalLunches s4 | 成功，394.8 s | 失败，2375.9 s | 16 VLA + 39 其他动作 | 未成功 |
| PanTransfer s3 | 成功，1715.8 s | 失败，1984.0 s | 21 VLA + 5 其他动作 | 未成功 |

最后完成的 WeighIngredients seed 5：9 次 rldx_arm 加 3 次 move_to 后原生任务成功，随后 Agent 调用 finish(success)。最后一次 move_to 的 ok=false，只代表没有达到该动作的位置容差；它不覆盖环境任务的成功判定。该局不返回 packaged_food_on_digital_scale，仍返回 gripper_obj_far、obj_upright、cabinet_closed。

PackIdenticalLunches seed 4：baseline 用 6 次 VLA 完成；NoContactGT 的进度为空，16 次 VLA 与 39 次其他动作后仍失败。这是轨迹差异，不能单独证明缺少进度导致失败。

## 逐任务与 seed

每个 seed 为 `Baseline/NoContactGT`，1 表示原生成功，0 表示失败。

| 分组 | 任务 | Baseline | NoContactGT | s1 | s2 | s3 | s4 | s5 |
|---|---|---:|---:|---|---|---|---|---|
| Seen | ScrubCuttingBoard | 5/5 | 5/5 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| Seen | StackBowlsCabinet | 5/5 | 3/5 | 1/1 | 1/0 | 1/1 | 1/0 | 1/1 |
| Seen | WashLettuce | 4/5 | 3/5 | 1/1 | 0/0 | 1/1 | 1/0 | 1/1 |
| Seen | RinseSinkBasin | 3/5 | 3/5 | 1/0 | 1/1 | 1/1 | 0/1 | 0/0 |
| Seen | PreSoakPan | 3/5 | 4/5 | 0/1 | 1/1 | 1/1 | 0/0 | 1/1 |
| Seen | StirVegetables | 2/5 | 3/5 | 0/1 | 0/0 | 1/1 | 0/0 | 1/1 |
| Seen | LoadDishwasher | 3/5 | 2/5 | 1/1 | 1/0 | 1/1 | 0/0 | 0/0 |
| Seen | SteamInMicrowave | 2/5 | 0/5 | 0/0 | 0/0 | 1/0 | 0/0 | 1/0 |
| Seen | SetUpCuttingStation | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | GetToastedBread | 1/5 | 1/5 | 0/0 | 1/0 | 0/0 | 0/0 | 0/1 |
| Seen | DeliverStraw | 1/5 | 1/5 | 0/0 | 0/0 | 1/0 | 0/1 | 0/0 |
| Seen | KettleBoiling | 1/5 | 1/5 | 1/0 | 0/0 | 0/1 | 0/0 | 0/0 |
| Seen | PrepareCoffee | 2/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 1/0 |
| Seen | StoreLeftoversInBowl | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | SearingMeat | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | PackIdenticalLunches | 2/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 1/0 |
| Unseen | ArrangeBreadBasket | 1/5 | 2/5 | 0/1 | 0/0 | 1/1 | 0/0 | 0/0 |
| Unseen | ArrangeTea | 1/5 | 2/5 | 0/0 | 0/1 | 0/0 | 1/1 | 0/0 |
| Unseen | BreadSelection | 3/5 | 3/5 | 1/1 | 0/1 | 1/0 | 1/1 | 0/0 |
| Unseen | CategorizeCondiments | 0/5 | 1/5 | 0/0 | 0/1 | 0/0 | 0/0 | 0/0 |
| Unseen | CuttingToolSelection | 2/5 | 1/5 | 1/0 | 0/1 | 0/0 | 1/0 | 0/0 |
| Unseen | GarnishPancake | 3/5 | 3/5 | 0/1 | 1/0 | 0/0 | 1/1 | 1/1 |
| Unseen | GatherTableware | 1/5 | 1/5 | 0/0 | 0/0 | 0/0 | 1/0 | 0/1 |
| Unseen | HeatKebabSandwich | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Unseen | MakeIceLemonade | 1/5 | 2/5 | 0/0 | 1/0 | 0/1 | 0/1 | 0/0 |
| Unseen | PanTransfer | 1/5 | 0/5 | 0/0 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | PortionHotDogs | 2/5 | 2/5 | 0/1 | 0/0 | 1/0 | 1/1 | 0/0 |
| Unseen | RecycleBottlesByType | 2/5 | 0/5 | 1/0 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | SeparateFreezerRack | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Unseen | WaffleReheat | 2/5 | 1/5 | 1/1 | 1/0 | 0/0 | 0/0 | 0/0 |
| Unseen | WashFruitColander | 2/5 | 1/5 | 1/1 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | WeighIngredients | 0/5 | 1/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 |

## 数据来源与重建

baseline：`official_main_composite_astra_xhigh_20261101T150450Z`；官方基线 `a744bd5f128ebef3cb8c6736cf7cd98adff681f1`。
nocontact：`official_main_composite_nocontactgt_astra_xhigh_20261104T014440Z`；官方基线 `a744bd5f128ebef3cb8c6736cf7cd98adff681f1`。

JSON / CSV 保存逐局 result.json 与 states.json 的 SHA-256；JSON 另含启动元数据、实际源文件、任务清单、记忆和本统计脚本的 SHA-256。NoContactGT 的 revision 表示官方基线，具体本地修改由 source_files_sha256 标识。原始运行文件不随网页发布。

```sh
python extract.py --baseline-run <baseline目录> --nocontact-run <NoContactGT目录> \
  --manifest <target50.json> --source-repo <NoContactGT源码目录> \
  --memory-dir <原任务记忆目录> --output <本分析输出目录>
```
