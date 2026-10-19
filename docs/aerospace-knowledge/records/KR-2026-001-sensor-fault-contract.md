# KR-2026-001｜传感器失效语义与虚拟设备边界

- 创建日期：2026-10-19；状态：**ANALYZED（源码与测试方案），NOT_REPRODUCED（未运行上游框架/飞控固件）**。
- 关联问题：Ad Astra \`R0-005\`、\`R1-002\`、\`R0-014\`。
- Ad Astra 审计锚点：\`44edda14982618627a020f1d8475ab6f750acb05\`。
- 上游版本：NOS3 \`5a3bdee6be9a2c67fdf994ae6db56d5c60395302\`（main）；NASA F´ \`1d70340caec1c4ce8092ccbdcbfc56fc8254e863\`（devel）。
- 技术用途：确定**离线虚拟传感器测试合同**，不形成动力、姿态控制或飞行放行建议。

## 1. 来自现有生产源码的可核实事实

| 观察 | 精确代码证据 | 工程含义 |
| --- | --- | --- |
| BMP280 \`begin\` 失败时输出 FAIL，但未停止后续每次高度读取 | [main.cpp L163-L173](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/flight_computer/src/main.cpp#L163-L173)，[L209](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/flight_computer/src/main.cpp#L209) | 设备初始化与“后续高度值可用”尚未通过一致的有效性机制关联 |
| 向 MPU 写配置后不检查 \`Wire.endTransmission()\` 结果，随后打印 \`MPU6500 OK\` | [main.cpp L172-L177](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/flight_computer/src/main.cpp#L172-L177) | “OK”目前只证明打印路径执行过，不能证明设备回应 |
| \`Wire.requestFrom(...,14)\` 后未检查实际可读长度，即进行七组双字节读取 | [main.cpp L212-L224](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/flight_computer/src/main.cpp#L212-L224) | 缺失字节可能传播为错误观测；\`Wire.read()\` 返回 -1 的错误路径未明确定义 |
| 原始值继续流向估计器、状态机与遥测，无逐样本有效性字段 | [main.cpp L227-L267](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/flight_computer/src/main.cpp#L227-L267) | 需要区分数值与数值可信性；不是仅靠打印“FAIL”解决 |

这些是**静态源码发现**，不是已经在硬件上诱发过的故障。设备是否真的缺席、读长异常如何在目标板表现、故障响应是否造成物理动作，均为 \`UNKNOWN\`。

## 2. 从 NOS3 / F´ 原始资料得到的具体方法

**NOS3 — 三层解耦**：[原始模拟器设计文档](https://github.com/nasa/nos3/blob/5a3bdee6be9a2c67fdf994ae6db56d5c60395302/docs/wiki/NOS3_Simulators.md#L1-L48) 分开：（A）硬件软件总线接口（如 I2C/UART）、（B）可以替换的硬件模型、（C）环境/传感真值数据提供者。该项目的[架构文档](https://github.com/nasa/nos3/blob/5a3bdee6be9a2c67fdf994ae6db56d5c60395302/docs/wiki/NOS3_Architecture.md) 进一步说明通过仿真设备访问与故障场景接口实现离线系统实验。注意原设计文档部分总线故障建模特性描述为未来能力，**不能据此宣称当前代码已经实现所有故障类型**。

**NOS3 — 明确故障发生条件与避免重启环路**：[故障场景](https://github.com/nasa/nos3/blob/5a3bdee6be9a2c67fdf994ae6db56d5c60395302/docs/wiki/Scenario_Fault_Science.md) 通过设备状态、任务模式、watch/action points 及故障响应形成可观察闭环，并明确警告循环重启风险。**不复制其卫星软件自动重启/恢复动作到本项目**；只提炼“触发条件—状态—日志—保护退出”的可测试合同。

**F´ — 组件显式接口和健康事件**：[Svc/Health/Health.fpp](https://github.com/nasa/fprime/blob/1d70340caec1c4ce8092ccbdcbfc56fc8254e863/Svc/Health/Health.fpp#L1-L120) 使用明确的 ping 输入/返回端口、可配置监控阈值、事件等级与遥测接口；说明健康检查应当以**单独可测模块/数据契约**表达。该例主要监控活动组件响应，**并不等于现成的 MPU/I2C 校验逻辑**。

## 3. 推荐的最低传感器合同（研究提案，未实现）

单条观测至少应包含：\`device_id\`、\`sample_time_monotonic\`、\`value\`、\`units\`、\`validity\`、\`fault_reason\`、\`sequence\` 和 \`source_mode={SIMULATED,PHYSICAL}\`；\`value\` 允许缺席，不用 0 替代设备不可读。此处 **不定义“真实系统应执行哪种舵机/回收动作”**，那必须由单独安全审查确认。

研究状态推荐：\`VALID\`、\`MISSING\`、\`SHORT_READ\`、\`STALE\`、\`NONFINITE\`、\`DEVICE_INIT_FAILED\`；以上为**提案枚举**，不是当前固件支持的状态。

| 测试编号 | 虚拟输入 | 预期软件可观察结果（拟定） | 不得得出的结论 |
| --- | --- | --- | --- |
| SENS-01 | 模拟设备完整有效一帧 | 值带时间、单位、\`VALID\` 与模拟来源 | 真实设备精度合格 |
| SENS-02 | 初始化显式失败 | \`DEVICE_INIT_FAILED\`，不得报告正常当前数据 | 物理故障响应已完成 |
| SENS-03 | 14 字节请求仅返回 0–13 字节 | \`SHORT_READ\`；不可用旧缓冲假装新观测 | I2C 线路稳定 |
| SENS-04 | 相邻采样超出时效窗口 | \`STALE\`，有时效证据与诊断 | 合理时效阈值已确定 |
| SENS-05 | 模拟数值为 NaN/Inf | \`NONFINITE\` 并拒绝当作有效观测 | 实机软件无其他浮点漏洞 |
| SENS-06 | 数据源跳变或序列回退 | 标明不连续，不悄然修改原始日志 | 系统整体控制稳定 |

阈值、采样率、错误转移、健康数据的记录和结构等仍需目标平台兼容性分析。现阶段以 native C++ 测试双层隔离实现，不连接任何真实控制输出。

## 4. 最小实现/验收与停止线

1. **先建无硬件依赖的读取抽象**与 fake stream，用固定字节序列模拟空读/短读/超时。
2. 用覆盖上述六种输入类别的回归测试锁定**数据有效性语义**；另审查与当前产品现有状态机的相容性。
3. 保证每次仿真样本和真实采样在遥测层可区分，默认纯软件路径不能驱动物理执行端。
4. 通过既有平台资源约束与原生测试后，另开实现 PR；不因本研究卡直接修改生产固件。
5. 硬件验证仍需独立授权和审查，软件通过不得将 \`R0-005/R1-002\` 标为 \`VERIFIED_HARDWARE\`。

**当前裁决：方法 \`TRANSFER_PROPOSED\`，实现 \`NOT_STARTED\`。** 适用研究仅限数据质量和验证架构。后续若要复用 NOS3 或 F´ 具体代码，须核对各自许可、子模块和平台资源，并对 NOS3 LICENSE 中既有文本疑点先澄清。
