# R2.5 | GNC/航电：从软件闭环到实物观测的最小准入

**范围：** 当前项目资产和分阶段计划的只读审计；非硬件验收、非飞行放行、非新的 TVC CAD。
**依据：** `engineering/assets/project-asset-registry.yaml`、`engineering/experimental-lines.yaml`、`engineering/bringup/gnc-avionics-bringup.yaml`、`engineering/current-baseline.yaml`、`engineering/cad-authority.yaml`、`engineering/as-built/measurement-plan.yaml`。历史报告只说明曾经演示的能力，不自动证明当前板卡/固件。

## 已经完成，不能重复立项

- S0 历史烧录、IMU、两舵机、WiFi/串口报告的来源与当前源码差异审计；
- S1 APM32/ESP-01S 实验性源码构建与目标兼容性梳理（非实物启动证明）；
- S2 最小回归需求；S2B `gnc_only_bench` 通过软件方式隔离回收逻辑；
- SYSTEM-V1 软件闭环、R2.3 生产 C++ 对照、R2.4 仿真极性差异归档。

绝不因为以上工作而将 `PENDING_HARDWARE` 升为 `VERIFIED_HARDWARE`。

## 机器可复核的当前入口

从仓库根目录运行：

```powershell
py -3 -m scripts.r2_5_entry_gate --json
py -3 -m pytest scripts/tests/test_r2_5_entry_gate.py -q
```

工具读取现有六份权威 YAML、调用既有 `r2_1_check` 结构验证、记录每份输入的 SHA-256，**不生成假定尺寸、不修改状态、不访问任何设备**。结果 `PASS_PREPARATION_ONLY` 仅表示准备资料与当前约束一致，**并非** `READY_FOR_HARDWARE`。出现缺失资产、伪造阶段完成、回收安全阻断被删、CAD 超前放行等情况将拒绝输出可执行的第一项人工交接。

## 第一处真正必须由现场人员提供的材料

来自当前已有的 `S2A-UNPOWERED-BOARD-OBSERVATION`：需要现有飞控板在**完全断电且未接外设**时的清晰正面照片，能够看见 MCU 标记与引脚丝印。只有正面无法确认具体版型时才补背面。照片及单板标识在后续人工审核时绑定到一份独立的原始证据记录；在照片出现前不得填造观测数据。此前历史烧录、传感器和舵机记录仍保留，不要求无条件重复。

这是一项**观测材料请求，不是通电、烧录、接线、舵机活动或自动控制授权**。采购记录足够支持当前软件工作，不需要催促更多采购。

## 下一阶段按阻断分组

| 模块 | 当前证据级别 | 从实物证据中仍缺什么 | 准入判断 |
|---|---|---|---|
| APM32 飞控板 | 采购已登记，实验性兼容构建通过 | 当前板卡标记、供电/接口审查、当前固件与版型绑定 | 先断电静态观测，其他动作独立审核 |
| GY-91 / MPU / BMP | 采购、历史 I²C 和软件身份检查 | 实物硅片身份、安装方向、有效性与采样性能 | 不从厂家名义参数推断实测 |
| 两只 SG92R | 两个采购单元 ID、历史 PWM、当前软件命令测试 | 独立单元标记、控制方向、中位、负载响应、受控台架安全条件 | 不以软件 Servo.write 证明实际运动 |
| ESP-01S | 当前源码构建、软件 ACK/NACK 仿真 | 当前板卡电源、串口、启动和真正端到端回传 | 不将 UDP 源关联等同身份认证 |
| 回收与失效处理 | FSM 软件测试 | 量程 ±2g 与严格 >2.5g 触发冲突，缺独立安全评审 | `BLOCKED_UNREACHABLE_THRESHOLD` 保留 |
| TVC 机械/CAD | 需求和测量计划存在 | EDF 当前型号、两只舵机与真实框架/基准的 CAD_START 19 项缺口 | `NOT_STARTED / BLOCKED_BY_MEASUREMENT` |

## 保留的边界

1. 不改变 PID 极性、增益、E-STOP、回收条件或执行器权限。R2.4 的符号差异只是数学证据，不能判断实物舵机/力矩符号。
2. 本阶段不进行通电、接线、烧录、无线电发射、舵机或 EDF 驱动及任何回收动作。
3. 实物照片只能证明所拍部件标识，不能证明板卡正常、传感器准确、舵机动作或系统稳定。
4. 后续物理阶段必须通过既有 `r2_1_check.py` 完整依赖链、配置/程序/结果/日期绑定门禁，不能用本工具直接跳过。
5. `engineering/current-baseline.yaml` 中的历史 SHA 和 CI 收据仍是各自时点记录；工具输出的输入哈希不能冒充当前 main 全量 CI。

**阶段性判定：** 软件准备可审计；首次断电观测待现场证据；后续带能硬件验证和 CAD 仍阻断。真实材料到位后才进入单独审查。
