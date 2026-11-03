# RoboCasa composite：Astra 与 5.6-Sol

320 个有效 episode；32 个任务 × seeds 1–5 × 2 模型。

Astra 批次：`composite_main_astra_rerun_20261101T150450Z`；Sol 批次：`composite_main_gpt56_sol`。

## Seen

| 模型 | 成功数 / 80 | 成功率 | VLA 直接 | 准备后 VLA | Planner 介入后 |
|---|---:|---:|---:|---:|---:|
| GPT-6-Astra | 34/80 | 42.50% | 13 | 3 | 18 |
| GPT-5.6-Sol | 32/80 | 40.00% | 13 | 0 | 19 |

## Unseen

| 模型 | 成功数 / 80 | 成功率 | VLA 直接 | 准备后 VLA | Planner 介入后 |
|---|---:|---:|---:|---:|---:|
| GPT-6-Astra | 21/80 | 26.25% | 6 | 1 | 14 |
| GPT-5.6-Sol | 13/80 | 16.25% | 5 | 0 | 8 |


分类按 states.json 的实际动作顺序，截止首次 success=true。VLA 包括 rldx_arm/rldx_skill，连续续跑仍属于 VLA 直接完成。只读感知和记忆调用不算控制介入。
准备类：非 VLA 动作只出现在首次 VLA 前。修复/介入类：首次 VLA 之后有非 VLA 动作，最后任务成功；并非因果消融结论。两批无纯解析动作成功案例，也无单次 VLA 调用直接成功案例。
Astra 的 32 个介入成功中，12 个最后由 VLA 完成，20 个最后由解析动作完成；Sol 的 27 个分别为 17 和 10。
Astra 共有 128 个 episode 出现 VLA 后介入，32 个成功；Sol 142 个中 27 个成功。这是实际介入病例的观察比例，不是随机化修复实验。
失败停止方式：Astra finish=stuck 91 个，无 finish 且到达 100 responses 上限 14 个；Sol 分别 42、73。completed 仅表示运行结束，不表示任务成功。
配对：双方成功 27、仅 Astra 成功 28、仅 Sol 成功 18、双方失败 87。按 task 与 seed 对齐不保证初始场景完全一致。

配置：官方 RLinf/RPent a744bd5；xhigh；最多 100 个模型响应（并非 100 个工具调用），3600s/episode；RLDX-1-FT-RC365，每次最多 40 chunks × 8 steps=320 仿真步。
Astra 记忆 GPT_6_astra_high，Sol 记忆 GPT_5.5_xhigh；不是单一模型变量的公平消融。种子0任务记忆可用，感知、地图与解析控制可用。
报告采用 target50 manifest 中的 320 个 canonical result.json；排除归档和中断的尝试。成功来自环境 state.success，与 320 份 states.json 交叉核对。逐例 JSON 附源文件 SHA-256。

## GPT-6-Astra 成功案例

| 任务 | seed | 类别 | VLA / 解析动作 | 首次成功动作 |
|---|---|---|---|---|
| ScrubCuttingBoard | 1 | Planner 介入后成功 | 10 / 24 | #34 move_delta |
| ScrubCuttingBoard | 2 | Planner 介入后成功 | 13 / 20 | #33 move_delta |
| ScrubCuttingBoard | 3 | VLA 直接完成 | 2 / 0 | #2 rldx_skill |
| ScrubCuttingBoard | 4 | VLA 直接完成 | 2 / 0 | #2 rldx_skill |
| ScrubCuttingBoard | 5 | VLA 直接完成 | 2 / 0 | #2 rldx_skill |
| StackBowlsCabinet | 1 | VLA 直接完成 | 2 / 0 | #2 rldx_skill |
| StackBowlsCabinet | 2 | Planner 准备后 VLA 完成 | 4 / 1 | #5 rldx_skill |
| StackBowlsCabinet | 3 | VLA 直接完成 | 4 / 0 | #4 rldx_skill |
| StackBowlsCabinet | 4 | Planner 介入后成功 | 10 / 10 | #20 rldx_arm |
| StackBowlsCabinet | 5 | VLA 直接完成 | 3 / 0 | #3 rldx_skill |
| WashLettuce | 1 | VLA 直接完成 | 3 / 0 | #3 rldx_skill |
| WashLettuce | 3 | Planner 介入后成功 | 5 / 1 | #6 rldx_skill |
| WashLettuce | 4 | VLA 直接完成 | 3 / 0 | #3 rldx_skill |
| WashLettuce | 5 | Planner 介入后成功 | 12 / 11 | #23 move_to |
| RinseSinkBasin | 1 | Planner 介入后成功 | 5 / 2 | #7 rldx_skill |
| RinseSinkBasin | 2 | Planner 介入后成功 | 8 / 15 | #23 move_delta |
| RinseSinkBasin | 3 | Planner 介入后成功 | 7 / 2 | #9 rldx_arm |
| PreSoakPan | 2 | Planner 介入后成功 | 12 / 24 | #36 move_delta |
| PreSoakPan | 3 | Planner 介入后成功 | 9 / 3 | #12 rldx_arm |
| PreSoakPan | 5 | Planner 介入后成功 | 9 / 2 | #11 rldx_arm |
| StirVegetables | 3 | Planner 介入后成功 | 17 / 24 | #41 move_delta |
| StirVegetables | 5 | Planner 准备后 VLA 完成 | 7 / 2 | #9 rldx_skill |
| LoadDishwasher | 1 | Planner 准备后 VLA 完成 | 4 / 1 | #5 rldx_skill |
| LoadDishwasher | 2 | VLA 直接完成 | 3 / 0 | #3 rldx_skill |
| LoadDishwasher | 3 | VLA 直接完成 | 5 / 0 | #5 rldx_skill |
| SteamInMicrowave | 3 | Planner 介入后成功 | 5 / 2 | #7 move_to |
| SteamInMicrowave | 5 | VLA 直接完成 | 4 / 0 | #4 rldx_skill |
| GetToastedBread | 2 | VLA 直接完成 | 8 / 0 | #8 rldx_skill |
| DeliverStraw | 3 | Planner 介入后成功 | 20 / 23 | #43 move_delta |
| KettleBoiling | 1 | Planner 介入后成功 | 11 / 22 | #33 move_delta |
| PrepareCoffee | 4 | Planner 介入后成功 | 8 / 11 | #19 move_delta |
| PrepareCoffee | 5 | Planner 介入后成功 | 11 / 5 | #16 move_delta |
| PackIdenticalLunches | 4 | VLA 直接完成 | 6 / 0 | #6 rldx_skill |
| PackIdenticalLunches | 5 | Planner 介入后成功 | 18 / 2 | #20 rldx_skill |
| ArrangeBreadBasket | 3 | Planner 介入后成功 | 8 / 1 | #9 rldx_skill |
| ArrangeTea | 4 | VLA 直接完成 | 6 / 0 | #6 rldx_skill |
| BreadSelection | 1 | Planner 介入后成功 | 9 / 19 | #28 scripted_grasp |
| BreadSelection | 3 | Planner 介入后成功 | 12 / 36 | #48 move_to |
| BreadSelection | 4 | VLA 直接完成 | 3 / 0 | #3 rldx_arm |
| CuttingToolSelection | 1 | Planner 介入后成功 | 10 / 2 | #12 rldx_arm |
| CuttingToolSelection | 4 | Planner 准备后 VLA 完成 | 2 / 2 | #4 rldx_skill |
| GarnishPancake | 2 | Planner 介入后成功 | 10 / 39 | #49 move_delta |
| GarnishPancake | 4 | VLA 直接完成 | 7 / 0 | #7 rldx_skill |
| GarnishPancake | 5 | VLA 直接完成 | 4 / 0 | #4 rldx_skill |
| GatherTableware | 4 | Planner 介入后成功 | 8 / 41 | #49 move_delta |
| MakeIceLemonade | 2 | Planner 介入后成功 | 8 / 1 | #9 rldx_skill |
| PanTransfer | 3 | Planner 介入后成功 | 13 / 47 | #60 move_to |
| PortionHotDogs | 3 | VLA 直接完成 | 5 / 0 | #5 rldx_skill |
| PortionHotDogs | 4 | Planner 介入后成功 | 19 / 35 | #54 move_delta |
| RecycleBottlesByType | 1 | Planner 介入后成功 | 6 / 51 | #57 move_delta |
| RecycleBottlesByType | 4 | Planner 介入后成功 | 3 / 55 | #58 move_delta |
| WaffleReheat | 1 | Planner 介入后成功 | 13 / 6 | #19 rldx_arm |
| WaffleReheat | 2 | VLA 直接完成 | 4 / 0 | #4 rldx_skill |
| WashFruitColander | 1 | Planner 介入后成功 | 9 / 4 | #13 rldx_arm |
| WashFruitColander | 3 | Planner 介入后成功 | 19 / 21 | #40 move_to |

## GPT-5.6-Sol 成功案例

| 任务 | seed | 类别 | VLA / 解析动作 | 首次成功动作 |
|---|---|---|---|---|
| ScrubCuttingBoard | 1 | VLA 直接完成 | 2 / 0 | #2 rldx_arm |
| ScrubCuttingBoard | 2 | VLA 直接完成 | 3 / 0 | #3 rldx_arm |
| ScrubCuttingBoard | 3 | VLA 直接完成 | 3 / 0 | #3 rldx_arm |
| ScrubCuttingBoard | 4 | VLA 直接完成 | 2 / 0 | #2 rldx_arm |
| ScrubCuttingBoard | 5 | VLA 直接完成 | 2 / 0 | #2 rldx_skill |
| StackBowlsCabinet | 1 | VLA 直接完成 | 2 / 0 | #2 rldx_skill |
| StackBowlsCabinet | 3 | Planner 介入后成功 | 13 / 1 | #14 rldx_skill |
| StackBowlsCabinet | 5 | VLA 直接完成 | 3 / 0 | #3 rldx_skill |
| WashLettuce | 1 | VLA 直接完成 | 5 / 0 | #5 rldx_skill |
| WashLettuce | 3 | Planner 介入后成功 | 4 / 2 | #6 rldx_skill |
| WashLettuce | 4 | Planner 介入后成功 | 7 / 5 | #12 rldx_arm |
| RinseSinkBasin | 1 | Planner 介入后成功 | 6 / 4 | #10 rldx_arm |
| RinseSinkBasin | 2 | VLA 直接完成 | 3 / 0 | #3 rldx_skill |
| RinseSinkBasin | 3 | Planner 介入后成功 | 7 / 20 | #27 rldx_skill |
| RinseSinkBasin | 4 | Planner 介入后成功 | 4 / 4 | #8 move_delta |
| PreSoakPan | 3 | Planner 介入后成功 | 20 / 6 | #26 rldx_skill |
| PreSoakPan | 4 | VLA 直接完成 | 5 / 0 | #5 rldx_skill |
| PreSoakPan | 5 | Planner 介入后成功 | 9 / 2 | #11 rldx_arm |
| StirVegetables | 3 | VLA 直接完成 | 4 / 0 | #4 rldx_skill |
| StirVegetables | 5 | VLA 直接完成 | 11 / 0 | #11 rldx_arm |
| SteamInMicrowave | 2 | VLA 直接完成 | 6 / 0 | #6 rldx_skill |
| SteamInMicrowave | 5 | Planner 介入后成功 | 5 / 2 | #7 move_to |
| SetUpCuttingStation | 4 | Planner 介入后成功 | 14 / 16 | #30 rldx_skill |
| SetUpCuttingStation | 5 | Planner 介入后成功 | 5 / 2 | #7 move_delta |
| DeliverStraw | 1 | Planner 介入后成功 | 8 / 3 | #11 move_delta |
| KettleBoiling | 2 | Planner 介入后成功 | 4 / 4 | #8 move_to |
| KettleBoiling | 5 | Planner 介入后成功 | 12 / 32 | #44 rldx_arm |
| PrepareCoffee | 5 | Planner 介入后成功 | 9 / 27 | #36 move_to |
| StoreLeftoversInBowl | 1 | Planner 介入后成功 | 10 / 2 | #12 rldx_skill |
| PackIdenticalLunches | 1 | Planner 介入后成功 | 10 / 2 | #12 rldx_skill |
| PackIdenticalLunches | 2 | Planner 介入后成功 | 10 / 6 | #16 rldx_skill |
| PackIdenticalLunches | 4 | Planner 介入后成功 | 12 / 11 | #23 move_delta |
| ArrangeBreadBasket | 1 | VLA 直接完成 | 7 / 0 | #7 rldx_skill |
| ArrangeBreadBasket | 5 | VLA 直接完成 | 5 / 0 | #5 rldx_skill |
| ArrangeTea | 2 | Planner 介入后成功 | 10 / 4 | #14 rldx_arm |
| ArrangeTea | 4 | VLA 直接完成 | 7 / 0 | #7 rldx_skill |
| BreadSelection | 4 | VLA 直接完成 | 4 / 0 | #4 rldx_skill |
| CuttingToolSelection | 3 | Planner 介入后成功 | 7 / 3 | #10 release |
| GarnishPancake | 4 | VLA 直接完成 | 9 / 0 | #9 rldx_skill |
| GarnishPancake | 5 | Planner 介入后成功 | 6 / 1 | #7 rldx_skill |
| MakeIceLemonade | 1 | Planner 介入后成功 | 9 / 20 | #29 rldx_arm |
| PortionHotDogs | 1 | Planner 介入后成功 | 9 / 9 | #18 move_to |
| PortionHotDogs | 2 | Planner 介入后成功 | 14 / 36 | #50 move_to |
| PortionHotDogs | 3 | Planner 介入后成功 | 12 / 8 | #20 rldx_arm |
| WaffleReheat | 2 | Planner 介入后成功 | 10 / 5 | #15 rldx_arm |
