# SYSTEM-V1 软件 Goal 进度总表

**审计日期：** 2026-10-27
**本次闭环审计源 main：** `b5001381fe03b334dd21a7bb9cfdff2c0f42b10e`
**本次闭环审计源 CI：** [40362346948](https://github.com/guo6x/AI-rocket/actions/runs/40362346948)，`SUCCESS`
**范围：** 软件与离线证据；不包含硬件资格。

**软件目标状态：** `SYSTEM_V1_SOFTWARE_GOAL_COMPLETE`。这是一个绑定到上述 exact
source/CI 的日期快照；后续仅文档合并产生的 descendant SHA 不改变该软件行为结论。

| Goal | 当前状态 | 已交付的可复核证据 | 仍未完成/边界 |
| --- | --- | --- | --- |
| A：消除生产集成缺陷 | `TESTED_SOFTWARE` | PR #35 已修复串口 `[FLIGHT]`/启动日志/完整坏行污染；修复前 11/14、修复后 15/15；Ground Station 132 项通过。 | 同一物理串口行内多个 JSON 对象仍按生产换行边界处理，不扩展为无界扫描；真实串口仍未测。 |
| B：可重复软件端到端演示 | `PARTIALLY_VERIFIED` | 真实 Qt 应用回放：测试源 `main@00c68cd`（PR #36 合并前），`runtime_main_00c68_20261026/runtime_result.json`；31 运行断言、Qt exit 0、固定夹具、故障/中断/恢复/日志/命令拒绝；main CI 40362346948 重跑完整 gate 与 Qt fallback smoke。 | 原生 GPU/WGL 仍 `NOT_VERIFIED`；2D fallback 和显式软件 OpenGL 范围通过，不等于物理链路或飞控稳定性。 |
| C：接口与数据契约冻结 | `COMPLETED_OFFLINE_ONLY` | JSON↔R3 字段/单位/时钟/来源映射、R3.0–R3.2 负例与离线实验已合并。 | 生产适配、来源认证、真实采样年龄、反重放与真实 RF 仍未验证。 |
| D：工程交付质量 | `TESTED_SOFTWARE` | 单进程 `scripts/check.py`（证据源 `00c68cd…`；后续 main docs-only descendants 保留该收据）收据：526 次执行、516 个不同身份、10 次重复、五个源码构建通过；runbook/README 已提供第三方复现入口；main@b5001381 的 CI 40362346948 通过。 | Windows 原生 GPU、长期耐久和物理设备资源仍不在软件 gate 内。 |
| E：下一阶段准入门槛 | `BLOCKED_BY_EXTERNAL_EVIDENCE` | 回收不可达阈值、硬件资产/接口、CAD 测量门禁和安全边界均有记录。 | 需要独立安全评审、真实测量、板卡/传感器/执行器/RF 受控验证；不得静默改阈值。 |

## 当前收据索引

- 离线运行：`engineering/offline-evidence/system_v1/runtime_main_00c68_20261026/`
  - source SHA：`00c68cd84c485cfcd86103f5dd2f2c8b65b4c294`
  - fixture SHA：`2bbf67f3b9ffb2b4fd5fedabc21dabb25c59cd53c791d1d0ef567812a309560f`
  - `runtime_result.json` SHA：`a4fcb49b0eba8fb56dedb9f4f55c4d15946781dea146871410ad9dce8b13c060`
- 完整 gate：`engineering/offline-evidence/system_v1/full_check_main_00c68_20261026/`
  - `check_result.json`：exit 0，source SHA 同上；全量证据为 `TESTED_SOFTWARE`。
  - `full_check.log` SHA-256：`d9c592f26916b1c9c7fabdabe8d8e808a9644c14416294957b35b18cb52a968b`

## 软件闭环审计结论

上述 Goal A–D 的声明范围已具备可复核的软件证据：串口 framing/异常恢复已修复，
Ground Station 离线回放、故障/中断/恢复和发送隔离可重复运行，JSON↔R3 仅读离线
契约与 R3.0–R3.2 负例已冻结，完整软件 gate、五个源码构建和 main CI 均通过。

Goal E 不是软件完成条件：回收判据 `BLOCKED_UNREACHABLE_THRESHOLD`、原生 GPU/WGL、
真实传感器/ESP/RF/执行器、样本年龄/来源认证和 CAD 测量仍分别保持
`BLOCKED`/`NOT_VERIFIED`/`UNKNOWN`。这些边界不会因 `SYSTEM_V1_SOFTWARE_GOAL_COMPLETE`
而升级，也不关闭 Issue #22 或 Issue #23。

历史报告和旧 SHA 仍保留用于审计；不得把历史运行次数或历史 main 当作当前结果。
