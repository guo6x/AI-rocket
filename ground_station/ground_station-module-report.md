# 地面枢纽组 (Ground Station) - V0.3 模块报告

> **历史模块报告 / STALE：** R0 确认 UDP 遥测接收代码存在，但 WiFi 指令下行尚未端到端实现；下述“所有指令”描述不可作为当前能力证明。

## 完成事项
- **Phase 1-3**: PySide6 MVC 框架 + 串口后台接收 + JSON 解析 + 仪表盘 + PyQtGraph 实时波形图 + CSV 数据落盘。
- **Phase 5: WiFi/UDP 无线透传**: 新增 `core/udp_reader.py`，UI 支持"串口 Serial / WiFi UDP"双模式切换。选择 UDP 模式后只需填入监听端口号（默认 8888），即可接收 ESP8266 透传的无线数据。
- **Phase 6: TVC 指令下发面板**: 新增 `ui/command_panel.py`，包含 PID 三参调参 (Kp/Ki/Kd)、手动舵机角度滑杆 (0°-180°)、紧急停止 (E-STOP) 大红按钮。所有指令通过 JSON 格式经串口/UDP 反向发送到 STM32。**设有安全锁机制，默认锁定**。
- **Phase 7: 滤波对比图**: 新增 `ui/comparison_plot.py`，以 Tab 页的形式新开一个"Raw vs Filtered"四线对比曲线图（Pitch/Roll 各两条：虚线=原始、实线=滤波后），当 STM32 输出包含 `pitch_raw/pitch_flt/roll_raw/roll_flt` 字段时自动渲染。

## 运行方式
1. `cd d:\AI_rocket\ground_station`
2. `pip install -r requirements.txt` (如已安装可跳过)
3. `python main.py`

## 数据流协议约定

### 下行数据 (STM32 → PC)
```json
{"time":1234,"pitch":1.2,"roll":-0.5,"yaw":90.0,"alt":10.5,"batt":7.4}
```
如果启用了卡尔曼滤波，扩展为：
```json
{"pitch_raw":5.2,"pitch_flt":5.0,"roll_raw":-1.0,"roll_flt":-0.8,"alt":50.0,"batt":7.4}
```

### 上行指令 (PC → STM32)
```json
{"cmd":"set_pid","kp":1.2,"ki":0.01,"kd":0.5}
{"cmd":"set_servo","angle":90}
{"cmd":"estop"}
```

## 跨组依赖提示
- **[主脑控制组]** 需要在 STM32 端实现：串口接收并解析上行 JSON 指令、PID 驱动舵机、同时输出 raw/filtered 数据字段。
- **ESP8266 透传固件**：需要另开一个会话编写 Arduino 固件，让 ESP8266 将 STM32 串口1 的数据通过 WiFi UDP 广播到 PC。
