# 开源项目与权威资料登记簿｜Source Register

- 检索/核对：2026-10-19；原始 GitHub 仓库元数据、README、部分 LICENSE 和根目录结构来自 GitHub，NASA 标准来自 NASA 官方站点。
- **状态定义**：本表的 `SOURCE_CHECKED` 只表示读取公开资料和仓库元信息；不表示跑通过代码、证明科学模型正确、取得产品认证或完成依赖安全审计。
- `pushed` 是 GitHub 元数据最近推送时间（UTC），**不是正式发布日、质量认证或本研究锁定的源代码 commit**。下一次复现必须单独记录确切 SHA/tag。
- 不以 Star 数作为工程可信度主因。评估更看：原始出处、限制条件、可重复测试、文档与维护、许可证和项目差距。

## A. 近期优先（真实项目缺陷直接相关）

| ID / 原始仓库 | 仓库证据（已查看） | 适合借鉴 | 对应项目问题 | 许可原文/风险 | pushed (UTC) |
|---|---|---|---|---|---|
| GH-01 [NASA F´](https://github.com/nasa/fprime) | README：组件化接口、异步任务/消息、代码生成、单元/集成测试；存在 docs/、CI 与测试工程 | 将飞控数据流拆为可独立测试组件；遥测/指令模型 | `R0-005` 传感器错误、`R1-001` 命令身份、组件边界 | Apache-2.0；架构体量大，不应未经资源评测整体移植到 STM32F103 | 2026-10-18 |
| GH-02 [NASA NOS3](https://github.com/nasa/nos3) | README：模拟设备、动力学环境、多目标构建、地面站和测试环境；有 docs/ | 为软件创建虚拟设备与故障注入环境 | `R1-002` 集成证据缺失、`R0-005` 无效传感器、`R0-014` | README 与 LICENSE 均写 NOSA 1.3；需逐条确认二次分发义务；本阶段只参考方法 | 2026-10-07 |
| GH-03 [RocketPy](https://github.com/RocketPy-Team/RocketPy) | README：6DOF、可变质量、气象、降落伞与蒙特卡洛；有 tests/、docs/、验证论文链接 | 追踪输入与输出、模型假设、随机性和数值误差 | `R0-008` 模型极性不统一、`R0-009` 可追溯不足 | MIT；**本项目旧 RocketPy 文件属于历史固体火箭基线，不可当成现 EDF 装置模型** | 2026-10-05 |
| GH-04 [NASA IKOS](https://github.com/NASA-SW-VnV/ikos) | README：LLVM/C/C++ 抽象解释静态分析，示例包括数组越界；CI 信息 | 检测可证明的运行时错误与边界问题 | 飞控固件解析/边界检查、`R0-005` 输入处理 | README 标 NOSA 1.3；实际兼容平台/编译工具链尚未测试 | 2026-05-31 |
| GH-05 [CadQuery](https://github.com/CadQuery/cadquery) | README：参数化 CAD、无 GUI API、STEP/装配、tests/examples；LICENSE 正文写 Apache 2.0 | 几何参数输入、模型来源、导出和装配验证 | `R0-011` CAD 版本混乱、`R0-012` 假通过 | Apache-2.0；几何检查不等于强度、工艺、公差及制造放行 | 2026-10-18 |

## B. 次优先（模块方法研究）

| ID / 原始仓库 | 已核对资料与拟研究内容 | 适用边界 | 许可或注意事项 | pushed (UTC) |
|---|---|---|---|---|
| GH-06 [OpenRocket](https://github.com/openrocket/openrocket) | README、LICENSE；模型火箭构型、轨迹仿真、结果展示、导出 | 是未来模型火箭的参考工具，不能作为 EDF 台架物理依据 | LICENSE：GPL v3 或更新版，有附加许可；谨慎复制源码 | 2026-10-08 |
| GH-07 [NASA cFS](https://github.com/nasa/cFS) | README：可插拔飞行软件架构、cFE/OSAL/PSP、应用等 | **README 明确本仓库是 Demo Bundle，不能直接用于飞行，未完成任务级验证** | Apache-2.0；组件化和健康管理方法可参考 | 2026-10-18 |
| GH-08 [JSBSim](https://github.com/JSBSim-Team/jsbsim) | README：飞行动力学模型、Python 绑定、测试与建模案例 | 可比较坐标/动力学组织方式，不可把飞机模型当台架实物 | GitHub license 元数据为 LGPL-2.1；分发前核对完整文件 | 2026-10-18 |
| GH-09 [Basilisk](https://github.com/AVSLab/basilisk) | README、docs/examples/benchmarks；多体航天器动力学框架 | 目前更适合学习仿真组件与交叉验证，非 R2 即时依赖 | ISC（GitHub 元数据）；依赖与安装体量需单独核算 | 2026-10-19 |
| GH-10 [NASA FRET](https://github.com/NASA-SW-VnV/fret) | README：形式化需求、歧义处理、要求一致性与测试用例生成 | 用于改善“需求说不清、验收无判据”问题 | README 标 Apache-2.0；先手工开展受控需求规范试点 | 2026-04-14 |
| GH-11 [OpenMDAO](https://github.com/OpenMDAO/OpenMDAO) | README：多学科模型分解、梯度优化；LICENSE.txt 为 Apache-2.0 | 只有在基础物理模型可信之后才值得优化 | 先不为未验证参数做自动寻优 | 2026-10-18 |

## C. 长期储备与学生团队实践

| ID / 原始仓库 | 已核对资料与价值 | 主要风险 | pushed (UTC) |
|---|---|---|---|
| GH-12 [Dymos](https://github.com/OpenMDAO/dymos) | 开源动态系统分析/最优化；存在 docs、benchmark | 基础建模/验证未成熟前不优先 | 2026-10-16 |
| GH-13 [NASA GMAT](https://github.com/nasa/GMAT) | 空间轨道与任务分析，适用于远期空间任务 | 当前 EDF 实验台无轨道任务；README 提醒未发布 tag 的提交以现状提供 | 2026-10-09 |
| GH-14 [SpaceAST](https://github.com/space-ast/ast) | 中文 README、C++ 轨道/坐标/常微分方程/空间环境算法及 test/；Apache-2.0 | 项目较新；算法正确性和环境模型版本未经独立交叉检验 | 2026-10-19 |
| GH-15 [MASA Rocket Avionics](https://github.com/masa-umich/Rocket-Avionics) | README：大学团队 STM 飞控、板驱动与传感器模拟板等目录 | 公开仓库许可证未能从元数据确定；**仅参考组织方式，不复制实现** | 2026-06-25 |

### 特别更正：不能仅凭 GitHub API `NOASSERTION` 推断无许可证

经过读取仓库 LICENSE 原文：
- CadQuery：Apache-2.0。
- OpenMDAO：Apache-2.0。
- OpenRocket：GPL v3 或更新版本（附加许可见 LICENSE.TXT）。
- NOS3：NOSA 1.3。
- NASA IKOS：README 标 NOSA 1.3；正式代码复用须进一步审查许可证正文。

有些仓库内容包含来自其他第三方的代码/资产，主体许可证**不一定覆盖全部子组件**。本库默认仅研究概念，若进入复制、链接、修改、商用分发，必须形成逐文件依赖与许可结论。

## D. 机构标准与非 GitHub 原始资料

| ID | 原始资料 | 核实要点 / 具体用途 |
|---|---|---|
| STD-01 | [NASA Systems Engineering Handbook (SP-2016-6105 Rev.2)](https://ntrs.nasa.gov/citations/20170001761) | 系统工程主线、需求/接口、技术评审、验证与确认；作为**参考方法**，非项目自动合规声明 |
| STD-02 | [NASA-STD-7009B（官方标准页）](https://standards.nasa.gov/standard/NASA/NASA-STD-7009) | 2024-03-05 版本 B；模型预期用途、可信性评估、验证与不确定性 |
| STD-03 | [NASA-HDBK-7009B（官方指南页）](https://standards.nasa.gov/standard/NASA/NASA-HDBK-7009) | 2026-02-03 版本 B；为 NASA-STD-7009B 提供实现解释和案例 |
| STD-04 | [ECSS Active Standards](https://ecss.nl/standards/active-standards/) | 后续按 ECSS-E 系统/工程及 ECSS-Q 质量保证逐项锁定版本，不泛称“符合 ECSS” |
| STD-05 | [NASA 建模仿真官方实践站点](https://public.ksc.nasa.gov/mns/) | 分开说明模型规划、开发、使用与可信结论 |

## E. 下次调查要补齐的字段

对每个技术候选逐项补充：`commit/tag`、读过的准确文件路径/行号、文档发布日期、依赖环境、安装成本、典型输入与输出、已知限制、测试可复现命令、正反例、和 Ad Astra 当前代码的差异、许可证尽调、最终决策/评审记录。

**本登记簿是可追踪的起点，不是“已经把 15 个仓库全部学透”或“可直接移植”的声明。**
