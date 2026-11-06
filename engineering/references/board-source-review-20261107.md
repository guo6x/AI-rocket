# 已购板级外形：来源适用性复核

日期：2026-11-07 UTC。起点：PR52 / `9d32832`。
目的：取得已购整板的真实边界与接口证据，不再用芯片模型代替整板。
以下是资料和可用模型的核验，不是装配确认或新的采购清单。

## Ra-02：确有整板资料，但不能与已购蓝色底板混用

已购选项为“RA-02带底板（原装安信可）”，商品缩略图是一块蓝色底板。
这只说明卖家所售选项，不能证明底板是原厂某一版。既有17×16 mm模组参考不变。

| 来源 | 公开尺寸 / 文件 | 本轮处置 |
| --- | --- | --- |
| [安信可LoRa-Kit资料页][AI]，所链[规格书V1.0.0][PDF]第8页图5 | 黑色Ra-01转接板，26.0±0.2 mm方板，排间22.86±0.2 mm、节距2.54±0.1 mm；第9页列可搭载Ra-02 | 原厂板的可追溯资料，但未绑定所购蓝板，不能移植其尺寸或孔位 |
| 同页[Ra-01转接板V2.0尺寸ZIP][ZIP] | ZIP内有PNG及DXF；不是所购Ra-02蓝板的STEP | 已下载并确认文件类型，留作候选对照，不导入当前装配 |
| [广华SX-1278DE][CPU] | 卖家标28×21×5 mm，随附2条8P排针；页面另声明供应商尺寸可能不同 | 未证实与原采购卖家同版，且5 mm是否含焊接后的排针未定义，不作为完整安装高度 |
| [WAVGAT Ra-02][WAV] | 当前页面描述28×20.3 mm装配尺寸，要求核实批次 | 与广华的宽度不同；不能拼用两家的长宽高，也不能把差异解释成同一板公差 |
| [LaskaKit LA162030][LAS] | 提供裸Ra-02 datasheet链接，无可核实整板外廓 | 裸模组PDF不能补齐转接板 |

厂商PDF原字节 SHA-256：
`3282b6cd9bab344c3c36b6ce95699fba27da1df54da5f827427e4d7a8d47fd57`，
1,185,821 bytes；第8页原始像素已检查。
尺寸ZIP SHA-256：
`3420cbff3dd4393ce32df14899d09222ad362ce88e3ee6dffcce9cbacabf2a60`，
72,617 bytes；内含PNG 29,134 bytes与DXF 711,517 bytes。
以上哈希只标识本轮读到的文件，不证明适用于所购实物。

**Ra-02剩余关键输入：** 同款底板版本对应、底板边界、引脚位置/方向/高度、
模组叠高，以及IPEX接头和已购转接线插接后的包络。当前没有足够证据生成它们。
不把26、28、20.3、21 mm任选其一当成已购尺寸。

## ESP32-S3：有两个卖家打印数值，但不是完整外廓

原购物图 `1000013496.jpg` 已由两次独立像素审阅确认：选中N16R8、44脚；
缩略图标Type-C、57 mm、28 mm。天线部分越过57 mm的标注边界，因此不能把该数值
称作含天线的整板总长。尺寸端点定义、接口突出、排针与公差没有工程图支撑。

本轮新增[57×28 mm数学平面参考][REF]，只把这两个打印数值变成可量取的CAD对象，
不提供真实PCB轮廓、三维占位或装配碰撞结论。板厚与总高仍为null。

通过[同店商品公开索引][ESPSELLER]定位到阿里商品CDN上的
[清晰正面图][ESPIMG]及[店铺标识系列图][ESPSTORE]。
图中能看出双Type-C和天线突出，但没有尺寸；当前页面不是历史订单批次的工程图。
这只缩小后续寻找卖家板图的方向，不构成对版认证，不替代原购买证据。
索引本身为第三方页面，来源关联置信度低于原购物图。

## APM32和GY-91：版本线索保留，整板未知

APM32所选仍是向下焊。通过[同店当前系列索引][APMSELLER]及
[商品CDN系列图][APMIMG]确认页面确实同时展示C6T6、C8T6与APM32，
但当前“原装STM32升级款”选项不等于已购APM32向下焊版本。
本轮没有找到对应版本的板厚、边界、USB与向下排针包络；不套用通用Blue Pill模型。

GY-91所选仍是紫板翻新芯片。作为对照，[Art of Circuits自家GY-91][GY]
标14.3×20.5 mm及2.54 mm间距，但没有证据绑定到所购卖家和版本。
不生成当前板卡外形，也不由“翻新”一词推断性能或故障。

## 本轮产物、剩余工作与边界

- 新增1个ESP32卖家打印数值的平面STEP、SVG、参数化源码和来源manifest。
  该对象不是整板轮廓，更不是完整装配。原图未复制到仓库。
- 找到原厂LoRa转接板DXF及可追溯卖家尺寸，明确了为什么还不能用于已购底板。
- 后续优先需要同款/同版板图或既有实物几何资料；首先追Ra-02底板和APM32向下
  排针版本。没有再把购买证据列为缺失，没有向用户重复索要购物截图。
- 当前未选购的EDF、ESC、主电池和框架不会被写成已有实物。
- 没有更新主参数注册表、as-built或CAD authority，没有制造/装配放行。
- 未与商家通信、登录账户、下单或操作硬件。

几何复核和本地验证见[交付说明][REF]。远端CI结果须对应后续实际提交另行确认。

[AI]: https://docs.ai-thinker.com/LoRa-Kit/index.html
[PDF]: https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Specification/LoRa-Kit_V1.0.0%E8%A7%84%E6%A0%BC%E4%B9%A6-20240511.pdf
[ZIP]: https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Support/Ra-01%E8%BD%AC%E6%8E%A5%E6%9D%BF_V2.0%E5%B0%BA%E5%AF%B8%E5%9B%BE.zip
[CPU]: https://shop.cpu.com.tw/product/59968/info/
[WAV]: https://wavgat.com/product/sx1278-lora-ra-02-spread-spectrum-wireless-module-433mhz-long-distance-rf-communication-module/
[LAS]: https://www.laskakit.cz/en/ai-thinker-ra-02-sx1278-433mhz-lora-modul-s-adapterem/
[ESPSELLER]: https://tao.hooos.com/goods_QKnxMn0tQtB7DPaa83IXQ2hatQ-WkRwwpuQgd5OyDwua.html
[ESPIMG]: https://img.alicdn.com/i2/1070042715/O1CN01BM7Mbw1VvWKJHqSIP_%21%211070042715.jpg_500x500q90
[ESPSTORE]: https://img.alicdn.com/i1/1070042715/O1CN01PbRdkb1VvWQLYlrP3_%21%211070042715.jpg_500x500q90
[APMSELLER]: https://tao.hooos.com/goods_PAoPwDt3tP5OWyFvvVUPt6-wzQnnOsbDgnQxq4FN.html
[APMIMG]: https://img.alicdn.com/i2/2206446147687/O1CN01fbGhZY26ehgnuTUnc_%21%212206446147687.jpg_500x500q90
[GY]: https://artofcircuits.com/product/10dof-gy-91-4-in-1-mpu-9250-and-bmp280-multi-sensor-module
[REF]: ../../cad_reference/BOARD_SPANS_REFERENCE.md
