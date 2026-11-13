# 已购板级资料与 ESP32 卖家尺寸参考

2026-11-07。**本轮不是完整板卡、装配或制造交付。**

从原采购图继续追查整板资料，没有再用芯片外形充当板卡。
实际可生成的新增几何只有 ESP32 商品图明示的 **57 × 28 mm 数值矩形**：
[STEP](examples/board-spans-20261107/ESP32S3_SELLER_SPANS_PLANAR_REFERENCE_ONLY.step)
与[带标注预览](examples/board-spans-20261107/ESP32S3_SELLER_SPANS_PLANAR_REFERENCE_ONLY.svg)。

## 这个参考能做什么

可以在 CAD 中查看、量取卖家标注的两个数值，并沿着同一来源清单补充后续真实尺寸。
STEP 只有一个数学平面，没有假定板厚，不是“厚度为零的实物”。
矩形中心与四角是抽象绘图基准，不是 PCB 的真实基准或边界。

原购物图 `1000013496.jpg` 选项是 ESP32-S3 N16R8、44 脚，商品缩略图写 Type-C、
57 mm、28 mm。**黑色天线部分伸出图中 57 mm 的标注界线，不能把57 mm称为整个
开发板的总长。** 标注端点的工程定义也没有得到板图确认。
这里仅照录打印的尺寸数值，没有按像素比例测量。

不能用于碰撞检查、安装孔、支架、壳体、线缆净空或整板体积估算。
没有凭常见的1.6 mm板厚、2.54 mm排针距或其他ESP32板模型补齐未知参数。
实物一致性、精度、公差、PCB轮廓、总高、排针、USB位置与突出、天线净空仍未知。

## 来源为什么没有直接变成整板

- **Ra-02带底板：** 找到了原厂带DXF的转接板尺寸包和两家卖家的整板尺寸，
  但没有证据把其中任一版本绑定到已购蓝色底板，故没有生成替代整板。
- **APM32向下焊：** 找到了同店当前商品系列图，但没有所购版本的机械图或
  向下排针完整包络。通用Blue Pill外形不能直接替代。
- **GY-91紫板：** 其他卖家的常见尺寸不构成所购紫板版本的对应证据。
- **ESP32：** 找到了同店当前清晰双Type-C图，仍无机械尺寸。
  官方Micro-USB版本或其他同名Type-C版本都没有替换这笔已购记录。

查看[逐来源适用性和下一步](../engineering/references/board-source-review-20261107.md)。
购买证据已经恢复，本轮不再要求重新上传或重新证明购买。

## 参数化源码与复现

- [来源与两个数值参数](board-span-reference-inputs.json)
- [生成器及只读核验](generate_board_span_reference.py)
- [交付目录及核验回执](examples/board-spans-20261107/)

在既有 Python 3.12 / CadQuery 环境中：

```sh
python cad_reference/generate_board_span_reference.py --output /tmp/esp32-seller-spans-new
python cad_reference/generate_board_span_reference.py --check /tmp/esp32-seller-spans-new
python cad_reference/generate_board_span_reference.py --check cad_reference/examples/board-spans-20261107
python -m unittest discover -s cad_reference/tests -v
```

参数集中在JSON中，但修改尺寸、来源或未知值后必须重新审阅来源。
脚本拒绝未审阅的输入和已有输出目录。导出后重新读入STEP，检查平面、四个直边、
四角、面积及57×28跨度；没有生成STL。核验几何数值不等于核验卖家尺寸或实物。

原图含私人订单信息，继续保留在私有位置，不进仓库。公开manifest只含文件名、
摘要、商品选项和技术尺寸摘录；没有原图访问权的读者不能只凭摘要独立核验原图。
参数权威层、as-built、19项CAD_START阻塞、零个已接受机械装配均未变。

没有采购、联系商家、上电、无线发射、执行器、推进、飞行或制造操作。

## 本轮验证记录

- Python 3.12 / CadQuery 2.7.0：99项CAD测试通过，包含新增10项平面参考检查。
- 28项既有manufacturer-nominal/CAD-authority测试通过。
- 交付STEP实际重新导入为1个平面、0个实体，跨度57×28 mm。
  SVG由已复核几何生成，渲染后检查文字和尺寸标注。
- 参数注册表检查通过；结构检查为PASS、hardware_status为NOT_EVALUATED。
  CAD账目仍保留19个阻塞，不构成新的验收。
- 完整本地`python scripts/check.py`因缺少PlatformIO在启动检查阶段失败，
  没有声称全项目本地通过；远端CI独立检查对应提交。
- 原图含义另经独立审阅，确认57 mm标注不包括突出的天线部分。
