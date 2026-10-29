# KR-2026-005｜真实历史动力学模型的非线性数值收敛验证（KB4）

> 2026-10-29 | 状态：**REPRODUCED_NUMERICAL_ONLY**，不构成模型物理有效性、控制器认证或任何真实硬件/飞行放行。  
> 源码版本：\`AI-rocket@25b0f6c31f01ab9178cf6dd96d7e0ca8eff7cc99\`，其中 \`dynamics_sim/physics_engine.py\` Git Blob SHA1 \`f804ab126d13781928036ee4a22b99cf0ea59be6\`；2026-10-29 再次核对当前主分支 \`bcd3a4412a59a1a69744bc2ea88dd103cd1f6ac2\` 下该文件仍具有相同 Git Blob。  
> 对应工程问题：\`R0-008\`、\`R0-009\`；它们**没有**因本实验而关闭。  
> 相关规范：[NASA-STD-7009B 官方页](https://standards.nasa.gov/node/263)、[NASA-HDBK-7009B](https://standards.nasa.gov/standard/nasa/nasa-hdbk-7009)、[SciPy DOP853](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.DOP853.html)。

## 研究问题

上一轮 KB3 使用了**小角度线性化解析近似**来比较历史模型的 RK4 积分，本轮更进一步：保留 \`sin(theta)\` 非线性项，独立实现方程右端，分别由 SciPy 的 DOP853（八阶显式 Runge–Kutta）和 Radau（隐式 Runge–Kutta）求解，校核原始 RK4 的步长收敛。注意这些解法共用概念方程，验证的是**数值程序内部一致性**，而非方程对于真实装置是否正确。

## 原型方程与边界

源码 \`InvertedPendulum1D\` 在明确设置 \`thrust=0.0\` 后：

\`\`\`text
I*theta'' = m*g*L*sin(theta) - c*theta'
I = (1/3)*m*(2L)^2
theta(0) = 0.5° ；theta'(0) = 0
\`\`\`

这里 \`m=1.0 kg\`、\`L=0.2 m\`、\`g=9.81 m/s²\`、\`c=0.5 N·m·s/rad\` 是 **HISTORICAL/PROTOTYPE** 假设，不是实物测量；模拟窗口 1.2 s。源文件构造器中还保存名义默认 \`max_thrust=15\` 字段，但 **所有积分实际都显式传入 \`thrust=0.0\`**；没有控制闭环、舵机、传感器或任何硬件动作。

## 实际运行与收敛证据

执行环境：Python 3.13.5，SciPy 1.17.0，NumPy 2.3.5；采用 \`rtol=1e-12\`，\`atol=1e-14\` 生成参考解。

| 原 RK4 步长 | RK4 最终角度 (rad) | 相对 DOP853 角度绝对差 (rad) | 误差缩小比例 |
| --- | ---: | ---: | ---: |
| 0.08 s | 0.249865322539459 | 1.8647789377e-5 | — |
| 0.04 s | 0.249882677913192 | 1.2924156442e-6 | 14.4286 |
| 0.02 s | 0.249883885215591 | 8.5113245063e-8 | 15.1847 |
| 0.01 s | 0.249883964867590 | 5.4612463440e-9 | 15.5849 |

- DOP853：\`theta=0.2498839703288359 rad\`、\`omega=0.7396666901245149 rad/s\`（结果受所用容差/软件版本限制）。
- Radau：\`theta=0.24988397032883158 rad\`、\`omega=0.7396666901248228 rad/s\`。
- 两个独立数值解法在最终**两分量状态**上的最大绝对差：\`3.078648447285559e-13\`（各分量保有自身单位，不能把这一个数无条件称为“角度误差”）。
- 原始 RK4 每次步长减半，末端角度误差缩小约 14–16 倍；在该局部测试区间接近 RK4 全局误差 \`O(h^4)\` 对应的理论 16 倍。
- 本例从 0.5° 初始角增长到约 14.3173°，因此线性化近似不能在整个区间无条件沿用；本轮**直接使用非线性 \`sin(theta)\` 右端**。
- 本轮新增 10 个测试，合并之前保留的 22 个独立测试后：**32/32 PASS（2026-10-29，本地隔离环境）**。未运行整仓库 PlatformIO/目标板构建。

### 可复查的真实文件

- [运行器](../examples/nonlinear_convergence.py) 与 [10 个独立测试](../examples/test_nonlinear_convergence.py)；原 KB3 运行器和归档验证器保持不变。
- [KB4 实验归档](../evidence/KB4-20261029/)：包含真实源文件快照、固定 \`case.json\`、\`convergence.csv\`、\`summary.json\` 和 \`manifest.json\`。
- 原始 \`manifest.json\` SHA256：\`fc7b291e510c7c6d848115f78b4b8ac38945e44b2db8b0563cd01556ecbe17d8\`；\`summary.json\` SHA256：\`68506175a22cd734b5625db5894fa1451ef22f247007183e7258a1cb39d79fb3\`。
- 在**同一执行环境**重复运行产生字节相同的归档；输出修改后，原有 manifest 校验器能够检出 SHA256 不匹配。

### 怎样自己复算（纯软件）

进入 AI-rocket 根目录，使用 Python 3.13.5 + \`numpy==2.3.5\` + \`scipy==1.17.0\`：

\`\`\`bash
python -m unittest discover -s docs/aerospace-knowledge/examples -p "test_*.py" -q
python docs/aerospace-knowledge/examples/nonlinear_convergence.py --output-dir /tmp/adastra-kb4-fresh-run
python docs/aerospace-knowledge/examples/simulation_manifest.py /tmp/adastra-kb4-fresh-run/manifest.json
\`\`\`

输出目录必须事先**不存在**；不要复用 \`/tmp/adastra-kb4-fresh-run\` 或覆盖归档。Windows 可将该路径替换为尚未建立的本地目录。运行器首先验证源文件 Git Blob；不匹配就拒绝执行。测试所需 SciPy/NumPy **仅为研究环境依赖**，不新增到固件或产品。

## 什么已经证实，什么仍未证实？

- **支持的结论**：锁定版本的 1D 历史模型，在该零推力条件下，RK4 误差呈四阶预期收敛趋势，并与两条独立数值求解路径一致；结果与输入归档可复查。
- **不支持的结论**：方程正确反映实物；材料、质量、转动惯量、气动/推进、控制极性正确；真实回路稳定；飞行/制造/人员安全；项目符合 NASA 标准。
- **剩余问题**：目前只覆盖 1 套初始条件、4 个步长。更宽泛的数值边界测试、硬件测量关联、各仿真模型之间坐标和动力学构型一致性仍待研究。

因此这是 **\`REPRODUCED_NUMERICAL_ONLY\`**，不得将 \`R0-008/R0-009\` 或 R2 的 \`UNKNOWN/BLOCKED\` 越级改为已验收。

## 下一步工程任务

1. 扩展多个**无动力**初值、不同数学区域和精度/数值敏感性；每个结果单独存档。
2. 建立所有仿真文件坐标、单位、传感器/执行器极性合同；首先以文档和静态回归测试形式表达，不碰实物。
3. 将无硬件知识库回归测试纳入受控 CI，并保持与现有 \`scripts/check.py\` 和机械审查权限隔离。
