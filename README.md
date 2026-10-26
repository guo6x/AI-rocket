# AI Rocket / Project Ad Astra

一个面向小型实验火箭与 EDF 涵道 TVC 测试台的软硬件协同项目，覆盖 STM32 飞控、ESP8266 遥测中继、Python 地面站、气动/动力学仿真及**历史 CAD 实验资料**。当前正式 CAD 尚未完成。

> **R0 authority notice:** 仓库包含多个年代、不同构型的历史产物。当前可采信状态、参数冲突、验证等级和已知问题以 [`engineering/`](engineering/) 为准；旧报告中的“完成”“验证”“最终”等措辞不能视作当前实物证据。

> **CAD 重要纠正（2026-10-25）：** 此前 AI 生成的 NX/STEP/STL/GLB/TVC/整箭模型已经被项目负责人否定，不存在当前可接受的正式 CAD、装配或制造放行。旧文件一律仅作历史资料，禁止直接打印、制造或当成当前尺寸基线。先阅读 [CAD 真实状态](engineering/cad-authority.yaml) 和 [CAD 清理/重建审计](docs/CAD_GROUND_TRUTH_RESET_2026-10-25.md)。

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
| `cad_automation/` | **不被接受的历史** NX/CAD 脚本和输出；非当前设计 |
| `3d_print_files/` | 未经认证的历史 STL/GLB/预览，仅供旧资料回溯；**禁止视为可打印制造件** |
| `tvc_design/`、`outputs/`、`pro_outputs*/` | 旧 AI 生成的 TVC 候选及 STEP/STL/GLB，已否定为当前设计 |
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

### SYSTEM-V1 确定性离线回放

不连接串口、UDP、无线电或飞控时，可直接运行仓库内现有的真实 PySide6
Ground Station 和固定回放夹具。完整步骤、证据字段和边界见
[SYSTEM-V1 离线回放运行手册](docs/SYSTEM_V1_OFFLINE_REPLAY_RUNBOOK.md)。

启动窗口后选择 **Offline Replay / 离线回放**，再使用开始、暂停、继续、重新开始
和停止。夹具 `ground_station/replay/system_v1.json` 的 SHA-256 为
`2bbf67f3b9ffb2b4fd5fedabc21dabb25c59cd53c791d1d0ef567812a309560f`，包含 18 个
固定事件：15 个有效样本、2 个传感器故障样本、1 个数据中断以及之后的恢复和回零。
这些值是显示/解析刺激，不是物理飞行或稳定性试验。

要保存一次可追溯的真实应用运行（输出目录必须是新的，以免覆盖历史证据）：

```powershell
$run = "engineering/offline-evidence/system_v1/demo_{0}" -f (Get-Date -Format yyyyMMdd_HHmmss)
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_OPENGL = "software"
.\.venv\Scripts\python.exe -u scripts/system_v1_runtime.py `
  --output $run --soak-minutes 0.05
```

运行器复用原解析器、仪表、曲线、日志和 2D/3D 视图，并在发送路径拒绝所有真实
命令；输出 `runtime_result.json`、截图和带 RAW/DICT 的遥测日志，记录源码/夹具/依赖
哈希及 `hardware_connections=0`、`radio_transmissions=0`、`control_sends=0`。
`--soak-minutes 0.05` 只是一段约 3 秒的短观察，不是长期稳定性证明；如需完整软件
回归，使用单进程 gate：

```powershell
$check = "engineering/offline-evidence/system_v1/check_{0}" -f (Get-Date -Format yyyyMMdd_HHmmss)
py -3 -u scripts/system_v1_check.py --output $check
```

该 gate 最终只给出 `TESTED_SOFTWARE` 证据等级。硬件、真实 RF、来源认证、传感器
采样年龄、原生 GPU/WGL 和飞行/执行器资格不会因回放或绿色测试而升级。

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

- 仓库暂时保留旧 AI CAD、STL/GLB 和仿真结果供历史审计；**不存在已完成的正式机械 CAD/制造装配**。
- 本机虚拟环境、PlatformIO 构建目录、遥测日志、调试日志和私有网络配置不会纳入版本控制。
- 部分 CAD 自动化脚本依赖 Siemens NX 或其他本机 CAD 环境。
