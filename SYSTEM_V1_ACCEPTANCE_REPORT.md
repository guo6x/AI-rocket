# AI-rocket SYSTEM-V1 软件系统验收

日期：2026-10-25。交付为待独立复核的功能分支，**不是已经进入 main 的发布版本，也不是硬件验收**。

## 结论与版本

当前总状态：`PARTIALLY_VERIFIED`。已有地面站已复用并接入确定性、只读离线回放；CI 和实际应用运行的证据分别记录，不以单元测试替代运行验收。可运行的仪表、曲线、日志与只读回放已取得实际应用证据；可见 3D 尚未验证。

| 项目 | 版本 / 状态 |
| --- | --- |
| 重新 fetch 后确认的 main | `03fbd826031f24055bf5de79c7aa4aa72810b451` |
| 已有功能盘点锚点 | `50006f8fd6830a34f16b5e9d2f4e84269c403007` |
| PR #24 修复后 head | `70c768de915fa7bd090aa5ad59d5db7d0affd0f5` |
| 运行 / 回归源码提交 | `16a37c3be0528f51cf152419e6907763a95b4ee4` |
| 交付分支 | `feat/system-v1-offline-integration-20261025` |
| Draft PR | [#25](https://github.com/guo6x/AI-rocket/pull/25)，叠在 PR #24 分支上，不直接替代 main |
| PR #24 | [完整软件 CI](https://github.com/guo6x/AI-rocket/pull/24)，保持 Draft / 等待独立复核 |
| 本地完整回归 | `PASS` / exit 0：23/23 检查组，419 次执行 / 409 个不同测试身份，五构建通过 |
| 实际 Windows UI | `PARTIALLY_VERIFIED` / Qt 退出 0：30 个运行检查点（含 10 次截图保存检查），3D 明确降级；`runtime_v2/runtime_result.json` |

本报告所在的最终 evidence commit 可以晚于上述源码提交。最终提交号由 `git rev-parse HEAD` 与 PR head 提供；不在文件中伪造自引用 SHA。源码、输入和输出各自的 SHA256 在证据清单中绑定。

## S0：真实 CI，不沿用历史的 379 次执行

已完整读取 Issue #23、PR #24 与其失败日志；PR #21 仍暂缓，Issue #22 CAD-V1 不在本次修改范围。

| 运行 | 实际执行 SHA（PR synthetic merge） | 结果 / 原因 |
| --- | --- | --- |
| [40163661917](https://github.com/guo6x/AI-rocket/actions/runs/40163661917) | `dc65e7531d0f49b7076d464a237a9cf546bec96b` | `FAIL`：GS 64 项断言通过后进程崩溃；三个 STM32 系构建因 Serial2 类型冲突失败 |
| [40166887126](https://github.com/guo6x/AI-rocket/actions/runs/40166887126) | `7670dd754f9cc49604d83401d334a1afa60ae0f0` | `FAIL` / gate exit 1：五构建已通过；Qt 生命周期清理后仍有 `bool_dealloc` 退出崩溃 |
| [40167326817](https://github.com/guo6x/AI-rocket/actions/runs/40167326817) | `a2f05c348c770da01f27415f6ede04d89b906e10` | `PASS` / exit 0：23/23 检查组、五构建、GS 进程正常退出 |

通过运行的 synthetic merge parents 已通过 GitHub API 核对：base 是 main `03fbd826...`，head 是 PR #24 的 `70c768de...`。不是把 PR head 当成执行 SHA。**main 本身尚未获得这些修复；没有合并任何 PR。**

两类最小修复：

- STM32 Arduino core 3.0.0 将串口具体类型改为 `Uart`。声明使用 `decltype(Serial2)`，并复用明确启用的框架实例；保留 USART2、引脚、波特率、命令和控制行为，native fake 仍使用原类型。
- PySide6/shiboken6 6.12.0 在 Ubuntu / CPython 3.11.17 下断言通过后发生引用计数退出崩溃。测试对象生命周期显式清理**单独未解决**。固定 PySide6 6.10.2 后同一 Python 与完整断言通过。此为已验证依赖配置约束，不是上游根因证明；没有忽略非零退出、删除测试或更换 Python 来掩盖问题。

S0 环境：Ubuntu 24.04.5，Python 3.11.17，PlatformIO 6.2.0，PySide6/shiboken6 6.10.2，pyqtgraph 0.14.0，numpy 2.4.6，pytest 9.1.1。完整依赖清单见 CI 的 `system-v1-environment.txt`。

集成分支随后也取得实际托管通过：[40168290228](https://github.com/guo6x/AI-rocket/actions/runs/40168290228)，执行 merge `dac49b14d6ebdc689c6495e24396a16473147a41`，parents 是 base `70c768de915fa7bd090aa5ad59d5db7d0affd0f5` 与源码 head `16a37c3be0528f51cf152419e6907763a95b4ee4`。23/23 检查组、五构建、exit 0；GS 增至 91，完整 **419 次测试执行 / 409 个不同测试身份**，零失败。该运行的五构建容量与下表相同；CI 日志 SHA256：`56cc67f82e5adf8a6ff7c4b9c85ff8970379cae3bb8abc620a2af8fbce683eb0`。

S0 测试执行：GS 64 + Flight native 47 + GNC-only 4 + ESP native 3 + scripts 157 + GNC oracle 5 + dual-period 5 + RF 85 + research 22 = **392 次执行 / 382 个不同测试身份**。两个各 5 项的 GNC 组已在 scripts 157 中运行，不能再次算成不同用例。54 个 native 函数已从日志解析核对无重名重复。烟测、结构审计、demo 和构建不再冒充 pytest 用例数。

S0 五构建（字节，非运行占用实测）：

| 目标 | RAM | Flash | 结果 |
| --- | ---: | ---: | --- |
| bluepill_f103c8 | 3064 / 20480 | 55860 / 65536 | PASS |
| apm32f103c8_compat | 3064 / 20480 | 55860 / 65536 | PASS |
| gnc_only_bench | 3064 / 20480 | 55292 / 65536 | PASS |
| nodemcuv2 | 28328 / 81920 | 273159 / 1044464 | PASS |
| esp01_1m | 28328 / 81920 | 273159 / 761840 | PASS |

APM32 仍是 STM32-core 兼容 target，不是已证实的原生移植。ESP-01S 构建不证明实际 Flash、供电、启动脚或无线链路。

### 本地最终单 gate 运行

命令：`py -3 -u scripts/system_v1_check.py --output engineering/offline-evidence/system_v1/full_check_16a37c`，包装器实际串行启动 `scripts/check.py`，完整退出 0。没有并行启动另一个 check 或构建。测试身份收集也全部退出 0，但不算成测试执行。

| 测试组 | 实际通过 / 失败 | 去重说明 |
| --- | ---: | --- |
| Ground Station | 91 / 0 | 原64 +27项必要边界/集成测试 |
| Flight C++ native | 47 / 0 | Unity 日志逐项列出 |
| GNC-only native | 4 / 0 | 原 main 的恢复输出隔离 |
| ESP relay native | 3 / 0 | 无设备 helper 测试 |
| scripts/tests | 157 / 0 | 包含以下两个 GNC 组 |
| GNC C++ / Python oracle | 5 / 0 | 重复执行，非新增身份 |
| GNC dual-period | 5 / 0 | 重复执行，非新增身份 |
| RF R3.0–R3.2 | 85 / 0 | unittest 实际计数 |
| 保留研究回归 | 22 / 0 | pytest 实际计数 |
| 合计 | **419 / 0** | **409 个不同身份，10 次重复执行** |

另外，syntax、engineering YAML、CAD authority bookkeeping、simulation smoke、R2/R2.1 结构、recovery advisory、R3.1 experiment 和 R3.2 demo 均通过。它们不是新增的 pytest 测试数。`BLOCKED` 的物理/CAD/recovery 状态仍由这些审计正常报告，不被 gate exit 0 升级。

本地五构建全部 PASS，容量字节：

| 目标 | 本地 RAM | 本地 Flash |
| --- | ---: | ---: |
| bluepill_f103c8 | 3060 / 20480 | 55160 / 65536 |
| apm32f103c8_compat | 3060 / 20480 | 55160 / 65536 |
| gnc_only_bench | 3060 / 20480 | 54592 / 65536 |
| nodemcuv2 | 28296 / 81920 | 273147 / 1044464 |
| esp01_1m | 28296 / 81920 | 273147 / 761840 |

本地采用已安装的 ststm32 19.4.0 / Arduino core 2.11.0；托管为 ststm32 20.0.0 / core 3.0.0，故不得混用两套构建容量。此轮 source 同时经过两套框架源码构建，但没有上传固件。

本地 `full_check.log` SHA256：`574695821d78d5cd8bc6fa075cd20dd237c550703adae833577477f2357adff1`。环境与依赖完整清单、PlatformIO 信息和真实 source SHA 在同目录 `environment.json`；不同于 UI 的 `.venv`，本次 `py -3` 使用 Windows 系统全局 Python 3.13.1、PySide6/shiboken6 6.9.0、numpy 2.1.3、pyqtgraph 0.14.0、pytest 8.0.0、PlatformIO 6.1.19，不将其冒充与 CI 相同的环境。已安装的 6.9.0 在本次 Windows 全门正常退出，不是新安装依赖的推荐约束；托管与最终 UI 运行均使用固定的 6.10.2。

## S1：先复用，再补输入边界

完整已有能力矩阵见 [SYSTEM_V1_CAPABILITY_MATRIX.md](docs/SYSTEM_V1_CAPABILITY_MATRIX.md)，固定到盘点源码，使用 `IMPLEMENTED / TESTED_SOFTWARE / NEEDS_INTEGRATION / BLOCKED / HISTORICAL / UNKNOWN`，没有将旧功能重新开发。

复用：PySide6 主窗口、原 JSON 解析器、仪表盘、高度/俯仰实时曲线、四条 raw/filtered 曲线、原简化 3D 方盒、命令状态机、串口/UDP reader 与 DataLogger。

新增的仅为：固定 synthetic 时间线、QTimer 输入源、原 UI 内四个回放控制、醒目标识和发送/连接入口拒绝。没有新 UI 框架、CAD 外形、无线驱动或飞控指令集成。

### 启动与离线回放

在仓库根目录安装依赖并启动（已有合适环境可直接复用，不需要设备）：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r ground_station/requirements.txt -r aero_sim/requirements.txt
.\.venv\Scripts\python.exe ground_station/main.py
```

顶部选择“离线回放 Offline Replay”，点击“开始 / 继续”。可暂停、继续、重新开始或停止。整个输入为 11 秒的固定显示刺激：18 个事件，其中 15 个有效样本、2 个传感器故障样本、1 个开始于 4 秒并在 7 秒恢复的数据空窗。含正负姿态、阶跃、回零；不是物理 plant，也不是 Kalman/PID 稳定性证明。

输入：[system_v1.json](ground_station/replay/system_v1.json)。SHA256：`2bbf67f3b9ffb2b4fd5fedabc21dabb25c59cd53c791d1d0ef567812a309560f`。

日志仍使用原 DataLogger 的时间戳 RAW / DICT 记录格式（历史名为 `.csv`，并非规范化矩形 CSV）。新增 provenance 行记录输入哈希、synthetic offset、无认证及无控制权限；日志不会被当作来源认证。新会话使用微秒级独立文件，重启不会混写此前会话。当前回放仅支持随仓库固定的场景，不冒充任意历史日志播放器。

### 隔离和数据语义

- offline 模式不会实例化串口或 UDP 控制连接。`connect_data()` 和 `on_send_command()` 均检查 offline，直接调用也会拒绝，包括 ARM、AUTO、舵机、回收、E-STOP 和 RESET；不仅是按钮禁用。
- 切换输入递增 session epoch，拒绝旧回调。转发由 GUI-parented QObject 的注册 Slot 完成，fake QThread 实测检查了主 GUI 线程执行，而非用普通闭包改变 worker 信号的线程归属。
- 无效、非有限、缺失姿态数据冻结旧值；不会补零。缺少比较字段时不制造比较曲线；新会话清空旧仪表值为 unavailable。格式正确的残缺 valid 声明不能抹掉此前明确 sensor fault。
- 当前飞控 `yaw=gz`，是 deg/s 角速度而非航向。3D 只显示已提供的 roll/pitch，不再将 gz 当 yaw 角积分/旋转；实物安装变换和控制方向仍未确认。`batt=7.4` 是固件常量，UI 明示为 placeholder，回放缺失电池值保持 unavailable。
- 来源始终为 LIVE UNAUTHENTICATED 或 SIMULATION / OFFLINE REPLAY。JSON、CRC、session、IP/port、`source_mode=PHYSICAL` 或最近到达均不会升级为来源认证/执行权限。
- 原曲线已有 1000 点上限；补齐 UI 文本 2000 blocks / 单条显示长度上限、残缺 JSON 16384 字符上限。磁盘日志是持久记录，不受这些 UI 缓存上限限制。

## S2 / S3：真实运行与集成结果

可重复执行真实窗口验收（输出目录必须是新目录，保护历史证据）：

```powershell
.\.venv\Scripts\python.exe -u scripts/system_v1_runtime.py --output engineering/offline-evidence/system_v1/my_runtime --soak-samples 4500
py -3 -u scripts/system_v1_check.py --output engineering/offline-evidence/system_v1/my_full_check
```

第二条只启动一个 `scripts/check.py` gate，按既有次序串行执行其全部阶段，并保存依赖、真实退出码、全日志及 collection-only 用例清单。收集测试身份不算执行通过；两个 GNC 重复组单独注明。

实际应用用原 `create_application()` / MainWindow、真实 Qt event loop 与 widgets。仅 serial/socket 建立边界替换成 deny-all，既不连接设备也不建立真实 UDP 控制端口。截图来自运行应用的 `QWidget.grab()` / 可用时的 OpenGL framebuffer，不是 AI 生成图，也没有替换为历史 CAD。

| 集成验收项 | 当前状态 / 证据 |
| --- | --- |
| 无设备启动、原窗口布局、模式切换 | `PASS`；最终结果见 `runtime_v2/runtime_result.json` |
| synthetic → 原解析器 → 仪表 / 两类曲线 → RAW/DICT 日志 → 停止（不含 3D 绘制） | `PASS`；最终运行 JSON 记录断言、输入哈希和日志哈希 |
| 故障冻结、中断、恢复、暂停/继续、重启/停止 | `PASS`；有真实截图与自动化断言 |
| 原简化 3D 实际绘制 | `NOT_VERIFIED`：本机初次有 GLError 1282；有效 context 不等于绘制成功。界面有明确降级提示，不将空白窗口计 PASS |
| 全链条包括可见 3D | `PARTIALLY_VERIFIED`，不得用 transform 单测替代可见渲染 |
| 4500 帧 / 内存有限观察 | `PARTIALLY_VERIFIED`：实际 260.164 秒；缓存有界，不能证明长期无泄漏 |
| 多小时耐久 / 所有显卡兼容 | `NOT_EVALUATED` |
| 真实鼠标交互独立检查 | `NOT_VERIFIED`：Computer Use 的 `@oai/sky` 模块不可用；已完成真实 Qt 应用运行夹具，不声称人工交互验收 |

运行环境为 Windows 11 build 26300、Python 3.13.1、仓库 `.venv` 的 PySide6/shiboken6 6.10.2、pyqtgraph 0.14.0、numpy 2.4.2、PyOpenGL 3.1.10。主要页面真实截图为 `runtime_v2/01_no_device.png`、`02_udp_settings_no_connection.png`、`03_replay_curves.png`、`06_raw_filtered_recovered.png`、`08_3d_or_explicit_degradation.png`，另有暂停、故障、中断、结束与负载截图。

4500 帧输入哈希：`2bf249d433533830a4039f06fb12f30ca96638cfa738faf329e92d021fb880ea`。所有 synthetic samples 的逻辑间隔固定 20 ms；实际该观测约 17.3 frames/s，包含 tracemalloc 与完整重绘开销，**不是 50 Hz UI 保证，更不是实测飞控 cadence**。2000→4500 帧期间 Python tracked memory 为 628555→693074 bytes，增加 64519 bytes；RSS 为 53514240→54841344 bytes，但早期 RSS 曾达到约 323 MB，Windows working-set trim 不能解释成“无泄漏”。曲线均维持 1000 点、UI log 2000 blocks、parser buffer 0。报告有限观察，不外推多小时稳定性。

`runtime_v2/runtime_result.json` 文件 SHA256 为 `be1f5229978500fce4b15dd5a2626ab813981891ff4f6863fad958c1ac715e83`；其中 `result_sha256` 是不含自身字段的 JSON 逻辑载荷哈希 `11583aae43a3620873f2ce446e784640377ed8f61540c5927af2049429197275`，两者不是同一个哈希。完整演示日志为 `runtime_v2/telemetry/telemetry_20261025_141250_510770.csv`，SHA256 `64c9a00889ae3f5b202045384a2d580dae7b190a3be148e1e32c4104d5c69c9a`。

已有命令纯软件行为由原测试保留覆盖：ACK、NACK sensor_invalid / recovery_disabled、未知拒绝原因、命令不匹配、TIMEOUT、错误 IP/port、通信中断、ESTOP/RESET。native 测试运行真实 C++ command processor / main fake-boundary；UDP 回归仅使用 127.0.0.1 behavioral stub，不是 ESP 设备或实际链路。

E-STOP/RESET/默认回收语义未修改：RESET 不能清除传感器 reboot latch，也不恢复 AUTO；默认 firmware 的 explicit deploy_chute 在部分 ESTOP / invalid-sensor 场景仍被允许；GNC-only 明确返回 recovery_disabled 并排除 PB0 attach/write。ACK 只表示软件决策被接受，不表示物理动作发生。

### 本轮缺陷与定点修补

| 问题 | 处理 / 状态 |
| --- | --- |
| core 3.0.0 Serial2 类型冲突 | 最小声明兼容修复；五构建 PASS |
| Qt 6.12 Linux 退出崩溃 | 保留失败记录；显式生命周期 + 固定 6.10.2 的托管全门 PASS；上游原因仍未证明 |
| 缺离线输入 / 可触发真实发送 | 新输入复用原 UI；发送和连接入口拒绝，fake transport 负例覆盖 |
| 旧会话数据/ACK/error/state 污染新输入 | epoch + GUI-owned typed Slot；旧源事件及真实 fake-QThread 测试 |
| live 值残留到 synthetic / 字段缺失补零 | 切换重置 unavailable；有限数字与必要字段检查；明确 sensor fault 不被残缺 valid 声明清除 |
| gz 当航向、batt 被当实测 | 地面站更正语义与 3D yaw 行为；固件未改 |
| GL context 有效但 paintGL 失败 | 捕获实际绘制异常、sticky 降级与可见说明；不宣称渲染合格 |
| 未绑定 UDP socket 提前发送的竞态 | bind/config 完成后才公开 socket；退出撤销引用；fake lifecycle 负例不触网 |
| 文本 / 残缺 JSON 无界保留 | 有界缓存，保留文件原始日志；不删断言或失败实验 |

首次 `runtime_a62ec51` 以系统全局 Python 3.13.1 / PySide6 6.9.0 运行，遇到实际 GL 绘制错误退出 1；该 JSON 中中途 context-only 的 `opengl.status=PASS` **已被随后的 FAIL 推翻，不是 3D 通过证据**。修正验收程序后使用仓库 `.venv` PySide6 6.10.2 重新运行，保留旧目录不变。开发中还修正了 deferred hide 未绑定 Qt context 的 teardown 错误；随后完整 GS 测试 91 项退出 0。此前一次 loopback 回归超时保留为发现记录；没有调大超时或降低断言，UDP 生命周期用独立 fake 边界验证。

## 未完成 / 阻断与证据上限

| 功能 / 工程问题 | 状态 | 边界 |
| --- | --- | --- |
| 本 Windows 主机可见 3D | NOT_VERIFIED | 需独立解决/验证 Qt/OpenGL 实际绘制；现有 fallback 可运行 |
| 实际串口、ESP UART/UDP、ESP-01S 实机 | NOT_EVALUATED | 本轮禁止设备操作；软件桩和构建不替代硬件验收 |
| RA-02 / SX1278 LoRa 驱动与实际链路 | BLOCKED | R3 是独立 binary research，现生产 ESP / GS 是文本 JSON；无适配、SPI/天线/法规资格，0 RF 发射 |
| R3.2 质量门进入现 GS | NEEDS_INTEGRATION | 未强接不兼容 binary/text 协议；最近接收时间不等于真实采样时间，不提供“可信度百分比” |
| UDP 身份认证、请求 ID、多客户端、跨会话 replay 防护 | BLOCKED | endpoint correlation、CRC/session 都不是 authentication；没有新增控制授权 |
| 自动回收检测资格 | BLOCKED | ±2g 配置与 strict >2.5g 启动阈值矛盾；invalid-sensor / ESTOP 也冻结自动 FSM。保留既有 advisory blocker，不调整阈值/安全逻辑 |
| 坐标/安装方向、实物恢复力矩、真实 cadence / plant | UNKNOWN | 数学 oracle / 10–50ms 比较不证明实物自稳 |
| dynamics / aero 的物理适用性 | HISTORICAL / UNKNOWN | 研究烟测保留预期 5°不收敛；旧75mm固体构型、CG/CP/惯量不能升级为当前EDF物理证据 |
| CAD-V1 / 旧资产清理 | NOT_EVALUATED | PR #21 未合并，Issue #22 后续独立任务 |

最高证据等级：`TESTED_SOFTWARE`。没有烧录、接线、通电、射频发射、舵机/回收/推进器动作或飞行；没有改增益、极性、默认模式、回收阈值或 E-STOP 权限。历史硬件和 R2/R3 证据不覆盖、不升级。

## 交付内容与证据索引

- 本报告、已有能力矩阵、原 UI 内只读回放与固定输入。
- `scripts/system_v1_runtime.py`：真实应用、截图、会话日志、输入/源码哈希和有限内存观察。
- `scripts/system_v1_check.py`：单 gate 进程的完整日志、环境、退出码与测试身份清单。
- `engineering/offline-evidence/system_v1/ci/`：初始失败、生命周期候选失败、固定依赖后的真实托管通过。
- `engineering/offline-evidence/system_v1/runtime_a62ec51/`：保留首次真实 GL 失败。
- `engineering/offline-evidence/system_v1/runtime_v2/`：修正后的实际应用运行与主要页面截图。
- `engineering/offline-evidence/system_v1/full_check_16a37c/`：本地完整回归、环境、身份清单和 exit 0 receipt。
- `engineering/offline-evidence/system_v1/SHA256SUMS.txt`：本报告、能力矩阵、固定输入、证据属性及交付证据逐文件 SHA256（不自包含；路径相对仓库根目录）。

原始 Windows 日志保留 CRLF，PlatformIO 日志保留工具输出的行尾空格；不为格式检查改写已哈希的证据。`.gitattributes` 仅对本次证据目录禁止换行归一化和源码空白告警，生产源码、测试和报告仍接受通常的 `git diff --check`，不放宽测试断言。

源码变更范围：PR #24 的 workflow、GS 依赖约束 / Qt 测试生命周期、飞控串口声明；PR #25 的 GS 输入与数据显示边界、回放与边界测试、真实运行/证据包装脚本和文档。ESP、RF 协议、PID/Kalman、command processor、FSM、安全权限、历史模型和 CAD 没有生产逻辑改动。

## 下一阶段最有价值的三个任务

1. **关闭 3D 本机兼容性门**：在独立、可复核的 Qt/OpenGL 环境取得实际方盒绘制与交互证据；不引入未经资格的 CAD。随后进行多小时 UI 耐久与重复会话测试。
2. **制定并离线验证统一只读遥测适配契约**：明确 ESP 文本与 R3 binary 的版本、长度、字段/单位、缺失值、采样时钟与接收年龄、未认证来源。以负例证明其没有命令权限，不进行 RF/硬件集成。
3. **形成独立安全工程变更建议**：围绕已记录的回收阈值/量程和 early-return 冻结矛盾，写明影响、拟议方案及纯软件验证；保持本次控制逻辑不动，交由独立审查后再授权实现。

没有需要用户立即完成的硬件动作。请独立复核 Draft PR #24 / #25；本任务不合并 PR。
