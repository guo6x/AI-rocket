# R2.4 仿真与生产飞控一致性审查

**状态：** `DIFFERENCE_CONFIRMED` / `PROTOTYPE`
**证据上限：** `TESTED_SOFTWARE`
**范围：** 离线源码与控制器比较；不包含硬件、射频、执行器、推进、飞行或物理稳定性结论。

本记录补充 R2.3 的生产 C++/Python oracle 和双周期比较。历史仿真输出没有被覆盖，也没有被提升为当前飞控或实物证据。

## 1. 源码审计结论

| 项目 | 生产飞控 | 现有仿真/研究代码 | 结论 |
| --- | --- | --- | --- |
| PID 误差 | `flight_computer/src/algorithms/pid.cpp` 使用 `target - current`，默认 target 为 0 | `dynamics_sim/physics_engine_2d.py` 的 `PIDController2D` 使用 `current` | 已确认的数学极性差异；不等于实物安装方向差异 |
| 积分、微分 | 积分为 `error * dt`，微分为误差差分除以 `dt`；`dt` 单位秒；FLIGHT 积分上限 5、输出 ±4° | FLIGHT 配置使用相同数值，但属于另一份 Python 实现 | 通过生产 C++ probe 与独立 trace 对照；不把 Python 类当作生产实现 |
| 变化率限制 | ±0.3°/次 `compute` 调用，不是已测得的 °/s | 仿真类也按调用次数限制 | 调用频率改变等效理论速率，必须单独记录 |
| 调用频率 | `micros()` 计算 `dt`，循环末尾有 `delay(50)`，另有传感器、串口和报告开销；实际板上周期未测 | 2D 模型 1 ms 积分，每 10 ms 计算一次 PID | 100 Hz 与标称约 20 Hz 不能直接视为同一控制器轨迹 |
| 延迟/执行器 | 固件代码未证明具体传感器传输延迟或舵机动态 | `components.py` 的历史模型含 20 Hz/50 ms 传感器延迟、50 Hz 舵机、0.5°死区和 600°/s | 这些是模型假设，本轮控制器比较未执行，不能当作实测参数 |
| 命令量化 | `main.cpp` 对 PID 输出执行 `constrain(90 + (int)PID, 0, 180)`，再写 PA6/PA7 | 本轮只离线计算相同整数映射，不写真实输出 | 浮点控制量和整数命令分别保留；量化不是身份或稳定性证据 |
| 坐标/符号 | 固件计算 pitch/roll，并使用 `gy/gx`；传感器安装变换和舵机连杆方向未知 | 2D 状态称 `theta_x/theta_y`，第二轴历史上称 yaw，并用负推力矩假设恢复 | 数学约定可审计，实物校正矩阵仍未知 |
| Kalman | 生产路径包含 `kalman.cpp` 的 angle+bias 滤波 | 2D 物理模型没有等价的 Kalman/gyro 路径 | Kalman 结论只来自既有 R2.3 C++/Python oracle，不由本轮模型推断 |

## 2. 可复现的控制器比较

比较输入是 `scripts/gnc_dual_period.py` 中同一物理时间轴上的固定合成姿态：正向斜坡至 +6°、正向保持、720 ms 阶跃至 −6°、负向保持、回零和零尾段。每个周期使用独立的 PID 状态；10 ms 和 50 ms 都是离线假设，50 ms 不是实测飞控周期。

`scripts/gnc_simulation_production_compare.py` 的生产侧直接编译并调用 `flight_computer/src/algorithms/pid.cpp`；历史 2D 侧仅调用 `physics_engine_2d.PIDController2D`。两侧都执行积分、微分、输出限幅、每次调用变化率限制和离线 `90 + int(output)` 映射。没有质量、惯量、推力、摩擦、传感器或执行器参数，也没有运行 plant。

| 指标 | 10 ms | 50 ms |
| --- | ---: | ---: |
| 比较行数 | 200 | 40 |
| 非零控制行 | 180 | 34 |
| 生产/历史输出反号行 | 180/180 | 34/34 |
| 最大绝对浮点差 | 8.0° | 5.999999762° |
| 浮点差 RMS | 5.147338513° | 2.607533958° |
| 历史侧整数命令变化次数 | 22 | 6 |
| 生产侧整数命令变化次数 | 22 | 6 |
| 变化率限制的理论等效值 | 30°/s | 6°/s |

这证明了一个可重复的软件差异：相同输入和相同 FLIGHT 参数下，现有 2D PID 的误差符号与生产实现相反。它没有证明哪一个方向适合当前舵机安装，也没有证明任何闭环稳定性。既有 `gnc_dual_period` 结果另外量化了生产 PID 在两个离线周期下的差异；两类结果均不能覆盖实测调度周期或物理模型不确定性。

## 3. 物理模型边界

`physics_engine.py`/`physics_engine_2d.py` 的质量、重心、转动惯量、推力、阻尼、传感器延迟、舵机死区和速度均是历史假设。`physics_engine_2d.py` 的负推力矩只表达一个数学 plant 约定，不能推出实物舵机正负方向。没有经过测量的质量、CG、惯量、推力、摩擦、连杆几何和安装坐标前，模型继续保持 `PROTOTYPE`，不用于 PID 调参或飞行放行。

本轮比较明确记录 `nonconvergence_or_model_failure=not_run_no_plant`：没有运行物理 plant，因此没有把“收敛/发散”伪装成结果；原有历史模型和输出仍保留在原路径。

## 4. manufacturer_nominal 冲突解析门槛

修复前的失败先行场景把 SG92R 冲突组的行改为 `CONFIRMED_SERIES/conflict=false/conflict_group=null`，同时把绑定改为 `RESOLVED`，并提供格式合法但不存在的审查路径/URL。旧 checker 可接受这种记录，说明仅检查文本格式会绕过冲突保护。

当前 checker 保留显式 `RESOLVED` 流程，但要求：

- 审查引用和 source index 必须是仓库内、相对路径、存在的非空文件；
- `asset_ids`、完整参数 ID 集合和每条参数的 `source_url/source_revision` 必须与当前 immutable binding 精确一致；
- 解析记录必须绑定同一 conflict group、状态和本地审查文件。

这仍不是外部网站真实性或身份认证器；没有独立证据的远程来源不能仅凭 URL 自动提升为可信型号。当前 registry 没有新增 `RESOLVED` 组，SG92R 齿轮材料/重量和 ESP32-S3 后缀冲突继续保持审查状态。

## 5. 证据与复现

- 逐行生产/历史比较：`engineering/offline-evidence/r2_3/gnc_simulation_production_compare.json`
- 生成命令：`py -3 scripts/gnc_simulation_production_compare.py --write-json engineering/offline-evidence/r2_3/gnc_simulation_production_compare.json`
- 定向测试：`py -3 -m pytest scripts/tests/test_gnc_simulation_production_compare.py -q`
- 冲突 checker 测试：`py -3 -m pytest scripts/tests/test_manufacturer_nominal.py -q`
- 完整软件门禁：`py -3 scripts/check.py`

JSON manifest 绑定固定输入 SHA、逐行结果 SHA、源码 SHA、运行环境和命令；提交时报告生成所用 source SHA 与 artifact commit SHA。所有结论均限于软件证据，真实板卡周期、安装极性和 plant 仍需后续独立工程验证。

本次生成的绑定值为：`source_git_sha=757205cf55c78f690c1a2a4e18265c96c43e2d27`，`input_trace_sha256=3159546dc4042de02cdfe2d3e50f927bcc7080a3d8d84c1976317fbe6985e092`，`result_rows_sha256=6ba189562ae2f70cc94f4f60be32797aae32b1edd25a4603b8472c5e2bb4e9eb`，JSON SHA-256=`35fe293fe36238e8f2fe8b52f8abb47b572f0f96eedb5d7c09f92cd26d28b118`。artifact commit 会在交付记录中另行列出。

## 6. 停止条件

本轮不修改生产 PID 增益、控制符号、默认模式、E-STOP、回收判据或执行器权限；不进行硬件操作。下一次若要处理极性，只能先提交工程变更建议，给出已确认的传感器安装/舵机连杆坐标证据、验收向量和回归计划。
