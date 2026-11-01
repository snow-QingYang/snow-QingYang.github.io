# Baiyajing HarnessVLA：160 次 composite 运行分析

本地成功 61/160（38.1%）：Seen 39/80，Unseen 22/80。仓库 README 为 59/160（39+20），两者分开统计。

| 成功路径 | Seen | Unseen | 总计 |
|---|---:|---:|---:|
| 初始整任务 VLA 成功 | 21 | 7 | 28 |
| Planner 修复 · vla/pick 程序 | 13 | 7 | 20 |
| Planner 修复 · 含显式控制 | 5 | 8 | 13 |

首次整任务 VLA 成功 28/160；剩下 132 个进入 Planner，33/132 成功。20 个成功程序只有 vla/pick；13 个还含显式导航/搬运/放置。
pick 使用 VLA。vla/pick 内部有自动靠近目标、手臂复位、放下持物和撤离等行为，因此 20 个不能称为纯 VLA 直接成功。
33 个修复成功最终程序步骤：vla 28、put_down 2、carry 2、release 1。vla 内部的撤离可能参与最后成功，不能直接把这 28 个称作纯神经策略收尾。
失败终止标签：budget 57；object_on_floor 42（含地面或机器人本体上不可达的物体）。初次 VLA 的 budget 是该 attempt 的 chunk 预算，并非整局超时。
7 个程序 op：vla / pick / carry / put_down / release / goto / retract。执行步骤、attempt、chunk 与 Planner 调用是不同计数单位。
步骤 ok 表示子步骤检查，不等于完整任务 success；以 result.json 中的环境成功为准。程序中未执行的排队步骤不算已执行。
配置：GPT-6-sol / medium；至多 32 次 Planner 调用，3600 秒预算；8 GPU、每卡 1 个 episode；seed-0 记忆；Baiyajing 0596036、RPent 72686b8。
初始整任务 VLA 上限 min(600,max(250,int(1.5*horizon/8))) chunks；每 chunk 8 控制步。原子子任务通常至多 2 attempts × 80 chunks。
与官方 RPent 报告的实现、Planner、记忆和 VLA 调度预算不同，不能当作只改变模型的消融。仓库说明执行器规则参考过同种子失败，不属于严格 held-out 评估。

## 逐例分类

| 任务 | seed | 组别 | 结果 / 路径 | Planner 调用 | 程序步 | 结束标签 |
|---|---:|---|---|---:|---:|---|
| ScrubCuttingBoard | 1 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| ScrubCuttingBoard | 2 | seen | 未成功 | 9 | 16 | budget |
| ScrubCuttingBoard | 3 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| ScrubCuttingBoard | 4 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| ScrubCuttingBoard | 5 | seen | 未成功 | 5 | 6 | object_on_floor |
| StackBowlsCabinet | 1 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| StackBowlsCabinet | 2 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| StackBowlsCabinet | 3 | seen | 未成功 | 6 | 7 | object_on_floor |
| StackBowlsCabinet | 4 | seen | 未成功 | 1 | 1 | object_on_floor |
| StackBowlsCabinet | 5 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| WashLettuce | 1 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| WashLettuce | 2 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| WashLettuce | 3 | seen | 未成功 | 9 | 12 | budget |
| WashLettuce | 4 | seen | 未成功 | 17 | 19 | budget |
| WashLettuce | 5 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| RinseSinkBasin | 1 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| RinseSinkBasin | 2 | seen | Planner 修复 · vla/pick 程序 | 3 | 4 | success |
| RinseSinkBasin | 3 | seen | Planner 修复 · vla/pick 程序 | 2 | 4 | success |
| RinseSinkBasin | 4 | seen | 未成功 | 10 | 11 | budget |
| RinseSinkBasin | 5 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| PreSoakPan | 1 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| PreSoakPan | 2 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| PreSoakPan | 3 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| PreSoakPan | 4 | seen | 未成功 | 12 | 14 | budget |
| PreSoakPan | 5 | seen | 未成功 | 10 | 13 | budget |
| StirVegetables | 1 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| StirVegetables | 2 | seen | 未成功 | 14 | 16 | budget |
| StirVegetables | 3 | seen | 未成功 | 8 | 10 | budget |
| StirVegetables | 4 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| StirVegetables | 5 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| LoadDishwasher | 1 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| LoadDishwasher | 2 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| LoadDishwasher | 3 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| LoadDishwasher | 4 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| LoadDishwasher | 5 | seen | 未成功 | 8 | 9 | budget |
| SteamInMicrowave | 1 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| SteamInMicrowave | 2 | seen | 未成功 | 1 | 1 | object_on_floor |
| SteamInMicrowave | 3 | seen | 未成功 | 2 | 2 | object_on_floor |
| SteamInMicrowave | 4 | seen | Planner 修复 · vla/pick 程序 | 1 | 3 | success |
| SteamInMicrowave | 5 | seen | 未成功 | 10 | 11 | budget |
| SetUpCuttingStation | 1 | seen | 未成功 | 12 | 18 | budget |
| SetUpCuttingStation | 2 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| SetUpCuttingStation | 3 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| SetUpCuttingStation | 4 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| SetUpCuttingStation | 5 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| GetToastedBread | 1 | seen | 未成功 | 18 | 22 | budget |
| GetToastedBread | 2 | seen | 未成功 | 15 | 19 | budget |
| GetToastedBread | 3 | seen | 未成功 | 2 | 3 | object_on_floor |
| GetToastedBread | 4 | seen | 未成功 | 11 | 13 | budget |
| GetToastedBread | 5 | seen | Planner 修复 · 含显式控制 | 2 | 6 | success |
| DeliverStraw | 1 | seen | 未成功 | 12 | 12 | object_on_floor |
| DeliverStraw | 2 | seen | Planner 修复 · vla/pick 程序 | 6 | 7 | success |
| DeliverStraw | 3 | seen | Planner 修复 · 含显式控制 | 11 | 17 | success |
| DeliverStraw | 4 | seen | 未成功 | 13 | 15 | budget |
| DeliverStraw | 5 | seen | 未成功 | 12 | 14 | budget |
| KettleBoiling | 1 | seen | Planner 修复 · 含显式控制 | 7 | 10 | success |
| KettleBoiling | 2 | seen | 未成功 | 9 | 11 | budget |
| KettleBoiling | 3 | seen | Planner 修复 · vla/pick 程序 | 1 | 3 | success |
| KettleBoiling | 4 | seen | Planner 修复 · vla/pick 程序 | 3 | 4 | success |
| KettleBoiling | 5 | seen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| PrepareCoffee | 1 | seen | 未成功 | 16 | 19 | budget |
| PrepareCoffee | 2 | seen | 未成功 | 17 | 28 | budget |
| PrepareCoffee | 3 | seen | 未成功 | 19 | 25 | budget |
| PrepareCoffee | 4 | seen | 未成功 | 27 | 40 | budget |
| PrepareCoffee | 5 | seen | 未成功 | 16 | 18 | budget |
| StoreLeftoversInBowl | 1 | seen | 未成功 | 1 | 1 | object_on_floor |
| StoreLeftoversInBowl | 2 | seen | 未成功 | 1 | 1 | object_on_floor |
| StoreLeftoversInBowl | 3 | seen | 初始整任务 VLA 成功 | 0 | 1 | success |
| StoreLeftoversInBowl | 4 | seen | 未成功 | 6 | 8 | object_on_floor |
| StoreLeftoversInBowl | 5 | seen | 未成功 | 1 | 1 | object_on_floor |
| SearingMeat | 1 | seen | 未成功 | 2 | 3 | object_on_floor |
| SearingMeat | 2 | seen | 未成功 | 14 | 21 | budget |
| SearingMeat | 3 | seen | 未成功 | 13 | 17 | budget |
| SearingMeat | 4 | seen | Planner 修复 · 含显式控制 | 15 | 20 | success |
| SearingMeat | 5 | seen | 未成功 | 7 | 10 | budget |
| PackIdenticalLunches | 1 | seen | 未成功 | 1 | 1 | object_on_floor |
| PackIdenticalLunches | 2 | seen | 未成功 | 15 | 22 | budget |
| PackIdenticalLunches | 3 | seen | 未成功 | 5 | 12 | object_on_floor |
| PackIdenticalLunches | 4 | seen | 未成功 | 13 | 20 | budget |
| PackIdenticalLunches | 5 | seen | Planner 修复 · 含显式控制 | 2 | 9 | success |
| ArrangeBreadBasket | 1 | unseen | 未成功 | 4 | 5 | object_on_floor |
| ArrangeBreadBasket | 2 | unseen | 未成功 | 3 | 3 | object_on_floor |
| ArrangeBreadBasket | 3 | unseen | 未成功 | 7 | 8 | object_on_floor |
| ArrangeBreadBasket | 4 | unseen | 未成功 | 2 | 2 | object_on_floor |
| ArrangeBreadBasket | 5 | unseen | Planner 修复 · 含显式控制 | 5 | 7 | success |
| ArrangeTea | 1 | unseen | 未成功 | 1 | 1 | object_on_floor |
| ArrangeTea | 2 | unseen | Planner 修复 · 含显式控制 | 4 | 10 | success |
| ArrangeTea | 3 | unseen | 未成功 | 16 | 17 | budget |
| ArrangeTea | 4 | unseen | Planner 修复 · 含显式控制 | 7 | 12 | success |
| ArrangeTea | 5 | unseen | 未成功 | 4 | 4 | object_on_floor |
| BreadSelection | 1 | unseen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| BreadSelection | 2 | unseen | 未成功 | 4 | 4 | object_on_floor |
| BreadSelection | 3 | unseen | 未成功 | 13 | 18 | budget |
| BreadSelection | 4 | unseen | 未成功 | 16 | 20 | budget |
| BreadSelection | 5 | unseen | 未成功 | 1 | 1 | object_on_floor |
| CategorizeCondiments | 1 | unseen | 未成功 | 20 | 30 | budget |
| CategorizeCondiments | 2 | unseen | 未成功 | 8 | 8 | object_on_floor |
| CategorizeCondiments | 3 | unseen | 未成功 | 16 | 23 | budget |
| CategorizeCondiments | 4 | unseen | 未成功 | 17 | 26 | budget |
| CategorizeCondiments | 5 | unseen | 未成功 | 16 | 24 | budget |
| CuttingToolSelection | 1 | unseen | 未成功 | 13 | 14 | budget |
| CuttingToolSelection | 2 | unseen | 未成功 | 14 | 15 | budget |
| CuttingToolSelection | 3 | unseen | 未成功 | 15 | 18 | budget |
| CuttingToolSelection | 4 | unseen | 未成功 | 15 | 19 | budget |
| CuttingToolSelection | 5 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| GarnishPancake | 1 | unseen | 未成功 | 3 | 3 | object_on_floor |
| GarnishPancake | 2 | unseen | Planner 修复 · 含显式控制 | 5 | 8 | success |
| GarnishPancake | 3 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| GarnishPancake | 4 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| GarnishPancake | 5 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| GatherTableware | 1 | unseen | Planner 修复 · 含显式控制 | 7 | 14 | success |
| GatherTableware | 2 | unseen | 未成功 | 9 | 10 | budget |
| GatherTableware | 3 | unseen | 未成功 | 14 | 24 | budget |
| GatherTableware | 4 | unseen | Planner 修复 · 含显式控制 | 2 | 7 | success |
| GatherTableware | 5 | unseen | Planner 修复 · 含显式控制 | 6 | 9 | success |
| HeatKebabSandwich | 1 | unseen | 未成功 | 12 | 14 | budget |
| HeatKebabSandwich | 2 | unseen | 未成功 | 11 | 19 | budget |
| HeatKebabSandwich | 3 | unseen | 未成功 | 10 | 15 | budget |
| HeatKebabSandwich | 4 | unseen | 未成功 | 12 | 15 | budget |
| HeatKebabSandwich | 5 | unseen | Planner 修复 · vla/pick 程序 | 6 | 8 | success |
| MakeIceLemonade | 1 | unseen | 未成功 | 2 | 3 | object_on_floor |
| MakeIceLemonade | 2 | unseen | Planner 修复 · vla/pick 程序 | 4 | 8 | success |
| MakeIceLemonade | 3 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| MakeIceLemonade | 4 | unseen | 未成功 | 25 | 31 | budget |
| MakeIceLemonade | 5 | unseen | Planner 修复 · vla/pick 程序 | 2 | 3 | success |
| PanTransfer | 1 | unseen | 未成功 | 8 | 7 | object_on_floor |
| PanTransfer | 2 | unseen | 未成功 | 11 | 10 | object_on_floor |
| PanTransfer | 3 | unseen | 未成功 | 13 | 14 | budget |
| PanTransfer | 4 | unseen | 未成功 | 8 | 7 | object_on_floor |
| PanTransfer | 5 | unseen | 未成功 | 5 | 5 | object_on_floor |
| PortionHotDogs | 1 | unseen | 未成功 | 14 | 17 | budget |
| PortionHotDogs | 2 | unseen | 未成功 | 12 | 17 | budget |
| PortionHotDogs | 3 | unseen | 未成功 | 13 | 14 | budget |
| PortionHotDogs | 4 | unseen | 未成功 | 1 | 1 | object_on_floor |
| PortionHotDogs | 5 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| RecycleBottlesByType | 1 | unseen | 未成功 | 1 | 1 | object_on_floor |
| RecycleBottlesByType | 2 | unseen | 未成功 | 1 | 1 | object_on_floor |
| RecycleBottlesByType | 3 | unseen | 未成功 | 1 | 1 | object_on_floor |
| RecycleBottlesByType | 4 | unseen | 未成功 | 1 | 1 | object_on_floor |
| RecycleBottlesByType | 5 | unseen | 未成功 | 15 | 17 | budget |
| SeparateFreezerRack | 1 | unseen | 未成功 | 1 | 1 | object_on_floor |
| SeparateFreezerRack | 2 | unseen | 未成功 | 1 | 1 | object_on_floor |
| SeparateFreezerRack | 3 | unseen | 未成功 | 1 | 1 | object_on_floor |
| SeparateFreezerRack | 4 | unseen | 未成功 | 1 | 1 | object_on_floor |
| SeparateFreezerRack | 5 | unseen | 未成功 | 1 | 1 | object_on_floor |
| WaffleReheat | 1 | unseen | Planner 修复 · vla/pick 程序 | 1 | 2 | success |
| WaffleReheat | 2 | unseen | Planner 修复 · vla/pick 程序 | 3 | 4 | success |
| WaffleReheat | 3 | unseen | Planner 修复 · vla/pick 程序 | 2 | 3 | success |
| WaffleReheat | 4 | unseen | 未成功 | 10 | 14 | budget |
| WaffleReheat | 5 | unseen | 未成功 | 5 | 9 | object_on_floor |
| WashFruitColander | 1 | unseen | Planner 修复 · 含显式控制 | 4 | 9 | success |
| WashFruitColander | 2 | unseen | 未成功 | 11 | 12 | budget |
| WashFruitColander | 3 | unseen | 未成功 | 9 | 12 | budget |
| WashFruitColander | 4 | unseen | 未成功 | 19 | 25 | budget |
| WashFruitColander | 5 | unseen | 未成功 | 15 | 20 | budget |
| WeighIngredients | 1 | unseen | 未成功 | 4 | 4 | object_on_floor |
| WeighIngredients | 2 | unseen | 未成功 | 15 | 17 | budget |
| WeighIngredients | 3 | unseen | 初始整任务 VLA 成功 | 0 | 1 | success |
| WeighIngredients | 4 | unseen | 未成功 | 16 | 18 | budget |
| WeighIngredients | 5 | unseen | 未成功 | 12 | 14 | object_on_floor |
