# KR-2026-002｜仿真结果可复现性、坐标符号与证据清单

- 创建日期：2026-10-19；状态：**ANALYZED**（独立读取源码）、**REFERENCE_EXPERIMENT_PASS**（仅本研究资料的 manifest 检查器自测），并非 Ad Astra 仿真验证。
- 项目锚点：\`AI-rocket@44edda14982618627a020f1d8475ab6f750acb05\`；上游锚点 \`RocketPy@9bd6ad3af8f97bafa3201d4e70eba2877e66e040\`。
- 对应已知问题：\`R0-008\`（控制极性/模型假设不一致）、\`R0-009\`（仿真产物缺来源信息）、\`R0-006\`（控制参数未硬件确认）。
- 决策用途：**让已生成的软件仿真结果可以追溯并被独立检验**；当前不能据此批准实际飞行、控制器参数、推进或 CAD。

## 1. 从本项目源码确认的事实

| 观察 | 精确依据 | 不应如何解释 |
| --- | --- | --- |
| \`param_sweep.py\` 的离散控制器输出直接送往模拟舵机 | [L90-L103](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/dynamics_sim/param_sweep.py#L90-L103) | 不能直接认为与其他符号约定的脚本相同 |
| \`cg_impact_study.py\` 采用 \`- pid.compute(...)\` | [L35-L43](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/dynamics_sim/cg_impact_study.py#L35-L43) | 正负号不同**不一定证明其中某个错误**：需确认坐标、模型力矩和执行方向 |
| \`param_sweep.py\` 把搜索结果写到固定 \`sweep_results.csv\` | [L127-L158](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/dynamics_sim/param_sweep.py#L127-L158) | 仅凭文件名无法确定源 commit、环境、参数和哈希 |
| 已有 \`simulation_smoke.py\` 校验历史质量关系、有限数、四元数与部分模型行为 | [脚本](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/scripts/simulation_smoke.py) | smoke PASS 只覆盖所列案例；不能推断动力学全工况正确 |
| \`engineering/parameter-registry.yaml\` 将质量、CG、模型 PID、传感器速率等分开记录并标 \`HISTORICAL/PROTOTYPE/UNKNOWN\` | [受控字典](https://github.com/guo6x/AI-rocket/blob/44edda14982618627a020f1d8475ab6f750acb05/engineering/parameter-registry.yaml) | 不可用现存理论值替换未测量的实物值 |

## 2. 上游 RocketPy 的具体测试思想

[FlightDataExporter 源码](https://github.com/RocketPy-Team/RocketPy/blob/9bd6ad3af8f97bafa3201d4e70eba2877e66e040/rocketpy/simulation/flight_data_exporter.py#L75-L155) 导出时间、位置、速度、四元数和角速度等字段，并在输出中标注部分单位；[对应单元测试](https://github.com/RocketPy-Team/RocketPy/blob/9bd6ad3af8f97bafa3201d4e70eba2877e66e040/tests/unit/test_flight_data_exporter.py) 用临时目录和数值比较检查导出内容。这是**导出语义可测试**的范例。

**局限**：上述导出/测试并不能自动保证每个 CSV 具备源 commit、所有依赖版本、随机种子、所有输入哈希和物理模型有效性。为 Ad Astra 单独设置 manifest，是一个基于项目缺口提出的加强方法，**不是声称 RocketPy 自身不能或从未支持 provenance**。

### 模型/结果分离的最低要求

一次研究软件运行保留一个隔离目录，至少记录：

- **问题目的**：本次仿真用来比较什么；明确不支持的用途。
- **模型定义**：\`model.name/version\`、参考坐标系、单位字典、假设、是否用实测数据相关性校准。
- **源码**：项目仓库、40 字符 Git commit；正式证据还应保存 dirty tree 状态和本地补丁哈希。
- **计算环境**：Python/依赖固定版本、命令、随机种子；正式复现还应记录操作系统/平台、线程与数值库差异。
- **输入输出**：文件路径、SHA256，结果不得只依赖人工粘贴的“优秀曲线”。
- **解释**：报告误差指标、失败案例与验证外推限制。

**不要将“同一 SHA256”当作“数学正确”或“物理真实”。** 它只表明归档文件内容一致。

## 3. 本轮独立完成的离线研究小工具

位于 [\`../examples/simulation_manifest.py\`](../examples/simulation_manifest.py) 与 [\`../examples/test_simulation_manifest.py\`](../examples/test_simulation_manifest.py)。

- **运行**：进入 \`docs/aerospace-knowledge/examples\`，运行 \`python -m unittest -v test_simulation_manifest.py\`。
- **实际本轮隔离环境的结果**：14/14 单元测试通过（2026-10-19）；仓库合入后的 CI 和实际 Ad Astra 仿真流水线尚未运行。
- **本轮正反例**：有效 manifest 可接受；篡改输出/文件缺失/绝对路径/上级目录越界/symlink 外逃/重复工件/伪造哈希/不合法源 SHA/错误证据分类/空工件列表均被拒绝。
- **工具边界**：只有 Python 标准库、只读校验，**不执行模拟，不使用真实硬件，不写回项目参数、不认证模型、不验证 SHA 是否属于真实 Git 对象**。
- **已知局限**：\`source.commit\` 检查格式不验远程存在；仅校验当次存档文件和字段，无法保证外部依赖被真实固定或运行可完全复现；哈希无法防止攻击者同时重写产物和 manifest；运行数据环境/容器镜像签名等另需独立证据；生产使用前需提升测试与安全审查。

## 4. 下一次科学模型专项实验（未执行）

### SIM-POLARITY-01：坐标约定自洽性
在**纯软件**单位案例中定义正向角度、正向传感器输出、执行器命令、作用力矩和反馈误差的符号表。为相同符号表准备正向与反向的小扰动案例，验证代码与明示的解析关系一致。未冻结统一物理模型前，**不开展控制器优化或比较“最佳 PID”**。

### SIM-MODEL-01：一个解析可校核的运动学基准
在无动力、无外力、无阻力的理想数学环境中设置恒定初始速度 \`v0\`，检验 \`x(t)=x0+v0 t\` 在离散积分结果中的数值误差及单位。该案例只验证数学和软件构件，不代表任何真实航天器轨迹。

### SIM-TRACE-01：真实研究结果归档
把一个**不会修改既有结果文件**的测试过程包装为有独立运行目录的证据包，运行结果和失败日志一并保留。归档满足结构校验后才能交人工审查“结果是否可信”。

## 5. 采纳裁决

- **当下结论**：\`ANALYZED\`，研究工具独立测试 \`REFERENCE_EXPERIMENT_PASS\`，仿真结果真实性依旧 \`UNVERIFIED\`。
- **允许推进**：通过 PR 为未来仿真记录引入可追溯 manifest 规范/只读检查。
- **禁止表述**： “动力学模型已获 NASA 验证”“PID 可用于实机”“RocketPy 结果证明 EDF 台架稳定”“归档通过等于模拟可信”。
- **后续依赖**：需对实际 Ad Astra 仿真源码、初始条件、符号极性、模型假设和代表工况开展独立验证，才可能更新工程决策。


## 后续实验证据追加（2026-10-20）

第三轮已完成其前述 \`SIM-MODEL-01\` 的首个**纯软件数学参考试点**，详见 [KR-2026-004](KR-2026-004-authentic-model-analytic-benchmark.md) 与 [完整证据](../evidence/KB3-20261020/)。

此项工作使用**源代码字节与 Git blob 一致**的历史 \`InvertedPendulum1D\`，在零推力、0.1°、0.4s 条件下验证解析近似差异、零平衡点和奇对称性，8/8 测试通过。与原先仅有 manifest 结构检查的阶段相比，现在确实运行过一段真实项目源码；**但其他仿真模型、极性冲突和实物验证仍未关闭**，本卡中更早的研究状态是当时事实，不应被追溯涂改。
