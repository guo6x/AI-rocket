# 单块实物读数 → 可回读的参考包络

日期：2026-11-10。适用于现有[五块板测量工作表](BOARD_MEASUREMENT_WORKBOOK.md)。

**本轮交付的是可运行的 CAD 输入/生成/独立回读工具，不是新测得的板卡尺寸。**
目前五份 JSON 模板全部空白，没有为 APM32 或 Ra-02 猜尺寸，也没有新增任何
已购物理板的 STEP。原 13 份参考 STEP、主参数/as-built/CAD authority 均未改。
19 项 CAD_START 门槛仍在，已验收装配仍为 0。

## 解决的具体问题

此前六页 PDF 可记录数据，但不能直接转换成有来源约束的 CAD。本工具把每块
实物单独处理：有一块的可靠数据即可先生成它的粗排布包络，不依赖其他四块补齐。
APM32、ESP32-S3、Ra-02 U1/U2、GY-91 沿用工作表编号；U1/U2 不互相冒充来源。

每次输出两个 **完整刚性外廓的数学盒子**：

- `OBSERVED_SPAN`：各项重复读数的均值所给出的外接盒。
- `UNCERTAINTY_EXPANDED`：各项最小/最大读数再向外扩展该项记录的不确定度。
  离散读数不会被均值抹平。它是输入不确定度估计下的参考外包络，
  **不是经过计量确认的最坏情况保证**，也没有偷偷加装配余量。

两个盒子都不是 PCB 实际轮廓或实体材料，不能用其体积算质量，不能由此生成
紧配合支架、孔位或宣布碰撞/装配通过。只有软件算术和 STEP 拓扑得到检查，
软件不认证测量人、照片真伪、量具准确度或实物身份。

## 私下准备输入，不公开原始照片

1. 复制 `measurement-record-templates/` 中对应实物的 JSON 到**私有工作目录**。
   也可运行下面的 `template` 命令。现成模板不含合成示例尺寸。
2. 按工作表 A 项人工整理真实读数和来源。每个尺寸保留至少三次读数，写明各自
   `uncertainty_mm` 及共同的 `uncertainty_basis`；不能把分辨率自动当准确度，
   不能用 0 代替未知不确定度。日期、量具、分辨率和断电状态都必须记录。
3. `identity` 写可读丝印/版号、排针/接口装配状态、方向与达到各极值的固定部件。
   读不到版号就明确写“版号不可读”并保留能区分该实物的照片，不要求重新证明购买。
   完整 XY 要含天线、USB 壳和排针塑料；仅裸模组或卖家 57×28 mm 不能冒充整板。
4. `evidence` 每项严格包含 `id`、`path`、`sha256`、`unit_id`。
   `id` 使用如 `EV-top` 的中性技术标识；`path` 是私有输入目录内的相对文件路径，
   如 `evidence/top.jpg`；`sha256` 为实际文件哈希；`unit_id` 必须与本表一致。
   对身份和九项测量分别填写 `evidence_ids`，指向支持该项的照片/原始读数文件。
   不允许空源、丢失文件、哈希变化、路径越界或符号链接。
5. 对照原始资料人工核对抄录后，填写 `reviewer_ref` 技术审阅标识，并将
   `reviewed_for_this_unit`、`transcription_checked` 设为 `true`。
   这是人工审阅声明，**不是靠打勾就能证明测量真实**。
6. 完整刚性外廓确已覆盖当前记录状态时，`coverage` 填
   `ALL_FIXED_RIGID_FEATURES_IN_CURRENT_RECORDED_STATE`。
   数据不完整就保留空白，不应为通过工具而填常见尺寸或改标签。

原始照片/订单和输入 JSON 留在私有目录，不提交公开仓库。输出只保存来源的
中性标识与哈希，不复制原图、原始文件路径、身份描述、量具说明或审阅人字段。
输出仍有实物尺寸，应按任务权限单独审查后再分享，工具不会自动上传。

当前生成器只接收人工审阅的**实物测量记录**。有可靠同版厂家图时仍可沿用独立的
厂家名义建模路径，不能把厂家标称值伪装成三次实测读数来喂这个入口。

## 运行

依赖沿用 `cad_reference/requirements.txt`，无新依赖。以下路径是示例，
输出须选新的独立目录，工具拒绝覆盖已有目录或记录。

```sh
mkdir -p /tmp/private-board-input
python cad_reference/board_measurement_envelope.py template \
  --unit APM32 --output /tmp/private-board-input/record.json
# 在私有目录补齐真实资料并人工审阅；空白模板会明确 REFUSED，且不生成 STEP。
python cad_reference/board_measurement_envelope.py generate \
  --input /tmp/private-board-input/record.json --output /tmp/apm32-reference-new
python cad_reference/board_measurement_envelope.py verify \
  --input /tmp/private-board-input/record.json --package /tmp/apm32-reference-new
```

同理可选择 `ESP32S3`、`RA02_U1`、`RA02_U2`、`GY91`。每次只处理一块。
不用重新采购、上电、焊接、插拔 IPEX 或为了试工具编造读数。

## 坐标、区间与验证

基准完全沿用工作表：TOP 看 +X 向右、+Y 向上，Z=0 为 PCB 下表面；
L 沿 Y，W 沿 X。H+ 与 H- 是非负距离，Z 范围是 `[-H-, T+H+]`，
不是从 PCB 中心对称拉伸。固定物可伸到负 X/Y，不会被裁去。

对每项读数 `r` 和人工给出的不确定度 `u`：

- 中心参考值为 `mean(r)`。
- 下界为 `min(r)-u`，上界为 `max(r)+u`。
- 扩展盒 Zmin 为 `-(max(H-)+u_H-)`；Zmax 为
  `max(T)+u_T+max(H+)+u_H+`，采用保守的独立区间相加，不假设误差独立并开方缩小。
- XYZ 外廓必须包含工作表给出的 PCB 跨度；正的 PCB 厚度/长宽不能因区间而变成零或负。
- 缺少数据、单位/基准错误、负的 H-、NaN/Inf、布尔/字符串数值、串板来源、未知字段
  或将未测接口填成 0/空列表时均拒绝；不得直接提升 fit/manufacturing 状态。

生成前校验源文件，导出后重新检查输入和来源是否改变。STEP 必须能由真实
CadQuery/OpenCascade 内核回读为一个有效闭合盒体，并检查全 XYZ 基准、尺寸和
数学体积。独立 `verify` 不信任旧 PASS：重读来源，重算区间，再回读两份 STEP；
仅改文件哈希不能掩盖尺寸或原点错误。失败输出记 `INCOMPLETE`，不是 PASS。

验算状态 `PASS_INPUT_AND_GEOMETRY_CHECKS_ONLY` **只表示输入一致性、算术和几何检查**。
它不更新工程权威文件，不解除测量门槛，不证明板级可安装、通电可用、无线合规、
结构强度、推进/飞行能力，也不执行任何硬件动作。

## 复现测试

```sh
python -m unittest cad_reference.tests.test_board_measurement_envelope -v
python -m unittest discover -s cad_reference/tests -v
python scripts/cad_baseline_gate.py --check
```

新增测试只在临时目录创建**明确标记为合成**的读数和 STEP，用于检验负坐标、
向下排针高度、读数离散、不确定度传播和错误路径；这些值与用户的任何实物无关。
没有将测试输出当成真实模型交付。

## 本轮本地验证记录

- 127 项 CAD 测试通过，其中本入口 28 项；使用真实 CAD 内核，不是跳过式通过。
- 28 项既有厂家名义参数/CAD authority 测试通过；两项审计也通过。
- 独审发现的“回读期间源文件变化仍可能 PASS”已修复，并增加来源、STEP 和回执
  在验证期间改变的回归；独审复跑通过。
- 13 份既有 STEP 与原提交逐字节相同；权威记录未改，19 项缺项、0 验收装配。
- `compileall` 和改动文本的空白检查通过。所有新数字测试均为合成临时夹具。
- 本地使用相关文件的精确快照，未运行完整固件/全软件构建；这些专项检查不能
  替代全项目 CI。远端结果必须对应实际提交查询，不沿用旧提交的成功状态。
