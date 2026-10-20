# KB3｜Project Ad Astra：真实历史动力学源码的零推力数学基准实验

> 执行日期：2026-10-20。研究等级：**REPRODUCED（限本实验的数值软件行为）**。  
> **不属于**实物验证、控制器合格测试、机械制造许可或真实火箭飞行准备。  
> 项目模型出处：[AI-rocket \`dynamics_sim/physics_engine.py\`](https://github.com/guo6x/AI-rocket/blob/25b0f6c31f01ab9178cf6dd96d7e0ca8eff7cc99/dynamics_sim/physics_engine.py)；锁定版本 \`25b0f6c31f01ab9178cf6dd96d7e0ca8eff7cc99\`；Git Blob SHA1：\`f804ab126d13781928036ee4a22b99cf0ea59be6\`。  
> 关联研究卡：[KR-2026-002](../records/KR-2026-002-simulation-provenance.md)；现存问题：\`R0-008\`（符号/动力学模型冲突）、\`R0-009\`（运行证据不完整）。

## 1. 实验真正解决的问题

上一轮的 \`simulation_manifest.py\` 只验证某份归档文件的 SHA256 和字段结构，**没有真正运行任何项目仿真**。这次推进两步：

1. **加载仓库真正的历史 \`InvertedPendulum1D\` 源码**，先核对 Git blob 与锁定版本匹配，不接受重新抄写的相似实现；
2. 对源代码限定为**零推力、极小角度、无控制动作**的情形，拿线性化微分方程解析近似与源码 RK4 数值积分比对，并把结果、输入、源码、版本、环境一并归档。

这个研究验证**有限条件下的模型数值行为**，不能用于外推实际 TVC 控制、真正火箭动力学、实际飞行或任何推进系统操作。

## 2. 独立理论参照

在源码 [\`InvertedPendulum1D._derivatives\`](https://github.com/guo6x/AI-rocket/blob/25b0f6c31f01ab9178cf6dd96d7e0ca8eff7cc99/dynamics_sim/physics_engine.py) 的零推力设置下：

\`\`\`text
I * θ'' = m*g*L*sin(θ) - c*θ'
I = (1/3)*m*(2L)^2
\`\`\`

当 \`θ\` 很小时，用 \`sin(θ)≈θ\` 得到线性近似：

\`\`\`text
I * θ'' + c*θ' - m*g*L*θ = 0
r+/- = [-c +/- sqrt(c²+4*I*m*g*L)] / (2*I)
θ(t) = A*exp(r+*t) + B*exp(r-*t)
A = -r-*θ0/(r+ - r-)
B =  r+*θ0/(r+ - r-)
\`\`\`

初始条件为 \`θ(0)=0.1°\`、\`θ'(0)=0\`；对应参数是**原模型的历史数学默认值**，不是当前实物测量。

该解析参照与数值积分采用不同的计算路径，但物理形式仍来自**同一个假设模型**。它能够检验模型实现的内部一致性，却不能作为独立实物准确性认证。且所报告误差包括非线性模型与线性参照之间的近似差异，不是纯 RK4 截断误差。

## 3. 运行参数

| 项目 | 值 | 属性 |
| --- | --- | --- |
| 物理模型 | \`dynamics_sim/physics_engine.py\` 历史 1D 倒立摆 | Git Blob 与原始版本一致 |
| 模型质量 \`m\` | 1.0 kg | **PROTOTYPE**，非实测 |
| 质心力臂 \`L\` | 0.2 m | **PROTOTYPE**，非实测 |
| 名义默认推力字段 | 15 N | 仅保留源码初始化参数，**未施加** |
| 本次实际动力学推力 | **0 N** | 严格零推力；不执行台架试验 |
| 初始角 | 0.1° | 虚拟初始数学条件 |
| 步长 | 0.002 s | 200 次积分，共 0.4 s |
| 数据记录 | 每 20 步 1 次（含 t=0） | 共 11 个样本 |
| 阻尼系数 | 0.5 N·m·s/rad | 源码历史默认假设 |
| 运行时 | Python 3.13.5 | 本次隔离环境 |
| 第三方运行依赖 | 无 | Python 标准库 |

## 4. 真正的执行结果

| 检查 | 观测结果 | 验收阈值 | 本案例 |
| --- | --- | --- | --- |
| 最大角度与线性参照差异 | **4.4732188604276746 × 10⁻⁹ rad** | ≤1 × 10⁻⁷ rad | PASS |
| 零起始角度：角度残差 | 0 rad | ≤1 × 10⁻¹⁴ rad | PASS |
| 零起始角度：角速度残差 | 0 rad/s | ≤1 × 10⁻¹⁴ rad/s | PASS |
| 正负对称：角度残差 | 0 rad | ≤1 × 10⁻¹³ rad | PASS |
| 正负对称：角速度残差 | 0 rad/s | ≤1 × 10⁻¹³ rad/s | PASS |
| 仿真证据归档校验 | manifest + 4 个输入/输出文件哈希逐个一致 | 全部匹配 | PASS |
| 重复执行 | 两次输出/清单逐字节相同 | 全部匹配 | PASS |
| 新增测试 | 8 项 unittest 全部通过 | 8/8 | PASS |

**证据位置**：[本轮存档目录](../evidence/KB3-20261020/)；尤其是 [manifest.json](../evidence/KB3-20261020/manifest.json)、[samples.csv](../evidence/KB3-20261020/outputs/samples.csv)、[summary.json](../evidence/KB3-20261020/outputs/summary.json)。

档案 SHA256：
- manifest：\`3bcf40efd2306ac9774f8f986a00613fb5e987f3f9a8a5ee2ce91d62191113bf\`；
- 真实源码快照：\`3aa387699abec402af3aac3045ccb7210f43c01b5b887f98a50564fdddc7ebe6\`；
- 配置：\`3780bd21b801a018d777b41b6722f23f484a4bcc48f196c2030124e8e5b3bc4b\`；
- samples.csv：\`7a9818b53f3317bcf34b7b5f7de88dd2023f68abc2f4d1c353a8baee502dcb89\`；
- summary.json：\`e1fe54afae271d2602169fa9a727d5122b1ca353423a9662d43c11823ffa4500\`。

上面这些不是“自称有日志”：完整研究代码和两次一致的输入/输出实际已在隔离环境执行，**其中一份原始证据已经提交至 GitHub**。

## 5. 如何重新跑（纯软件、无第三方库）

在 \`AI-rocket\` 仓库根目录，确保有 Python 3.10+，并创建一个**原本不存在的**输出目录路径，例如：

\`\`\`bash
python -m unittest discover -s docs/aerospace-knowledge/examples -p 'test_reference_experiment.py' -v
python docs/aerospace-knowledge/examples/run_reference_experiment.py --output-dir research-output/KB3-new-run
python docs/aerospace-knowledge/examples/simulation_manifest.py research-output/KB3-new-run/manifest.json
\`\`\`

运行器检查 \`dynamics_sim/physics_engine.py\` 的 Git Blob；若与锁定源码不一致会提前报 \`MODEL_SOURCE_MISMATCH\`，不让不同模型假装可直接比较。**已存在的输出目录也会被拒绝覆盖**。本实验不改变现存 \`aero_sim\`、\`dynamics_sim\`、\`engineering/\` 或任何生产代码/参数。

需要 Linux shell 时上述示例有效；PowerShell 命令参数格式亦可适用，具体 Python 可执行名因环境而异。

## 6. 一次真实“证据闭环”与尚未闭合的工程问题

已完成：

\`版本锁定 → 真实历史源码 → 受控输入 → 数值执行 → 解析近似对照 → 单元测试 → 重复计算 → 文件哈希 → 可复查存档\`。

**尚未完成/不应越级推断**：
- 本实验只覆盖 0 N、0.1°、0.4 s；未评估大角度、实际惯量、模型误差、外部扰动、离散传感器、控制链路。
- 解析方程与代码使用同一物理关系，未进行独立软件求解器/实验测量交叉验证；还不能断言“全局模型可信”。
- 没有对 \`R0-008\` 的多个脚本控制极性冲突做完对比；历史 \`R0-009\` 的各类结果尚未逐一补齐。
- 本轮未运行完整 AI-rocket 的 PlatformIO/地面站/硬件测试，没有制造、推进或飞行放行证据。
- Python 版本、硬件/操作系统以及执行环境不同可能改变浮点最后几位；只针对这两次相同环境执行断言归档逐字节一致。

**结论与下一步**：此研究案例的 \`REPRODUCED\` 是真实的，但作用范围很小；下一步应进行积分步长收敛和独立数值求解器交叉校核，再扩大**纯软件**数学测试覆盖。**不得因为本研究卡通过而把现有 \`engineering/\` 中的物理状态提升为已验证**。


## 7. 合并前的真实仓库目录复测（2026-10-20）

将已通过的运行器、旧归档工具及两组 unittest 放到与 GitHub **相同的相对目录层级**，把测试文件的仓库根目录解析固定为 \`Path(__file__).resolve().parents[3]\`，再次运行：

\`\`\`bash
python -m unittest discover -s docs/aerospace-knowledge/examples -p 'test_*.py' -v
\`\`\`

**结果：22/22 PASS**（上一轮归档工具的 14 项 + KB3 新增的 8 项），无跳过；使用无第三方库的 Python 3.13.5。通过该真实目录结构重新生成的 manifest、samples.csv 与 summary.json 的 SHA256 均与原始归档**完全一致**。GitHub 分支中的代码亦核对与这次真实运行文件 Git Blob 相同。

复测仅涉及知识库独立软件，并未执行 AI-rocket 完整 \`scripts/check.py\`、PlatformIO 飞控目标或任何实物。研究声明仍严格局限于本文数值参考场景。
