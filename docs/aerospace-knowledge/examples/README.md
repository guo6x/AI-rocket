# 离线仿真结果来源检查器｜研究示例，不进入生产/飞控

> 2026-10-19 第一版。目标：验证归档的**输入/输出文件内容与声明的 SHA256 是否相符**，以及基本的研究元数据是否完整。该示例并非对真实动力学模型的验证、厂商认证或软硬件准入。详见 [KR-2026-002](../records/KR-2026-002-simulation-provenance.md)。

文件：
- \`simulation_manifest.py\` — 标准库实现、只读文件检查；不启动仿真，也不修改任何输入/输出。
- \`test_simulation_manifest.py\` — 14 个正反例测试，使用 Python 临时目录，不连接外设。

## 怎么自行复现

需要 Python 3.10+（推荐 Python 3.11/3.12），**无需 pip 安装第三方库**。

在本目录运行：

\`\`\`bash
python -m unittest -v test_simulation_manifest.py
python simulation_manifest.py path/to/archived-run/manifest.json
\`\`\`

- 校验成功 → 退出码 \`0\`，输出“archive structure and file hashes match; NOT a simulation validity certification”。
- 任何元数据/工件问题 → 退出码 \`1\`，打印对应的 \`FAIL\` 诊断。
- 实际本轮开发容器本地执行记录：2026-10-19，\`Ran 14 tests ... OK\`，未在 Ad Astra 完整生产 CI 运行，未对上游 NASA/RocketPy 构建。
- **源 commit 只检查 40 位小写十六进制格式**，不联网校验是否存在；版本字符串、依赖、命令也只检查字段，不实际运行/比对环境。

## 一个归档目录示意

\`\`\`text
archived-run/
  manifest.json
  inputs/
    model.json
  outputs/
    result.csv
\`\`\`

\`manifest.json\` 规范示意（使用占位 SHA256 的数据仅说明**格式**，不能通过实际校验）：

\`\`\`json
{
  "schema_version": 1,
  "run_id": "RESEARCH-EXAMPLE-001",
  "classification": "SOFTWARE_SIMULATION_ONLY",
  "intended_use": "Review a synthetic no-propulsion numerical exercise",
  "unsupported_uses": ["flight readiness", "hardware validation", "manufacturing release"],
  "model": {
    "name": "synthetic-kinematic-model",
    "version": "draft-1",
    "coordinate_system": "1D x-positive",
    "units": {"position": "m", "time": "s"},
    "assumptions": ["constant velocity", "no forces"],
    "physical_correlation_status": "NONE"
  },
  "source": {
    "repository": "guo6x/AI-rocket",
    "commit": "44edda14982618627a020f1d8475ab6f750acb05"
  },
  "runtime": {
    "python_version": "3.11",
    "dependencies": {},
    "command": "placeholder: synthetic numerical demonstration",
    "random_seed": 0
  },
  "inputs": [
    {"path": "inputs/model.json", "sha256": "<replace with exact lowercase SHA256 of this file>"}
  ],
  "outputs": [
    {"path": "outputs/result.csv", "sha256": "<replace with exact lowercase SHA256 of this file>"}
  ]
}
\`\`\`

**注意**：如果使用说明中这个占位示意，需要将字符串改为真实的 64 字符 SHA256，并实际创建相应文件。这里的示例没有被当成已验证数据结果。

## 已测试的错误条件

1. 正确归档被接受。
2. 输出内容遭篡改。
3. 文件不存在。
4. 路径使用 \`../\`。
5. 使用绝对路径。
6. 哈希不是 64 字符。
7. 同一文件重复登记。
8. commit 不是 40 字符。
9. 将分类虚假升级为 \`VERIFIED_HARDWARE\`。
10. 删除 \`unsupported_uses\`。
11. 无任何输出文件。
12. Windows/反斜线路径。
13. 清单企图把自身作为工件。
14. 通过软链接逃逸归档目录。

## 不能证明的事情

这段代码不能验证源提交是否真实、项目是否 dirty、仿真是否运行过、输入数值是否合理、坐标和单位实际是否正确、结果有无伪造、是否可重复算出、控制是否稳定或硬件是否安全。存档的操作者可以同时更改数据和 SHA256，因此还需要外部不可篡改证据、审阅和模型独立验证。

这就是为什么它仅为 **R0-009 证据来源治理的最小 PoC**。任何正式接入仿真生产流程的提案，都必须补上 CI、已知平台兼容性、供应链审查及实际结果复算，不可自动提升当前 \`engineering/\` 的验证等级。


## KB3｜现有动力学源码的首次实际数学参考运行（2026-10-20）

新增：
- [\`run_reference_experiment.py\`](run_reference_experiment.py)：实际导入并核对 Git Blob SHA 与历史 \`dynamics_sim/physics_engine.py\` 匹配，然后运行**零推力、小角度** RK4 数值计算；对照线性化解析近似；将源代码快照、输入参数、CSV 结果、误差摘要和 SHA256 manifest 保存到一个全新目录。
- [\`test_reference_experiment.py\`](test_reference_experiment.py)：八个纯软件测试，覆盖原始源码版本锁、解析近似误差、零平衡点、正负对称、重复归档逐字节一致、结果被修改能检出、存在目录拒绝覆盖、源码改动被拒绝。
- [**完整实测软件证据**](../evidence/KB3-20261020/) 和 [**研究报告**](../records/KR-2026-004-authentic-model-analytic-benchmark.md)。

在 \`AI-rocket\` 仓库根目录：

\`\`\`bash
python -m unittest discover -s docs/aerospace-knowledge/examples -p 'test_reference_experiment.py' -v
python docs/aerospace-knowledge/examples/run_reference_experiment.py --output-dir research-output/KB3-new-run
python docs/aerospace-knowledge/examples/simulation_manifest.py research-output/KB3-new-run/manifest.json
\`\`\`

上述命令不会通电、不会调用 EDF/舵机/推进系统、不会写回现有仿真成果，要求输出目录此前不存在。

**本次实际实验**：8/8 自测通过；0.4s / 200 步 / 0.1° 初值 / 0 N；最大解析近似偏差 \`4.4732188604276746e-09 rad\`，预设阈值 \`1e-7 rad\`；同一 Python 3.13.5 环境下两次运行档案逐字节一致。此处是对**同一物理假设下的数值行为**做有限检验，不验证真实火箭性能，也不意味着原有项目 R0/R1/R2 问题已关闭。


### 合并前复测记录

在模拟真实 GitHub 目录层级下运行 \`python -m unittest discover -s docs/aerospace-knowledge/examples -p 'test_*.py' -v\`，结果为 **22/22 PASS**，其中包括原 \`test_simulation_manifest.py\` 的 14 项与新 \`test_reference_experiment.py\` 的 8 项。曾发现并修复测试模块仓库根目录计算的层级错误（\`parents[1]\` → \`parents[3]\`），随后重新执行的完整实验归档 SHA256 与本轮证据一致。**不是整仓库 CI 验收**。


## KB4｜非线性 RK4 步长收敛 + 两套独立数值求解器（2026-10-29）

运行文件：[nonlinear_convergence.py](nonlinear_convergence.py)、[test_nonlinear_convergence.py](test_nonlinear_convergence.py)。本轮**额外需要** Python 3.13.5、SciPy 1.17.0、NumPy 2.3.5；不修改飞控或产品依赖，可在独立虚拟环境中安装：

\`\`\`bash
python -m pip install -r docs/aerospace-knowledge/examples/requirements-kb4.txt
python -m unittest discover -s docs/aerospace-knowledge/examples -p "test_*.py" -q
python docs/aerospace-knowledge/examples/nonlinear_convergence.py --output-dir /tmp/kb4-my-new-run
python docs/aerospace-knowledge/examples/simulation_manifest.py /tmp/kb4-my-new-run/manifest.json
\`\`\`

建议创建**全新**输出目录，Windows 下改用本地路径（不要覆盖已有数据）；如果已存在，运行器会拒绝覆盖。其根目录解析 \`Path(__file__).resolve().parents[3]\` 对应 AI-rocket 根目录。测试程序及结果**仅包含离线数学运算**，不调用推进设备、传感器、舵机、飞控目标板或实物。

实际执行：本地 32/32 知识库测试通过；本轮独立实验的新 10 项通过，代码、真实模型源文件和数据的 Git Blob 均与 GitHub 上传结果核对一致。完整数值、误差定义与模型局限见 [KR-2026-005](../records/KR-2026-005-nonlinear-convergence.md)；研究资料中的控制符号差异见 [KR-2026-006](../records/KR-2026-006-polarity-contract.md)。**没有执行整仓库 CI，也没有进行模型的实物测量验证。**
