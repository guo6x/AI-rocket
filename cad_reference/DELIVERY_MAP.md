# AI-rocket 参考 CAD：从哪里开始

核对版本：`af0cce2496a90e65cd214620808a64e12cdfceb0`（PR #52，2026-11-13）。

本页把已有交付接成一条使用路线，不新增或替换几何，不宣布实物已装配。
**软件验证完成不等于完整产品完成。当前仍有 19 项 CAD_START 缺项，验收装配为 0。**

## Ra-02 来源版本提示

现有 Ra-02 参考仍绑定2017英文资料，不代表当前原厂完整公差包络。2026-06-29中文资料
出现不同公差标注；新版并未确认为用户持有版本，蓝色底板也没有因此得到尺寸。
详见 [README 的来源版本说明](README.md#ra-02-source-version-warning-reviewed-2026-11-13)。
本提示不改既有几何或验收状态。

## 我现在打开什么

| 要看什么 | 已有入口 | 实际范围 |
| --- | --- | --- |
| Ra-02 裸模组和两个传感器芯片 | [三页预览 PDF](examples/electronics-reference-review.pdf) | 9 份 STEP；不是 Ra-02 底板或 GY-91 整板 |
| APM32 芯片外形、48 个推荐焊盘 | [APM32 预览 SVG](examples/apm32-20261106/APM32F103C8T6_REFERENCE_ONLY.svg)、[说明](APM32_REFERENCE.md) | 2 份芯片实体参考和 1 份平面焊盘 STEP；不是向下焊核心板 |
| ESP32 商品图的两个尺寸数值 | [卖家跨度 SVG](examples/board-spans-20261107/ESP32S3_SELLER_SPANS_PLANAR_REFERENCE_ONLY.svg) | 1 份 57×28 mm 数学平面 STEP；天线伸出标注，不能当完整板长 |
| 手头已有某块板的可靠实测记录 | [记录→包络工具](BOARD_MEASUREMENT_ENVELOPE.md) | 单块即可推进，不必等五块全部齐全；模板目前为空 |
| 确认同版图纸是否已经找到 | [供应资料适用性审阅](../engineering/references/board-source-review-20261107.md) | 已购版本与别家相似板严格区分 |

**合计 13 份既有参考 STEP，不是 13 个可安装实物零件。三页 PDF 只覆盖其中 9 份。**
所有模型都不支持直接确定紧配合支架、孔位、装配、打印或制造。

## 我下载后怎样核对

使用匹配的可信源码快照及 `cad_reference/requirements.txt` 依赖，在仓库根目录执行：

```sh
python cad_reference/verify_package.py --kind ra02 --package cad_reference/examples/ra02-20261106
python cad_reference/verify_package.py --kind sensors --package cad_reference/examples/sensors-20261106
python cad_reference/generate_apm32_reference.py --check cad_reference/examples/apm32-20261106
python cad_reference/generate_board_span_reference.py --check cad_reference/examples/board-spans-20261107
python cad_reference/make_review_pdf.py --ra02 cad_reference/examples/ra02-20261106 --sensors cad_reference/examples/sensors-20261106 --check cad_reference/examples/electronics-reference-review.pdf
python scripts/cad_baseline_gate.py --check
```

前五项检查交付文件及来源的一致性，最后一项确认工程门槛未被错误解除。
这些命令均不启动硬件、不改写被检查包，也不认证实物身份。
不要混用不同源码版本的回执；不要为消除失败直接重算哈希。

## 下一步真正能推进产品的是什么

1. **有同款同版整板厂家图：** 先核实与所购版本的对应关系，再走厂家名义参数建模。
   不能拿不同底板的尺寸拼成一块板，也不能把标称值伪装成三次实测。
2. **已有可信实物几何记录：** 走记录→包络入口。先 APM32 或任一 Ra-02 即可；
   它输出上下突出和不确定度包络，但仍不能代替孔位/接口/线缆净空数据。
3. **两类资料都没有：** 不继续生成猜测外形。已有购买证明无需重复收集，
   不要求购买尚未选定的部件，更不能宣称可直接组装。

目前 Ra-02 蓝色底板、APM32 向下焊版本、GY-91 紫板、ESP32 Type-C 版本的完整整板
对应证据仍不足。继续有价值的纯线上工作是取得这些版本的可靠图纸，而不是再造
芯片盒子、重复合成参数测试或增加另一份同义验收表。

## 本次软件状态和边界

- [CAD CI](https://github.com/guo6x/AI-rocket/actions/runs/43372757141)：成功。
- [完整软件 CI](https://github.com/guo6x/AI-rocket/actions/runs/43372757237)：成功。
- 上述结果仅对应页首提交，不自动覆盖后续提交。
- 本页不涉及飞控、上电、执行器、射频、推进、制造或载人操作。
