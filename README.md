# AI Rocket / Project Ad Astra

一个面向小型实验火箭与 EDF 涵道 TVC 测试台的软硬件协同项目，覆盖 STM32 飞控、ESP8266 遥测中继、Python 地面站、气动/动力学仿真、CAD 自动化与 3D 打印模型。

> **R0 authority notice:** 仓库包含多个年代、不同构型的历史产物。当前可采信状态、参数冲突、验证等级和已知问题以 [`engineering/`](engineering/) 为准；旧报告中的“完成”“验证”“最终”等措辞不能视作当前实物证据。

> 当前仍处于物理验证阶段。涉及电池、旋转部件、推进或飞行测试时，请遵守当地法规，并使用固定试验台、隔离区域、护目装备和可靠的紧急停机措施。

软件侧统一检查：安装 `requirements-dev.txt` 后运行 `python scripts/check.py`。该命令不执行实物测试，硬件项目始终单独标记为 manual / hardware-gated。

## 项目结构

| 路径 | 内容 |
| --- | --- |
| `flight_computer/` | STM32F103C8T6 飞控固件与 SIL 测试 |
| `esp8266_firmware/` | ESP8266 串口到 UDP 的遥测中继固件 |
| `ground_station/` | PySide6/pyqtgraph 地面站与测试 |
| `aero_sim/` | RocketPy 气动、弹道、参数扫描与 Monte Carlo 仿真 |
| `dynamics_sim/` | 2D/6DOF 动力学、PID 与重心影响研究 |
| `cad_automation/` | NX/CAD 自动化脚本及关键模型成果 |
| `3d_print_files/` | 可预览、可打印的 STL/GLB 模型 |
| `tvc_design/`、`outputs/`、`pro_outputs*/` | TVC 生成脚本及 STEP/STL/GLB 成果 |
| `reports/` | 各模块工程报告 |

详细的硬件状态、引脚分配和下一步计划见 [project-overview.md](project-overview.md)。

## 快速开始

### Python 仿真

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r aero_sim\requirements.txt
python aero_sim\run_simulation.py
```

### 地面站

```powershell
pip install -r ground_station\requirements.txt
python ground_station\main.py
```

### 固件

STM32 与 ESP8266 工程均使用 PlatformIO。ESP8266 编译前，可将
`esp8266_firmware/src/wifi_config.example.h` 复制为 `wifi_config.h`，再填写本地网络配置；该文件已被 Git 忽略，不会上传凭据。

```powershell
cd flight_computer
pio run

cd ..\esp8266_firmware
pio run
```

## 说明

- 仓库保留了关键 CAD、3D 打印和仿真结果，便于复现与查看。
- 本机虚拟环境、PlatformIO 构建目录、遥测日志、调试日志和私有网络配置不会纳入版本控制。
- 部分 CAD 自动化脚本依赖 Siemens NX 或其他本机 CAD 环境。
