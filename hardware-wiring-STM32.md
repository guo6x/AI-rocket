# 硬件接线参考 (STM32 + GY-91 + ESP8266)

> 状态：**已验证通电，实际生产接线**

---

## 接线总表

### GY-91 → STM32 (I2C)

| GY-91 | STM32 | 说明 |
|---|---|---|
| VIN | 5V | 板载 LDO 稳至 3.3V |
| GND | GND | 共地 |
| SCL | **PB6** | I2C1_SCL |
| SDA | **PB7** | I2C1_SDA |

> NCS / SDO 等悬空不接。

### ESP8266-01S → STM32 (UART2)

| ESP8266 | STM32 | 说明 |
|---|---|---|
| VCC | 3.3V (面包板供电模块) | ⚠️ 只能 3.3V，接 5V 必烧 |
| GND | GND 共地轨道 | |
| EN | 3.3V | 必须拉高才能启动 |
| TX | **PA3** (USART2_RX) | ESP发 → STM收 |
| RX | **PA2** (USART2_TX) | STM发 → ESP收 |

> ESP8266 单独用面包板供电模块的 3.3V 供电（不从 STM32 板上取），避免电流不足导致反复重启。

### CH340 (USB转串口) → STM32 (UART1，调试用)

| CH340 | STM32 | 说明 |
|---|---|---|
| RX | **PA9** (USART1_TX) | 调试监控/指令输入 |
| TX | **PA10** (USART1_RX) | |
| GND | GND 共地轨道 | |

### 舵机接线

| 舵机 | 引脚 | 功能 |
|---|---|---|
| Servo Pitch (橙线信号) | **PA6** | TVC Pitch 轴 |
| Servo Roll (橙线信号) | **PA7** | TVC Roll 轴 |
| Servo Recovery (橙线信号) | **PB0** | 降落伞拉销 |
| 全部红线 | 面包板 5V 轨 | 舵机电源（从 STM32 USB 5V 引出） |
| 全部棕线 | 面包板 GND 轨 | |

---

## 供电拓扑

```
电脑 USB
  ├─→ STM32 Micro-USB（供电 + 5V 轨给舵机）
  └─→ CH340 USB（串口监控）

面包板供电模块（独立）
  ├─→ 3.3V 轨 → ESP8266 VCC + EN
  └─→ GND 轨 → 共地
```

---

## 烧录模式（ESP8266 专用）

| 步骤 | 操作 |
|---|---|
| 1 | 拔 USB 断电 |
| 2 | IO0 接 GND（拉低） |
| 3 | 插 USB 上电 → 自动进入 Flash 模式 |
| 4 | PlatformIO Upload |
| 5 | 拔 IO0 那根线，拔插 USB 重启 |

---

## 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| ESP8266 蓝灯狂闪复位 | 3.3V 电流不足 | 用独立面包板供电模块，不从 STM32 取 3.3V |
| 串口无输出 | CH340 TX/RX 接反 | PA9↔TX，PA10↔RX 确认 |
| I2C 扫描无设备 | SDA/SCL 接线错 | 检查 PB6(SCL) PB7(SDA) |
