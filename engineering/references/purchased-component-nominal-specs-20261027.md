# Project Ad Astra｜已采购组件的原厂标称规格与版本差异索引（V1）

> 2026-10-27 资料核查快照。**仅供离线选型、约束识别和接口研究；不是当前实物测量、硬件验收、CAD_START 或制造授权。**
>
> 采购事实源：`engineering/assets/project-asset-registry.yaml`，源标识 `SRC-PURCHASE-2026-10-22`。本索引基于采购登记和公开厂家资料；此前对话中的 24 张采购/商品截图虽曾提交，但原始逐图文件目前未链接进仓库的 `engineering/evidence/records/`。**这不表示用户没有提交过照片；不要求重复上传。**
>
> 创建依据的 main：`9a86da41c082bde79f4ea390a9ee4f63c8a41df5`。此文件不改变任何权威实物状态。来源网页随时间可变；核查日期 2026-10-27。

## 一、证据等级与使用限制

- `PURCHASE_CONFIRMED`：采购已记录，能支持型号/数量线索，不等于收货、单件身份及当前安装。
- `MANUFACTURER_NOMINAL_REFERENCE`：厂家对明确型号、封装或器件系列公布的标称参数；在卖家版本核对前，**不得当成该订单对应物的确定尺寸**。
- `SELLER_VARIANT_UNRESOLVED`：型号名称不唯一、厂商版本不明或商品描述与厂家资料冲突；不应悄然选择某版本。
- `PHYSICAL_OBSERVATION/MEASURED`：需要物理对象和实际原始记录；本研究没有产生此等级的新证据。

**单位特别提示**：芯片 package 尺寸 ≠ 搭载它的 GY-91 / USB-UART / 降压模块 PCB 外形；模块 PCB 尺寸 ≠ 安装件、插座、走线、线束包络；原厂推荐电气额定值 ≠ 卖家模块板卡的已验证工作能力。

## 二、已经查到的厂家标称参数及版本冲突

| 注册资产 ID | 采购描述 | 原厂可用参考 | 未解决的问题 / 明确禁止的推断 |
| --- | --- | --- | --- |
| `AST-MCU-APM32-001` | APM32F103C8T6 核心板×1 | Geehy APM32F103 **系列**为 Arm Cortex-M3，系列主频可达 96 MHz、供电 2.0–3.6 V；原厂提供 x4/x6/x8 型号 datasheet [S1] | 芯片系列信息不是当前核心板的晶振、布局、排针尺寸、实际引脚连接或烧录兼容结论；具体 C8 容量/封装须以对应子系列订货表核对 |
| `AST-MCU-ESP32S3-001` | ESP32-S3 DevKitC-1 N16R8 / 44pin×1 | 乐鑫 DevKitC-1 v1.1 列出 N8R8 等官方订货号 [S2]；旧 v1.0 文档列出 **N16R8V**（带 V），16MB Flash + 8MB PSRAM [S3] | **订单 N16R8 ≠ 自动等于 N16R8V**；不承认开发板 PCB、SPI 电压、引脚占用和 flash/PSRAM 组合为官方对应版本，直到卖家商品资料对齐 |
| `AST-WIFI-ESP01S-001` | ESP8266 ESP-01S×1 | Ai-Thinker ESP-01/01S 模块手册：24.7 × 14.4 × 11.0 mm（含排针），2.54mm 引脚间距；ESP8266 系列支持 2.4GHz Wi-Fi [S4][S5] | 模组标称值不包含额外 USB-TTL、适配底板或线束；真实 flash 容量、电源及 UART 仍需物理审查 |
| `AST-SENSOR-GY91-001` | GY-91，订单 MPU9250 + BMP280×1 | TDK MPU-9250 是 9 轴组合芯片，官方封装 3×3×1mm [S6]；Bosch BMP280 为 2.0×2.5×0.95mm、I²C/SPI，压力范围 300–1100hPa [S7] | 这是**两颗芯片**的参考而非 GY-91 整板尺寸。订单声称 MPU9250，不证明实板器件 ID、板轴、芯片真假或焊盘位置 |
| `AST-SERVO-SG92R-001` | SG92R 金属齿轮 9g 舵机×2 | TowerPro SG92R 产品页面标称 23×12.2×27mm、4.8V、2.5kgf·cm 堵转扭矩 [S8] | **重大型号冲突**：该官方型号标注碳纤维增强 POM 齿轮，订单描述为金属齿轮；厂家同一页面亦同时出现 9g 与描述表 12g，不能将外形、质量、齿轮材质、扭矩当作实际两只舵机的验收值 |
| `AST-POWER-LM2596-001` | LM2596S 可调降压板×1 | TI LM2596 芯片系列为 4.5–40V 输入、名义最高 3A、150kHz 降压稳压器 [S9] | **芯片参数不是卖家组装降压模块的实际供电额定值**；整体尺寸、元件品质、散热和输出保护仍未确认；不得据此批准供电系统 |
| `AST-RF-RA02-001` | SX1278 Ra-02 模组×2 | Ai-Thinker Ra-02 V1.1：SMD16，17×16×(3.2±0.1)mm，SPI，410–525MHz，供电 2.5–3.7V（典型 3.3V），天线 IPEX，参考质量 0.45g [S10] | **LoRa/RF 性能未验证**；不由厂家理论灵敏度、CRC 或功率规格推断区域发射许可、链路距离或身份认证。卖家模组版本与连接头尚未核实 |
| `AST-TOOL-CH340-001` | CH340G USB-TTL×1 | WCH 官方 CH340G 芯片资料：支持 5V/3.3V 芯片供电与 USB-UART 转换 [S11] | 芯片工作电压不能证明某块卖家转接板 TX/RX 的**实际逻辑电平**，也不能替代 USB 接口、排针或板尺寸 |
  
## 三、其余已采购项目（保留订单，不发明物理参数）

以下均继承注册表中的采购/数量状态。缺乏明确厂家及卖家 SKU 的，先登记 `SELLER_VARIANT_UNRESOLVED`，不要将随意搜索到的通用商品图或标称性能提升为已知参数。

| 注册资产 ID | 采购描述 / 数量 | 当前有效下一步 |
| --- | --- | --- |
| `AST-RF-SMA-IPEX1-001` | SMA–IPEX1/U.FL 转接×2 | 接口名称仅作商品声明；不可擅自确定实际插头极性、插合/射频匹配 |
| `AST-RF-ANT-WHIP-001` | 433MHz 短天线，订单约 5cm×1 | 保留卖家名义频段/外形；不推算增益、驻波、链路距离 |
| `AST-RF-ANT-35DBI-001` | 433MHz／3.5dBi／185mm、约 3m 馈线天线×1 | 3.5dBi 是订单描述；未测驻波、损耗、增益 |
| `AST-TOOL-STLINK-001` | ST-LINK V2×1 | 确认商品版本来源前不套用 ST 官方探针尺寸与引脚形态 |
| `AST-TOOL-LOGIC-001` | USB 逻辑分析仪×1 | 采样率、通道数、输入耐压取决于实际卖家变体 |
| `AST-TOOL-DMM-001` | 9205A-class 万用表×1 | 只保留采购类型；不把未校准设备等同计量标准 |
| `AST-TOOL-SCALE-001` | 10kg / 0.1g 电子秤×1 | 0.1g 为商家标称分辨力，不是准确度 |
| `AST-PROTOTYPE-BREADBOARD-001` | 830 孔面包板及线束×1 | 不推断额定电流或机械耐振性能 |
| `AST-PROTOTYPE-DUPONT-MM-001` | 20cm 公对公杜邦线×20 | 保留商品长度与数量，不推断导线线径和额定电流 |
| `AST-PROTOTYPE-DUPONT-FF-001` | 20cm 母对母杜邦线×20 | 同上 |
| `AST-TOOL-USB-AA-001` | USB-A 公对公数据线，订单 0.5m×1 | 未证明具体 USB 数据/供电协议或板卡兼容性 |
| `AST-TRAINING-STC89-001` | STC89C52RC 51 单片机学习套件×1 | 训练板厂家和 PCB 变体不明确 |
| `AST-TOOL-HOTGLUE-001` | 小号热熔胶枪及胶条×1 | 限非承力临时工装；无结构/耐温/耐振认证 |
| `AST-CHEM-PH-001` | pH 试纸×1 | 消耗品，暂无工程几何参数需求 |
| `AST-TOOL-TORCH-001` | 小型丁烷气喷枪×1 | 不授权任何推进、点火、燃料或发动机测试 |

**排除项**：LoRa 150mm 连接线×2 的历史订单标记“交易关闭/超时关闭”，按注册表 `TX-EXCLUDED-LORA-CABLE-001` 不计入已购。

**未见采购证据的当前方案对象**：EDF（具体风扇/电机总成）、ESC、主电池、BEC、当前整套机架/云台/结构件。与用户提供购买范围一致，不擅自增列为已购；也不得从过时 70/74/90mm CAD 猜回 EDF 型号。

## 四、对工程状态和 CAD 的实际含义

1. 现有 23 类资产**可立即开展芯片/标准模组的离线电气接口与标称几何研究**。这与“已确认实物测量”是两个独立状态。
2. 40 项 as-built 测量仍为 `MISSING`；CAD_START 原有 19 个测量/构型门槛不因本文件自动解除。厂家标称数值可进参考资料，不得写进 `MEASURED` 字段或打 `CONFIRMED_PRESENT` 标签。
3. 对未采购的 EDF 及未定义结构，不再以“用户必须拍 EDF”作为立即任务；应标记为**构型对象缺失 / 选型未决**。当前可先研究航电模块、固定传感器和纯软件集成接口。
4. 有确定的同型号原厂 CAD/封装时，可开展 **parametric reference/concept** 研究，但不能发布制造合格的当前装配。
5. 产品页面冲突或同名变体未确认时，记录 `VERSION_CONFLICT`，不得静默择优填写。

## 五、来源清单（2026-10-27 查阅）

- **[S1] Geehy APM32F103 系列及子系列资料入口**：https://www.gee-hy.com/product/fifth/APM32F103.html
- **[S2] Espressif DevKitC-1 v1.1 官方订货表**：https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html
- **[S3] Espressif DevKitC-1 v1.0 历史订货表**：https://docs.espressif.com/projects/esp-idf/en/v5.1/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1-v1.0.html
- **[S4] Ai-Thinker ESP-01/07/12 模组手册**：https://docs.ai-thinker.com/_media/esp8266/esp8266_series_modules_user_manual_en.pdf
- **[S5] Ai-Thinker ESP8266 系列官方入口**：https://docs.ai-thinker.com/en/esp8266/index.html
- **[S6] TDK InvenSense MPU-9250 芯片型号介绍**：https://www.invensense.tdk.com/en-us/news-media/press/invensense-sets-new-industry-standard-worlds-smallest-lowest-power-integrated-9-axis
- **[S7] Bosch BMP280 官方产品页**：https://www.bosch-sensortec.com/products/environmental-sensors/pressure-sensors/bmp280/
- **[S8] TowerPro SG92R 官方产品页**：https://torqpro.com/product/sg92r/
- **[S9] TI LM2596 芯片官方产品页**：https://www.ti.com/product/LM2596
- **[S10] Ai-Thinker Ra-02 V1.1 规格书**：https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Specification/Ra-02_V1.1%20Specification-20171219.pdf
- **[S11] 沁恒 CH340 产品页**：https://www.wch.cn/products/CH340.html

## 六、独立审计/后续小任务

- 从已有 24 张历史采购截图**如可直接索引**，仅为两个版本冲突（SG92R 齿轮及 ESP32-S3 N16R8）核对卖家明示品牌、SKU；不能访问原图时保留 unresolved，不重新要求用户提交整批订单。
- 后续如要录入可计算规格，单独建立 `manufacturer_nominal` 数据层，必须包含 `asset_id, model_claim, source_url, source_revision, property, value, unit, applicability, confidence, conflict`，并与 `engineering/as-built/` 的 `OBSERVED/MEASURED` 证据完全隔离。
- 不新建 CAD 验收、回收状态机修改或 RF 生产适配；保持 Issue #22/#23 开放。文档-only 修改可仅检查链接、格式、字段对应，不需要新增硬件测试。
