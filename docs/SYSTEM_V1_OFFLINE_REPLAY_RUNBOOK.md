# SYSTEM-V1 确定性离线回放运行手册

**范围：** 只读软件演示和回归。本文不授权接线、通电、烧录、射频发送、舵机/EDF
操作或飞控命令集成。证据上限是 `TESTED_SOFTWARE`；它不是硬件、通信范围、身份认证
或飞行资格证明。

## 1. 运行前提

在仓库根目录使用已有 Python 环境。不要为普通复核创建 Clone、worktree 或长期
耐久副本。若已经有项目虚拟环境，可按如下方式安装现有依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt `
  -r ground_station\requirements.txt -r aero_sim\requirements.txt
```

如果只需要交互窗口：

```powershell
.\.venv\Scripts\python.exe ground_station\main.py
```

在窗口顶部选择 `Offline Replay / 离线回放`，然后按顺序检查：

1. 开始：看到 `SIMULATION / OFFLINE REPLAY` 标识，仪表、姿态和曲线开始更新。
2. 暂停/继续：暂停期间游标和图表不追加，继续后从原位置恢复。
3. 故障：约 2–3 秒时出现传感器故障；显示冻结最后有效值，不补零。
4. 中断/恢复：约 4 秒开始数据空窗，约 7 秒恢复；状态从 `INTERRUPTION` 回到有效。
5. 重新开始/停止：新会话清理旧值和日志，停止后不再接收旧回放事件。

离线发送路径在 `MainWindow.on_send_command()` 内拒绝 ARM、AUTO、舵机、回收、
E-STOP、RESET 及未知命令；这不是单纯禁用按钮。串口/UDP reader 不会在离线入口
实例化。

## 2. 固定输入

输入文件是 [`ground_station/replay/system_v1.json`](../ground_station/replay/system_v1.json)，
来源字段必须为 `SIMULATION / OFFLINE REPLAY`，事件时间为递增的整数毫秒。当前固定
SHA-256：

```text
2bbf67f3b9ffb2b4fd5fedabc21dabb25c59cd53c791d1d0ef567812a309560f
```

夹具包含 18 个事件：15 个有效遥测对象、2 个显式 `sensor_valid=0` 故障事件、1 个
数据空窗，以及故障后的恢复、负姿态扰动和回零。它不包含命令，也不模拟真实动力学。

## 3. 可追溯运行收据

使用新输出目录运行真实 Qt event loop、原 UI 和原解析器：

```powershell
$run = "engineering/offline-evidence/system_v1/demo_{0}" -f (Get-Date -Format yyyyMMdd_HHmmss)
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_OPENGL = "software"
.\.venv\Scripts\python.exe -u scripts/system_v1_runtime.py `
  --output $run --soak-minutes 0.05
```

`--output` 必须不存在；这是为了保留历史证据，不是要求删除旧结果。成功收据至少
包含：

- `runtime_result.json`：源码 SHA、固定输入 SHA、依赖版本、命令、Qt 退出码、运行断言、
  结果哈希和硬件边界；
- `01_*.png` 至 `10_*.png`：真实窗口/控件抓取的启动、回放、故障、恢复、结束和
  2D/3D 降级画面；
- `telemetry/*.csv`：原 `DataLogger` 的 RAW/DICT 日志及 provenance 行。

`status=PARTIALLY_VERIFIED` 在原生 OpenGL/WGL 不可用时是诚实结果；2D Qt Painter
降级可以通过，但不能改写为 3D PASS。截图非空、Qt context 存在或调用 `paintGL()`
都不能单独证明可见 3D 绘制。

## 4. 完整软件 gate

用独立新目录运行单进程 gate：

```powershell
$check = "engineering/offline-evidence/system_v1/check_{0}" -f (Get-Date -Format yyyyMMdd_HHmmss)
py -3 -u scripts/system_v1_check.py --output $check
```

包装器只启动一个 `scripts/check.py`，保存 `environment.json`、`full_check.log`、
`test_inventory.json` 和 `check_result.json`。collection-only 清单不是执行次数；两个
GNC 文件在总 gate 中是重复执行组，报告时必须和不同测试身份分开。

## 5. 证据边界和故障排查

- `source_mode=SIMULATION / OFFLINE REPLAY` 是输入边界声明，不是传感器身份认证。
- 回放时间、飞控采样时间、发送时间、接收时间和墙钟时间保持不同；最近收到的帧不等于
  真实样本年龄。
- CRC、JSON 格式、序号或 session label 都不赋予控制权限；R3 二进制离线协议也没有
  自动接入现有 ESP 文本/JSON 链路。
- 回放和测试通过不解除 `BLOCKED_UNREACHABLE_THRESHOLD`、原生 GPU/WGL、真实 RF/ESP、
  传感器/执行器、CAD 测量等阻断。
- 若窗口无法创建，先记录 Python/Qt/平台版本和 `runtime_result.json` 的失败，而不是
  将空白窗口标为通过；已有 2D fallback 应继续保持可见。

当前基线、历史证据与最新 main/CI 由 [`engineering/current-baseline.yaml`](../engineering/current-baseline.yaml)
和 [`SYSTEM_V1_ACCEPTANCE_REPORT.md`](../SYSTEM_V1_ACCEPTANCE_REPORT.md) 统一维护。
