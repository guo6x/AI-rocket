# KR-2026-006｜Ad Astra 仿真符号、极性与控制周期差异：源码静态审查

> 2026-10-29 | 状态：**SOURCE_ANALYZED / BLOCKED_BY_PHYSICAL_DATUM**。本卡只审查不同历史仿真代码的数学与接口约定，**不进行控制器参数推荐、真实舵机方向设定或实物试验**。  
> 审查主分支：\`AI-rocket@bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2\`。  
> 对应 \`R0-008\`（模型符号约定冲突）、\`R0-006\`（PID 未实物验证）、\`R0-007\`（物理数据缺失）。

## 对照源码与实际读到的事实

| 模块 | 代码出处 | 在当前数学模型内的方向与时间假设 | 裁决 |
| --- | --- | --- | --- |
| 1D 物理对象 | [\`dynamics_sim/physics_engine.py\`](https://github.com/guo6x/AI-rocket/blob/bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2/dynamics_sim/physics_engine.py) | \`theta>0\` 为顺时针；\`tau_thrust=-F*Lt*sin(servo_angle)\`。正舵角在正推力的这个数学约定下贡献**负**力矩 | 对象级方程明确；物理装配方向未测 |
| 1D 网格扫描 | [\`dynamics_sim/param_sweep.py\`](https://github.com/guo6x/AI-rocket/blob/bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2/dynamics_sim/param_sweep.py) | \`DiscretePID.compute(setpoint, measured)\` 的 error=\`setpoint-measured\`；其主循环调用 \`servo.command(pid.compute(0,measured,t))\`，**不翻转输出** | 与上述力矩方向组成的闭环符号值得警惕；不是实物认定 |
| 1D 极性示范 | [\`dynamics_sim/test_polarity.py\`](https://github.com/guo6x/AI-rocket/blob/bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2/dynamics_sim/test_polarity.py) | \`cmd_angle=-pid.compute(0,measured,t)\`，明确翻转符号 | 与 \`param_sweep.py\` 的数值接口方向不同 |
| 1D 重心研究 | [\`dynamics_sim/cg_impact_study.py\`](https://github.com/guo6x/AI-rocket/blob/bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2/dynamics_sim/cg_impact_study.py) | 同样 \`cmd_angle=-pid.compute(...)\` | 与极性示范一致；物理参数仍是假设 |
| 2D 控制器 | [\`dynamics_sim/physics_engine_2d.py\`](https://github.com/guo6x/AI-rocket/blob/bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2/dynamics_sim/physics_engine_2d.py) | \`error=current\`；正测量产生正的 PID P 项；正舵角在同一负力矩假设下为抵消项 | 与 1D 翻转后方向逻辑相容，但不是实物有效证据 |
| 2D 时间步 | 同上 \`run_2d_test\` | 动力学 \`dt=0.001s\`，PID 每 \`step_i % 10 == 0\` 更新一次，**即实际 100 Hz**。文件部分历史注释/打印文案仍出现 1kHz PID 的描述 | 应以实际代码/时序证据为准，避免用旧文字推断采样频率 |

## 用初等数学检查“负反馈”方向（只检查抽象符号）

在假设推力正值 \`F>0\`、力臂 \`Lt>0\` 且与该 1D 代码符号定义一致的数学系统中：

\`\`\`text
theta > 0                      # 正角度偏差
e = 0 - theta < 0              # PID 的常见 setpoint-minus-measured 误差
Kp > 0 => PID P项 < 0
servo = PID P项 < 0            # param_sweep 的直传路径
tau_thrust = -F*Lt*sin(servo) > 0
\`\`\`

于是对 \`theta>0\`，控制力矩 **也为正**，不抵消正向重力倾覆力矩。这说明：**在这个代码级数学约定和局部 P 项占主导的情况下，\`param_sweep.py\` 的直传极性不是所预期的负反馈方向**。反过来，\`test_polarity.py\` 显式将该输出取反，可以形成数学模型期望的相反力矩。

**重要限制**：具体时刻的完整 PID 输出受初始条件、I/D、限幅和速率限制影响；实际设备中“舵机正转”与“喷流向量正转”的机械映射、安装朝向、坐标变换、执行器中位和真实力矩方向都仍是 \`UNKNOWN\`。不允许把这里的符号推导直接当作实际接线/调参指令。

## 对已有仿真结果的影响

- \`param_sweep.py\` 的历史“最优参数”不能与 \`cg_impact_study.py\`、\`test_polarity.py\` 直接同组排名；它们在符号、假设质量、重心、推力、传感器/执行器模拟与 PID 更新周期上并不完全一致。
- 在任何比较前，首先冻结**同一模型、同一误差定义、同一单元、同一状态及输入输出极性**；下一步再讨论数值方法和结果可复现。
- 代码和文档的更新时间不同，过去结果不应在来源缺失时自动升级为现行物理构型的工程事实。
- **此研究不会修改任何现有仿真脚本或控制参数**，也不代表已有物理系统中存在经实测确认的“正反馈问题”。

## 建议建立的“方向合同”最小字段（今后拟定）

\`reference_datum\`、\`theta_positive_direction\`、\`measured_angle_frame\`、\`error_sign\`、\`PID_output_sign\`、\`servo_command_sign\`、\`actuator_to_vector_sign\`、\`vector_to_body_torque_sign\`、\`units\`、\`update_frequency_hz\`、\`model_version\`、\`physical_confirmation_status\`。

最后的字段必须始终如实保留 \`UNKNOWN\`，直到有独立、可追溯的实物测量与专项评审。

## 课程联系

这不是“把 PID 公式背熟”就能解决的问题。它串联了：
- **控制工程基础**：负反馈的符号与闭环可比性；
- **机械振动基础**：倒立摆的线性/非线性响应及阻尼；
- **机械工程测试技术**：输入输出实际量测与数据有效性；
- **飞行器设计/系统工程**：坐标基准、接口合同和验证证据。

当前裁决：保留 \`R0-008\` 与硬件验证门禁；只有在软件合同与物理几何/方向量测齐备后才考虑进一步工程决策。
