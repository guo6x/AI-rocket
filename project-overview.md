# Project Ad Astra — 项目现状总览

> **历史快照 / STALE：** 下述阶段与完成度未在 R0 中获得可重复实物证据。当前状态以 `engineering/` 为准。

> 最后更新：2026-05-13 | 当前阶段：**阶段六 — 物理验证期 (EDF 涵道 TVC 测试台)**

---

## 1. 已确定的硬件平台

| 组件 | 型号 | 状态 |
|---|---|---|
| **飞行控制器** | STM32F103C8T6 (Blue Pill) | ✅ 烧录运行中 |
| **IMU + 气压计** | GY-91 (MPU6500 变体 + BMP280) | ✅ I2C 通信正常 |
| **WiFi 透传** | ESP8266-01S | ✅ UDP 透传固件已烧录 |
| **TVC 舵机** | SG92R × 2 (PA6/PA7) | ✅ PWM 驱动验证 |
| **回收舵机** | SG92R × 1 (PB0) | ✅ 代码集成，待物理安装 |
| **地面站** | Python PyQtGraph (PC) | ✅ WiFi/串口双模接收 |
| **动力系统** | EDF 涵道风机 70/90mm (待采购) | ⏳ 物理组装阶段 |
| **飞行电池** | 6S LiPo (待采购) | ⏳ 待采购 |

## 2. 固件功能清单 (main.cpp v6)

- ✅ 裸机 I2C 驱动 MPU6500 + BMP280（无库依赖）
- ✅ 一维卡尔曼滤波器（pitch/roll 双轴，独立状态估计）
- ✅ JSON 遥测帧输出（USB 串口 + Serial2 → ESP8266 双通道）
- ✅ 上行指令解析：`set_servo` / `set_pid` / `estop` / `reset` / `auto_on` / `auto_off` / `arm` / `deploy_chute`
- ✅ PID 自动姿态稳定（`auto_on` 激活，当前参数：Kp=1.2, Ki=0.2, Kd=0.4）
- ✅ 降落伞回收状态机：BMP280 顶点检测 + 15s 定时器 + 地面指令三重冗余

## 3. 引脚分配表

| 引脚 | 功能 |
|---|---|
| PB6 / PB7 | I2C1 SCL/SDA → GY-91 |
| PA2 / PA3 | USART2 TX/RX → ESP8266 |
| PA9 / PA10 | USART1 TX/RX → CH340 调试 |
| PA6 | TIM3_CH1 → Servo Pitch (TVC) |
| PA7 | TIM3_CH2 → Servo Roll (TVC) |
| PB0 | TIM3_CH3 → Servo Recovery (拉销) |

## 4. 工具链

| 工具 | 用途 | 状态 |
|---|---|---|
| VS Code + PlatformIO | STM32 / ESP8266 固件开发 | ✅ 在用 |
| Python + PyQtGraph | 地面站 UI | ✅ 在用 |
| RocketPy (Python) | 气动/弹道仿真 | ✅ 已用于气动分析 |
| NX 12.0 + Python API | CAD 自动化建模 | ✅ 已验证（孵化为独立项目） |
| NX CAD / FreeCAD | 3D 打印件设计 | 待用于 EDF 机架 |
| ST-Link V2 | STM32 烧录/调试 | ✅ 在用 |
| CH340 USB转串口 | ESP8266 烧录 + STM32 调试监控 | ✅ 在用 |

## 5. 下一步：物理组装清单

| # | 任务 | 说明 |
|---|---|---|
| 1 | 采购 70/90mm EDF 涵道风机 + ESC | 动力核心 |
| 2 | 采购 6S LiPo 飞行电池 | 给涵道供电 |
| 3 | 设计/3D 打印矢量喷管机架 | 让 SG92R 偏转涵道 |
| 4 | 组装：底部涵道 + 中间管 + 顶部飞控 | 重心 ≤ 0.2m |
| 5 | 开启 `auto_on`，实物 PID 调参 | 初值 Kp=1.2, Kd=0.4（注意先加牵引绳！） |
| 6 | 受限悬停测试 | 牵引绳保护下推小油门 |

## 6. 关键技术结论存档

- **气动仿真**：基线箭体 75mm/600mm + 冯卡门 150mm 整流罩，稳定裕度 1.36 cal ✅。Estes D12/E12 推力不足（脱架速度 < 8m/s），**已转向 EDF 涵道方案**。详见 `reports/aero-sim-report.md`
- **PID 极限**：50ms 卡尔曼延迟 + SG92R 死区，高重心（0.5m）下全参数空间发散。重心压低至 ≤ 0.2m + 关节阻尼后可收敛，起始建议纯 PD 控制。详见 `reports/dynamics-module-report.md`
- **降落伞**：十字伞 100×35cm，SG92R 拉销 + 弹簧，三重触发冗余。详见 `reports/recovery-module-report.md`
