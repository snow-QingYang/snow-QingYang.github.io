# E10 · VLM 任务进度，保留模拟器成功真值

2026-11-13 15:13:19（UTC+8）完成。160 个有效 episode：Seen **26/80（32.50%）**，
Unseen **18/80（22.50%）**，总计 **44/160（27.50%）**。

## 方法与配置

中间 `task_progress` 由独立 `gpt-6.1-terra` / medium 对固定条件逐项判断。
输入包括任务文字、条件清单、前一次视觉判断，以及当前和上一次动作边界的
左、右、导航、腕部 RGB。初始请求 4 张图，后续每次 8 张。重复查询读取缓存。
VLM 不接收模拟器当前成功值、原生进度、深度、动作返回、接触真值或 memory。

外层 Agent 收到原生 `success` / `robocasa_terminated`，`success_source=native`；
VLA 恢复原生成功早停。`finish(success)` 检查最新原生成功值，即使视觉判断
仍为 unknown/incomplete 也可结束。几何、接触、原版历史 memory 和 VLA 输入保留。
条件清单增加静态任务规则知识；不能把它的影响与 VLM 模型贡献混为一谈。

Planner：GPT-6-Astra / xhigh，100 turns / 3600 秒。VLA：RLDX-1-FT-RC365，
40 chunks × 8 steps、settle patience 999。任务：16 Seen + 16 Unseen，各 seeds 1–5，
环境 split=target。物理 GPU 0、2、3、7；2026-11-12 22:24:55 开始。
原版 memory revision：47f301ef33bf8d0e8c770342f16b3c39c6a0e8c1。

## 对照

| 设置 | Seen | Unseen | 总计 |
| --- | --- | --- | --- |
| E01 · 原版 baseline | 34/80 | 21/80 | 55/160 |
| E03 · 移除 task_progress，保留原生成功 | 24/80 | 17/80 | 41/160 |
| E10 · VLM 进度 + 原生成功 | 26/80 | 18/80 | 44/160 |

E10 相比 E03 多成功 3 局（+1.875 个百分点），相比 baseline 少 11 局（−6.875 个百分点）。
与 E03 按 task/seed 配对：20 局都成功、24 局仅 E10 成功、21 局仅 E03 成功、95 局都失败。
与 baseline 配对：28 局都成功、16 局仅 E10 成功、27 局仅 baseline 成功、89 局都失败。

本次导出未完整核验对照组初态一致性，也没有固定 VLA 随机噪声。
E03 历史运行仍生成 success_criteria.md，但文件工具只许读取选定 memory；
本次不生成该文件，代码版本也不同。条件知识及额外 VLM 计算也是新增变量。
这是单批运行比较，不能把 +3 局全部归因于 VLM。

## 视觉判断与真实成功

| 最终 VLM 判断 | 模拟器成功 | 模拟器失败 |
| --- | --- | --- |
| apparently_complete | 3 | 2 |
| incomplete | 31 | 68 |
| unknown | 10 | 46 |

44 个原生成功中，41 个结束时没有得到 VLM 的完成确认。这正是原生成功反馈允许
Agent 及时结束的场景。全部 44 局调用 finish(success)，首次记录原生成功后均无额外动作。
其余 97 局 finish(stuck)，19 局没有 finish。终态比较受停止策略影响，不能直接当作
独立视觉准确率测试。6 个最后观测在预算取消后把视觉结果标为 unavailable/unknown，
没有发起新的 VLM 请求；这些有效失败仍计入分母。

## 核验和模型开销

160 个结果与末条原生状态一致，160 个 memory 审计通过，160 个 launcher 退出码为 0。
502 个固定源码哈希、148 个原版 memory 文件通过核对。
4059 条真实 VLM 请求审计：4050 个响应、9 个 API 错误；另有 6 次请求前取消。
所有实际请求均核对了任务输入白名单、四路相机和 4/8 张图像数量。
VLM 输入 23,192,795 tokens，输出 960,747 tokens，合计 24,153,542 tokens。
中位延迟 6.339 秒，p95 9.912 秒。这些用量不包含外层 Astra。
离线回归 291 项通过，完整 Agent 冒烟通过。

## 数据与复算

`data.json` 保存 160 组配对记录、来源哈希、配置、初态与计数；`episodes.csv` 提供平表。
`extract.py --help` 给出从本地原始运行目录复算的方法。
网页 ZIP 包含全部 160 局原生状态、结果、memory 审计、VLM 判断/请求审计及生产源码，
不含图像、视频、深度/world map、原始 Planner 流和机器日志；本地完整 ZIP 保留所有已保存
episode 产物及固定源码。两个包都包含内部 SHA-256 清单。
生产源码来自基底 fee5dfacb939ee1ca09220710d4586da9e5a5a41 加已记录工作树修改；
基底提交不等于最终评测代码。新实验分支尚未单独发布，ZIP 中提供源码快照与哈希。
