# 飞控软件架构 (main.cpp v6 实际实现)

> 状态：**已实现并烧录运行** | 文件：`d:\AI_rocket\flight_computer\src\main.cpp`

---

## 1. 飞行状态机

```
上电 → IDLE
  → arm 指令 → ARMED（校准地面高度基准）
    → 检测到离地 Δh > 10m → COAST（滑行段）
      → 连续 5 次高度递减 → DEPLOYED（开伞）
```

指令触发路径（地面站手动）：`deploy_chute` → 直接 DEPLOYED

---

## 2. 主循环结构 (20Hz，50ms/帧)

```
loop()
  ├─ 0a. 读 Serial2 指令（ESP8266 → 地面站上行）
  ├─ 0b. 读 Serial 指令（USB 调试端直接输入）
  ├─ 1.  ESTOP 检查（如果停机，跳过后续）
  ├─ 2.  读 MPU6500（裸机 I2C，9轴原始值）
  ├─ 3.  读 BMP280（气压→高度）
  ├─ 4.  姿态解算（atan2 → pitch_raw / roll_raw）
  ├─ 5.  卡尔曼滤波（→ pitch_flt / roll_flt）
  ├─ 6.  回收状态机检测（顶点检测 + 定时器）
  ├─ 7.  PID 控制（auto_mode=true 时驱动 TVC 舵机）
  └─ 8.  JSON 遥测输出（Serial + Serial2）
```

---

## 3. 指令协议（纯文本，换行结尾）

| 指令 | 格式 | 说明 |
|---|---|---|
| `set_servo` | `set_servo:45,135` | 手动设置 Pitch/Roll 舵机角度 (0~180) |
| `set_pid` | `set_pid:1.2,0.2,0.4` | 动态调整 PID 参数 |
| `estop` | `estop` | 紧急停机，舵机归中，遥测停止 |
| `reset` | `reset` | 解除停机，恢复输出 |
| `auto_on` | `auto_on` | 开启 PID 自动姿态稳定 |
| `auto_off` | `auto_off` | 关闭 PID，舵机归中 |
| `arm` | `arm` | 进入待发射，校准地面高度 |
| `deploy_chute` | `deploy_chute` | 手动触发开伞 |

---

## 4. JSON 遥测帧格式

```json
{
  "time": 123456,
  "pitch_raw": -6.39,
  "pitch_flt": -6.21,
  "roll_raw": -130.04,
  "roll_flt": -129.87,
  "yaw": -1.05,
  "alt": 142.73,
  "auto": 0,
  "chute": 0,
  "rec": "IDLE",
  "batt": 7.4
}
```

---

## 5. PID 控制器

- **当前参数**：Kp=1.2, Ki=0.2, Kd=0.4（比动力学仿真安全边界值激进，实物调参时先加牵引绳）
- **仿真建议的保守起点**：Kp=0.58, Ki=0.0, Kd=0.15（50ms 延迟下的稳定边界）
- **积分限幅**：±30°（防饱和）
- 开伞后自动退出 PID，TVC 舵机归中

---

## 6. 回收系统

- **引脚**：PB0（TIM3_CH3）→ SG92R 回收舵机
- **锁定位**：90°（阻挡销插入）
- **触发位**：0°（拔出阻挡销，弹簧弹出鼻锥）
- **三重触发冗余**：
  1. BMP280 顶点检测（连续 5 帧高度递减）
  2. `arm` 后 15s 定时器强制触发
  3. 地面站 `deploy_chute` 指令
