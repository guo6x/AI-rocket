# 铸剑局：NX 12.0 自动化建模技术报告 (完结)

**项目名称**：Ad Astra - 自动化整流罩生成
**环境**：NX 12.0, Python 3 (NXOpen)
**状态**：功能已完全打通

## 1. 核心技术成果
我们成功建立了脱离 NX 软件手工图形界面的 **“代码 -> 物理几何实体”全自动生成流水线**。
这证明未来“铸剑局”上位机平台能够直接下发数字指令（如空气动力学优化后的函数参数），在后台超算或工作站中无人值守地输出可制造（3D打印/机加）的模型文件。

## 2. 解决的技术难点

### 2.1 冯·卡门外形抽象与无约束样条构建
- **难点**：NX 的 `ConstraintManager` 在构建复杂方程生成点组成的密集曲面线条时，会因为端点切线或曲度计算失败产生 `Cannot compute bcurve`。
- **方案**：降级抛弃了几何拓扑约束追踪，使用原点矩阵组成的 `ThroughPoints` 类型 `StudioSplineBuilderEx`，精确拟合数学方程输出点。

### 2.2 闭盒抽壳导致实心杯碗状的规避
- **难点**：在建立 Solid Revolve 之后执行抽壳 (Shell) 默认会导致产生有底座的“杯子”，而不是两头中空的整流罩。
- **方案**：利用 Python 逆向反射遍历了生成的几何对象的面 (`GetFaces()`)，并严格过滤枚举值常量 `FaceType == 1 (Planar)`，将提取出的唯一平面特征底面送入 `RemovedFacesCollector`。达成完美的底端去皮开口，形成真皮悬空整流外罩。

### 2.3 命令行动调与外部参数注入
- **集成方式**：脚本末尾已经介入了 `sys.argv` 支持。
- **调用语法**：
  外部调用只需依赖 `UGS run_journal.exe`，无需搭建完整的 C# .NET 编译环境：
  ```bat
  Set UGII_BASE_DIR=C:\Siemens\NX 12.0 
  "%UGII_BASE_DIR%\NXBIN\run_journal.exe" generate_fairing.py -args Diameter=120 Length=350 Thickness=2.5
  ```

## 3. 下一步建议 (Next Steps)
1. **CFD 流体计算联动**：生成的 `.prt` 能够自动转换为 STEP 文件格式。我们可以用 AI 跑 OpenFOAM 直接计算不同直径/长度的马赫数阻力。
2. **连接前端系统**：用这套脚本库接入我们的平台 Vue Dashboard，前端滑块改变外形，点击按钮后端5秒出 3D 图给用户提供下载。
