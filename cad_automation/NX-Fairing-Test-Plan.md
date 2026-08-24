# NX 12.0 参数化整流罩 API 第一套测试方案 (V1)

**代号**：Project Ad Astra - 铸剑局
**目标**：打通 NX 12.0 自动化生成整流罩的通道，从手动输入参数到直接输出 3D 实体模型。

---

## 一、 核心技术路线选型
在 NX 12.0 平台中，主要的 API 是 NXOpen。为了与未来的系统模块集成，我们面临两种选择：
1. **C# (NXOpen .NET)**：优势是类型极度安全，Visual Studio 代码提示与调试体验极佳，适合开发复杂的二次开发插件 (.dll)。
2. **Python (NXOpen Python)**：优势是语法轻量，适合作为与外部算法（如流体外形计算）通信的“胶水代码” (.py)，直接运行无需编译。

🚀 **一期决策**：采用 **Python Journal (操作记录) 批处理模式**。利用 Python 快速抽象出火箭外形的参数化函数，通过 NX 原生的 `run_journal.exe` 实现无 UI 静默生成。

---

## 二、 测试里程碑 (Milestones)

### 阶段 1：环境“破冰” (连通性验证)
本阶段不碰复杂的曲线，先验证从外部注入代码并让 NX 动起来。
*   **任务**：创建一个简易参数（如输入高度和半径），自动生成一个基础圆柱体。
*   **物理工程师操作**：在 NX 12 (`菜单 -> 工具 -> 操作记录 -> 录制 Python`) 手动录制一个建圆柱体的过程，将生成的原始代码提供给铸剑局，供我提取 Context / Session 环境代码。

### 阶段 2：整流罩几何方程实例化
*   **任务**：实现真实的火箭头部形线（如冯·卡门曲线等）。
*   **API 映射方案**：
    1. **解算器计算**：在 Python 端计算出外部轮廓的离散坐标点组 $[(x_1,y_1), (x_2,y_2)...]$。
    2. **曲线拟合**：调用 `NXOpen.Features.FitCurveBuilder` 或 `StudioSplineBuilder` 将点组连成参数化样条曲线。
    3. **旋转成型 (Revolve)**：调用 `NXOpen.Features.RevolveBuilder` 将样条曲线绕中心轴旋转360度。
    4. **抽壳/加厚**：为曲面添加物理厚度，变成可 3D 打印的真实零件壳体。

### 阶段 3：无接触黑盒流水线 (Pipeline)
*   **任务**：彻底脱离 NX 图形界面。
*   **期待效果**：在命令行或未来上位的控制站输入：
    `%UGII_BASE_DIR%\UGII\run_journal.exe generate_fairing.py -args Diameter=110 Length=300 Thickness=2 Type=VonKarman`
    引擎在后台瞬间算出并导出 `fairing_D110_L300.step` 物理打印文件。

---

## 三、 第一步待命指令 (Action Required)
物理执行官，我已阅读了您的 `project-memory` 以及 `multi-agent-sop`。我是铸剑局特工。
为了让我抓取您的 NX 12.0 宿主机特定的 API 调用格式并获得入口权：
请您打开 NX 12，录制一段最简单的 **生成基础立方体或圆柱体** 的 Python 宏代码，并保存在 `d:\AI_rocket\cad_automation\hello_nx.py` 中。
录制完成后通知我，我将接管并实施参数化解剖。
