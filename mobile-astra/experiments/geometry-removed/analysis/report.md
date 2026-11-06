# RoboCasa composite：移除主动几何查询

官方 RPent · GPT-6-Astra / xhigh · RLDX-1-FT-RC365。32 个任务 × seeds 1–5；两组各 160 个有效 episode。

| 任务组 | Baseline | NoGeomTools | 成功率差 |
|---|---:|---:|---:|
| Seen | 34/80 · 42.50% | 22/80 · 27.50% | -15.00 pp |
| Unseen | 21/80 · 26.25% | 17/80 · 21.25% | -5.00 pp |
| 总计 | 55/160 · 34.38% | 39/160 · 24.38% | -10.00 pp |

| 配对结果 | Seen | Unseen | 总计 |
|---|---:|---:|---:|
| 双方成功 | 15 | 8 | 23 |
| 仅 baseline 成功 | 19 | 13 | 32 |
| 仅 NoGeomTools 成功 | 7 | 9 | 16 |
| 双方失败 | 39 | 50 | 89 |

## 实验范围

移除 Planner 工具注册表中的 `back_project_batch` 与 `query_world_map`，并删除评测 prompt 对这两个工具的说明、示例与调用要求；同步调整观测工具说明。

这两个工具原本分别返回指定像素对应的世界坐标，以及按高度／区域查询的世界坐标聚类。本实验不删除模拟器内部深度或世界坐标图，也不接入 DA3。

原版 `task_progress`（可能包含距离）、success、接触反馈、本体状态、相机标定、评分规则访问、历史记忆、VLA 输入／权重和动作控制均保留。move_to、scripted_grasp、navigate_to、move_delta 仍可接收 Agent 提供的位置或位移。这是一项主动几何查询工具的消融，不是完全无几何真值或文件／RPC 隔离。

## 数据核验

两组 320 个 canonical 结果均有效，末条观测的原生 success 与结果逐局一致；NoGeomTools 160 局均正常结束，任务失败也保留在分母中。归档和中断重试不重复统计。

检查 NoGeomTools 的 4615 条保存观测；其中 4348 条仍有非空任务进度。2113 条 VLA 动作结果仍含 grasp_contact，符合保留接触反馈的设置。

检查 160 局的流式记录，共 5263 个去重 MCP 调用；两个移除工具的调用数为 0。另检查 1 个原生命令记录；读取几何文件或通过原生命令访问几何的模式命中共 0 次。检查范围限于已记录工具名、文件参数和命令文本；不能覆盖间接路径、外部脚本、历史记忆或未记录执行。

两组 148 个启动记忆文件的 SHA-256 相同；160 对结果选择的记忆文件一致，涉及 95 个唯一文件，当前哈希也一致。读取顺序不要求相同。

初始机器人状态最大绝对差 >1e-6 的有 10 对，逐值不完全相同的有 16 对；任务文本不同的有 2 对。未检查全部场景物体。

每个任务仅 5 个 seed，每种设置只运行一轮。VLA 动作采样未随场景 seed 固定，同任务同 seed 的结果变化不能直接解释为移除工具的稳定因果效应。

## 代表轨迹的动作数量

下表是 states.json 动作记录，不包括读图、读文件等只读调用；不据此判断失败原因。

| 任务 / seed | Baseline | NoGeomTools | Baseline 动作 | NoGeomTools 动作 |
|---|---|---|---|---|
| RinseSinkBasin s1 | 成功 | 失败 | 5 VLA + 2 其他 | 11 VLA + 4 其他 |
| StoreLeftoversInBowl s3 | 失败 | 成功 | 17 VLA + 18 其他 | 21 VLA + 5 其他 |
| GarnishPancake s1 | 失败 | 成功 | 9 VLA + 47 其他 | 4 VLA + 0 其他 |
| WashFruitColander s1 | 成功 | 失败 | 9 VLA + 4 其他 | 19 VLA + 50 其他 |

## 逐任务与 seed

每个 seed 为 Baseline/NoGeomTools；1 为原生成功，0 为失败。

| 分组 | 任务 | Baseline | NoGeomTools | s1 | s2 | s3 | s4 | s5 |
|---|---|---:|---:|---|---|---|---|---|
| Seen | ScrubCuttingBoard | 5/5 | 3/5 | 1/1 | 1/0 | 1/0 | 1/1 | 1/1 |
| Seen | StackBowlsCabinet | 5/5 | 4/5 | 1/1 | 1/0 | 1/1 | 1/1 | 1/1 |
| Seen | WashLettuce | 4/5 | 3/5 | 1/1 | 0/0 | 1/0 | 1/1 | 1/1 |
| Seen | RinseSinkBasin | 3/5 | 0/5 | 1/0 | 1/0 | 1/0 | 0/0 | 0/0 |
| Seen | PreSoakPan | 3/5 | 3/5 | 0/1 | 1/0 | 1/1 | 0/0 | 1/1 |
| Seen | StirVegetables | 2/5 | 0/5 | 0/0 | 0/0 | 1/0 | 0/0 | 1/0 |
| Seen | LoadDishwasher | 3/5 | 2/5 | 1/0 | 1/0 | 1/1 | 0/1 | 0/0 |
| Seen | SteamInMicrowave | 2/5 | 2/5 | 0/0 | 0/1 | 1/0 | 0/0 | 1/1 |
| Seen | SetUpCuttingStation | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | GetToastedBread | 1/5 | 1/5 | 0/1 | 1/0 | 0/0 | 0/0 | 0/0 |
| Seen | DeliverStraw | 1/5 | 2/5 | 0/1 | 0/0 | 1/1 | 0/0 | 0/0 |
| Seen | KettleBoiling | 1/5 | 1/5 | 1/0 | 0/0 | 0/0 | 0/0 | 0/1 |
| Seen | PrepareCoffee | 2/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 1/0 |
| Seen | StoreLeftoversInBowl | 0/5 | 1/5 | 0/0 | 0/0 | 0/1 | 0/0 | 0/0 |
| Seen | SearingMeat | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Seen | PackIdenticalLunches | 2/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 1/0 |
| Unseen | ArrangeBreadBasket | 1/5 | 1/5 | 0/1 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | ArrangeTea | 1/5 | 1/5 | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 |
| Unseen | BreadSelection | 3/5 | 2/5 | 1/0 | 0/1 | 1/0 | 1/1 | 0/0 |
| Unseen | CategorizeCondiments | 0/5 | 1/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 |
| Unseen | CuttingToolSelection | 2/5 | 3/5 | 1/1 | 0/1 | 0/1 | 1/0 | 0/0 |
| Unseen | GarnishPancake | 3/5 | 4/5 | 0/1 | 1/1 | 0/0 | 1/1 | 1/1 |
| Unseen | GatherTableware | 1/5 | 0/5 | 0/0 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | HeatKebabSandwich | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Unseen | MakeIceLemonade | 1/5 | 0/5 | 0/0 | 1/0 | 0/0 | 0/0 | 0/0 |
| Unseen | PanTransfer | 1/5 | 0/5 | 0/0 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | PortionHotDogs | 2/5 | 3/5 | 0/0 | 0/1 | 1/0 | 1/1 | 0/1 |
| Unseen | RecycleBottlesByType | 2/5 | 0/5 | 1/0 | 0/0 | 0/0 | 1/0 | 0/0 |
| Unseen | SeparateFreezerRack | 0/5 | 0/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| Unseen | WaffleReheat | 2/5 | 1/5 | 1/1 | 1/0 | 0/0 | 0/0 | 0/0 |
| Unseen | WashFruitColander | 2/5 | 0/5 | 1/0 | 0/0 | 1/0 | 0/0 | 0/0 |
| Unseen | WeighIngredients | 0/5 | 1/5 | 0/0 | 0/0 | 0/0 | 0/0 | 0/1 |

## 数据来源与重建

baseline：`official_main_composite_astra_xhigh_20261101T150450Z`；官方基线 `a744bd5f128ebef3cb8c6736cf7cd98adff681f1`。
nogeom：`official_main_composite_nogeomtools_astra_xhigh_20261104T093002Z`；官方基线 `a744bd5f128ebef3cb8c6736cf7cd98adff681f1`。

JSON / CSV 保存逐局 result.json 与 states.json 的 SHA-256；JSON 另含启动元数据、实际源文件、任务清单、记忆和本脚本的 SHA-256。原始运行文件不随网页发布。

```sh
python extract.py --baseline-run BASELINE_RUN --nogeom-run NOGEOM_RUN --manifest TARGET50_JSON --source-repo NOGEOM_SOURCE --memory-dir MEMORY_DIR --output OUTPUT_DIR
```
