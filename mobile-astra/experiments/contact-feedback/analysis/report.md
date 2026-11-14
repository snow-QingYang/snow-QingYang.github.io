# E04：移除 VLA 接触反馈，保留完整 task progress

2026-11-14 完成；32 个任务 × seeds 1–5，共 160 个有效 episode。

| 分组 | E01 baseline | 新版 E04 | 成功率差 |
|---|---:|---:|---:|
| Seen | 34/80 · 42.50% | 29/80 · 36.25% | -6.25 pp |
| Unseen | 21/80 · 26.25% | 15/80 · 18.75% | -7.50 pp |
| 总计 | 55/160 · 34.38% | 44/160 · 27.50% | -6.88 pp |

双方成功 24 局；仅 baseline 成功 31 局；仅新版 E04 成功 20 局；双方失败 85 局。

## 实验范围

仅从 rldx_skill / rldx_arm 返回中移除 grasp_contact、grasp_obj、grasped、grasp_detected，并停止对应的封装接触查询。

**完整保留所有原生 task_progress，包括接触派生条件。** 保留 held_apart、gripper_qpos、peak_lift、执行状态、几何查询、原版记忆、评分源码访问、simulator success 和 VLA 原生成功早停。无 VLM；提示词与控制预算保留原版设置。

GPT-6-Astra / xhigh；100 个模型响应、3600 秒每局；RLDX-1-FT-RC365，每次最多 40 chunks × 8 steps。

## 核验与限制

160 个结果逐一匹配末条原生 success；160 个进程退出码为 0；最终协议校验通过。扫描 4343 条观测、1869 条 VLA 动作记录，四个移除字段零命中。日志监控未记录显存不足或崩溃告警。

493 个源码文件哈希和 148 个原版记忆文件哈希通过核验；160 局 memory audit 均通过，涉及 95 个选中记忆文件。

E01 对照来自已发布的逐局导出；本次没有重新审计 E01 原始日志。任务文本有 3 对不同；未核对初始机器人及全部物体状态，不能沿用旧 E04 的初态检查数字。

单批差值不建立统计显著性或逐局因果关系。同 task/seed 不保证初态相同，VLA 动作采样也未固定。

## 版本与历史

评测提交：`092d8b8d344a7a0b2f8b6d5dd3bfae6a81342804`；分支 `no_contact_gt`；批次 `composite-nocontact-full-progress-3gpu-20261114-010523`。

本页 E04 已替换为保留完整进度的 44/160。旧 46/160 批次还过滤了 25 个任务、60 项接触派生进度，作为历史归档保存，不混入当前 160 局。

## 重新导出

`python extract.py --run RUN --site SITE_CHECKOUT --output OUTPUT`

RUN 需含原始 manifest、dynamic-control、results、冻结 source，且 manifest 指向原记忆审计文件。公开 ZIP 提供逐局结果、原生状态、记忆审计、生产源码和本报告；不包含模型原始对话、运行配置或凭据。
