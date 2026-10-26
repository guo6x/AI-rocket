# SYSTEM-V1 软件 Goal 进度总表

**审计日期：** 2026-10-27
**当前 main：** `9f202c5f279676c02cd6d0f1ef3e4f71e573b647`
**最新 main CI：** [40355328266](https://github.com/guo6x/AI-rocket/actions/runs/40355328266)，`SUCCESS`
**范围：** 软件与离线证据；不包含硬件资格。

| Goal | 当前状态 | 已交付的可复核证据 | 仍未完成/边界 |
| --- | --- | --- | --- |
| A：消除生产集成缺陷 | `TESTED_SOFTWARE` | PR #35 已修复串口 `[FLIGHT]`/启动日志/完整坏行污染；修复前 11/14、修复后 15/15；Ground Station 132 项通过。 | 同一物理串口行内多个 JSON 对象仍按生产换行边界处理，不扩展为无界扫描；真实串口仍未测。 |
| B：可重复软件端到端演示 | `PARTIALLY_VERIFIED` | 真实 Qt 应用回放：测试源 `main@00c68cd`（PR #36 合并前），`runtime_main_00c68_20261026/runtime_result.json`；31 运行断言、Qt exit 0、固定夹具、故障/中断/恢复/日志/命令拒绝。 | 原生 GPU/WGL 仍 `NOT_VERIFIED`，2D fallback PASS；不等于物理链路或飞控稳定性。 |
| C：接口与数据契约冻结 | `COMPLETED_OFFLINE_ONLY` | JSON↔R3 字段/单位/时钟/来源映射、R3.0–R3.2 负例与离线实验已合并。 | 生产适配、来源认证、真实采样年龄、反重放与真实 RF 仍未验证。 |
| D：工程交付质量 | `TESTED_SOFTWARE` | 单进程 `scripts/check.py`（证据源 `00c68cd…`，PR #36 合并后 main `9f202c5…`）收据：526 次执行、516 个不同身份、10 次重复、五个源码构建通过；runbook/README 已提供第三方复现入口；合并后 CI 40355328266 通过。 | Windows 原生 GPU、长期耐久和物理设备资源仍不在软件 gate 内。 |
| E：下一阶段准入门槛 | `BLOCKED_BY_EXTERNAL_EVIDENCE` | 回收不可达阈值、硬件资产/接口、CAD 测量门禁和安全边界均有记录。 | 需要独立安全评审、真实测量、板卡/传感器/执行器/RF 受控验证；不得静默改阈值。 |

## 当前收据索引

- 离线运行：`engineering/offline-evidence/system_v1/runtime_main_00c68_20261026/`
  - source SHA：`00c68cd84c485cfcd86103f5dd2f2c8b65b4c294`
  - fixture SHA：`2bbf67f3b9ffb2b4fd5fedabc21dabb25c59cd53c791d1d0ef567812a309560f`
  - `runtime_result.json` SHA：`a4fcb49b0eba8fb56dedb9f4f55c4d15946781dea146871410ad9dce8b13c060`
- 完整 gate：`engineering/offline-evidence/system_v1/full_check_main_00c68_20261026/`
  - `check_result.json`：exit 0，source SHA 同上；全量证据为 `TESTED_SOFTWARE`。
  - `full_check.log` SHA-256：`d9c592f26916b1c9c7fabdabe8d8e808a9644c14416294957b35b18cb52a968b`

历史报告和旧 SHA 仍保留用于审计；不得把历史运行次数或历史 main 当作当前结果。
