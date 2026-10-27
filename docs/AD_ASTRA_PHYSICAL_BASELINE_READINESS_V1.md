# Project Ad Astra｜真实工程基线与系统集成准备 V1

**状态：`GOAL_BLOCKED_BY_PHYSICAL_EVIDENCE`**
审计日期：2026-10-27
仓库：`guo6x/AI-rocket`
审计基线：`main` `32d2c20658c1d5f83cb1ec720a9b6bf327dffb0b`

## 结论先行

本轮完成了软件基线、资产注册表、as-built/CAD 准入资料和回收判据的只读审计，并运行了现有的软件回归。软件系统仍保持 SYSTEM-V1 的既有能力；没有任何新的实体硬件、射频、执行器、推进或飞行证据。

当前目标不能在本地继续自主关闭：仓库没有可索引的实物照片、标签、发票、测量记录或 `engineering/evidence/records/` 记录。购买登记只能证明项目负责人记录了采购，不能证明当前实物身份、接口、安装、校准或可用性。

## 当前 GitHub 与软件状态

| 项目 | 实际状态 |
|---|---|
| `main` | `32d2c20658c1d5f83cb1ec720a9b6bf327dffb0b`，本地与 `origin/main` 一致，工作树干净（审计开始时） |
| 最新主线 CI | run `40372916700`，`PASS`，测试 SHA 与 `main` 一致：[Actions](https://github.com/guo6x/AI-rocket/actions/runs/40372916700) |
| Issue #22 | `OPEN`，CAD-V1 仍等待实测接口 |
| Issue #23 | `OPEN`，软件完成不等同于实体集成完成 |
| 硬件行为 | `NOT_EVALUATED`；本轮未接线、通电、烧录、发射射频或驱动执行器 |

本轮本地执行 `py -3 scripts/check.py`，退出码 `0`。实际结果为：Ground Station `132`、飞控 native `47`、GNC-only `4`、ESP relay `3`、脚本门 `211`、R2.3 oracle `5`、双周期 `5`、RF Lab `97`、研究回归 `22` 全部通过；`bluepill_f103c8`、`apm32f103c8_compat`、`gnc_only_bench`、`nodemcuv2`、`esp01_1m` 五个源码构建全部 `PASS`。这些是软件证据，不提升硬件证据等级。

## 资产与实物证据差异

`engineering/assets/project-asset-registry.yaml` 共登记 `23` 项，均为 `OWNED/PURCHASE_CONFIRMED`，依据是 owner-supplied `SRC-PURCHASE-2026-10-22` 采购记录。仓库没有对应的实物照片、标签或收货记录。

| 技术对象 | 当前可确认 | 不能据此确认 |
|---|---|---|
| APM32F103C8T6 控制板 | 采购类别；APM32 opt-in 软件兼容构建 | 芯片/板卡丝印、晶振、启动、引脚、电气状态、运行 |
| GY-91（订单写 MPU9250 + BMP280） | 采购类别；生产软件已做身份/有效性保护 | 实际芯片、地址、板向、校准、安装、读数 |
| ESP-01S | 采购类别；`esp01_1m` 软件构建 | 实际板型、闪存、供电、启动、UART、双向链路 |
| SG92R | 采购记录为 `2` 件；软件有双轴输出 | 两个 unit 的身份/尺寸/舵角/中立/负载；历史的第三个 recovery servo 没有当前采购证据 |
| SX1278 RA-02 与天线配件 | 采购类别；R3 只有离线协议实验 | 接头、天线匹配、合规性、真实链路 |
| EDF、电池、BEC/ESC、框架、云台、线束、紧固件 | 未形成当前实物证据；EDF 也不在资产注册表 | 型号、尺寸、质量、接口、安装和可制造性 |

`engineering/as-built/component-inventory.yaml` 有 `19` 个逻辑组件，但 `0` 个 `CONFIRMED_PRESENT`、`0` 个 `MEASURED`；`evidence-index.yaml` 为空，`engineering/evidence/records/` 不存在。不能把历史 `project-overview.md`、旧 wiring 叙述或被否决的 AI CAD 当作当前 as-built 证据。

## CAD_START 与 19 项缺口

`py -3 scripts/cad_baseline_gate.py --check` 返回审计 `PASS`，含义仅是“当前权威记录诚实地保持阻断”，不是 CAD 可开始。结果为：`CAD status=NOT_STARTED`、`CAD_START=BLOCKED`、`manufacturing_release=NOT_AUTHORIZED`、`accepted_current_models=0`。

当前 19 项 CAD_START 输入全部缺失或无证据：

`M-P0-EDF-01..04, M-P0-EDF-06..11`；
`M-P0-SERVO-01..06, M-P0-SERVO-08`；
`M-P0-STRUCT-01`；`M-P0-DATUM-01`。

测量计划总计 `40` 项，当前 `40/40 MISSING`。未取得这些记录前，不生成声称可制造的装配体，不引用历史 70/74/90 mm EDF 或历史 SG92R 几何填空。

## 回收安全独立审查

生产路径已在 `flight_computer/src/sensor_validity.cpp` 与 `flight_computer/src/flight_fsm.cpp` 中定位：

- `ACCEL_CONFIG=0x00`，加速度满量程为 `±2 g`，`az` 使用 `raw_az / 16384`；有符号 `int16` 的可表示最大绝对值为约 `2.0 g`（正端严格小于 `2.0 g`）。
- 发射判据是 `fabs(az) > 2.5f`，并要求连续样本；静态审计 `scripts/recovery_configuration_audit.py --json` 的结果为 `BLOCKED_UNREACHABLE_THRESHOLD`，`threshold_numerically_reachable=false`。
- 传感器读失败会锁存 fault，控制路径跳过 Kalman/PID 与回收 FSM；TVC 归中，E-STOP/RESET 和紧急部署命令仍按现有安全路径处理。循环 `delay(50)` 只是代码延迟，不是已测得的真实周期。
- 当前代码没有把量程饱和、卡死在端点或缓慢异常单独识别为可信故障；有限的饱和值可能仍是“数值有效”。因此不能把静态不可达误解为安全，也不能把修复可达性误解为回收资格。

可供独立安全评审的候选方案（本轮均未实施）：

1. **方案 A：扩大 IMU 量程后重新审查阈值。** 适用条件是确认传感器型号、噪声/分辨率、安装和量程配置，并完成兼容性与故障注入验证。副作用是分辨率、饱和行为和现有标定/阈值语义变化；需要更新配置、测试和硬件基线。
2. **方案 B：重新设计可达的检测量与判据。** 可在独立安全设计中评估多轴/变化率/高度等冗余信号及其滞回、超时和故障处理。副作用是误触发、延迟和状态机复杂度增加；需要独立 FMEA、回放、传感器故障注入和受控台架验证。
3. **方案 C：保持当前 fail-closed 阻断。** 在没有批准的设计变更和实体证据前，不改变量程、阈值或部署行为。副作用是自动回收能力继续不可用，但不会以软件改动掩盖安全缺口。

本轮选择并执行的是方案 C 的审查状态；没有修改生产阈值、E-STOP、控制增益、执行器权限或回收逻辑。

## 技术线准入矩阵

| 技术线 | 当前状态 | 证据上限 | 进入下一门的前提 |
|---|---|---|---|
| GNC / 飞控 | `TESTED_SOFTWARE`；历史实物能力保留为 `HISTORICALLY_DEMONSTRATED_REBASELINE_REQUIRED` | 离线源码/测试一致性 | 当前板卡、传感器身份/安装坐标、实测周期与受控台架记录 |
| 航电 / ESP | `TESTED_SOFTWARE`；硬件 `UNKNOWN` | 源码构建、协议与故障测试 | APM32/ESP-01S 标签与电气配置、非控制性链路验证 |
| RF | `PARTIAL_ASSET_SET` | 只读离线帧/可靠性/质量实验 | 合规的接口审查、接头/天线确认和另行批准的链路门 |
| TVC 机械 | `BLOCKED_BY_MISSING_MECHANICAL_INPUTS` | CAD/测量模板与 fail-closed gate | EDF、舵机、结构、线束和基准的观察/测量记录 |
| Recovery | `SOFTWARE_FOUNDATION_ONLY` | 静态不可达审计与软件状态测试 | 安全设计决定、传感器范围/故障证据和受控验证 |
| 系统集成 | `BLOCKED_BY_UPSTREAM_MATURITY` | 组件契约与软件回归 | 上述子系统分别通过准入，且有独立集成评审 |

## 最小人工资料清单

当前最小下一步不是通电实验，而是一批**不通电的实物观察资料**：

1. 按 `M-P0-STRUCT-01` 对所有拟纳入 `AA-TVC-BENCH-001` 的物件拍一组带比例尺的整体/正面/侧面/标签照片，并明确 `PRESENT`、`NOT_PRESENT` 或 `UNKNOWN` 及是否复用。
2. 若照片确认 EDF、两只 TVC 舵机和现有结构确实存在，再按现有 `M-P0-EDF-*`、`M-P0-SERVO-*`、`M-P0-STRUCT-02`、`M-P0-DATUM-01` 模板补齐无通电尺寸、孔位、线缆出口和基准记录；不要用历史 CAD 数值替代。
3. 将记录放入 `engineering/evidence/records/`，每条包含日期、具体物件 ID、工具、单位、不确定度、照片路径和 SHA-256；由独立工程审查后再改变 gate 状态。

在这些输入出现前，不能进入正式 CAD_START、TVC 运动、功率架构、真实通信、回收或系统集成验证。

## 可复核证据

- 资产/实物基线：`engineering/assets/project-asset-registry.yaml`、`engineering/as-built/**`、`engineering/component-status.yaml`、`engineering/experimental-lines.yaml`。
- CAD 准入：`engineering/cad-authority.yaml`、`engineering/as-built/measurement-plan.yaml`、`scripts/cad_baseline_gate.py`、`scripts/r2_physical_baseline_check.py`。
- 回收审查：`scripts/recovery_configuration_audit.py`、`docs/RECOVERY_LOGIC_SAFETY_CHANGE_PROPOSAL.md`、`engineering/known-issues.md`。
- 软件门与历史证据：`engineering/current-baseline.yaml`、`engineering/offline-evidence/system_v1/**`、`engineering/offline-evidence/r2_3/**`、`engineering/offline-evidence/r3/**`。
- 本轮静态审计输出哈希见 `engineering/offline-evidence/physical_baseline_readiness_v1/manifest.json`。

因此本 Goal 的最终状态为：`GOAL_BLOCKED_BY_PHYSICAL_EVIDENCE`。这表示准入准备资料已整理、软件基线可复核，并不表示任何实体硬件、无线链路、执行器、回收机构或飞行资格已验证。
