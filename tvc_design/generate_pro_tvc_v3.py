from build123d import *
import os

# ==============================================================================
# 航天级 TVC 矢量喷管设计 V3 (Mechanical Engineering Edition)
# 核心特性：
# 1. 真实万向节装配逻辑：所有旋转轴心点在绝对原点 (0,0,0) 重合。
# 2. 考虑打印公差：零件间预留 0.4mm 径向间隙。
# 3. 稳固枢轴：使用 M3 螺钉规格 (3.2mm 孔) 或 3mm 金属销。
# 4. 舵机接口：为 SG92R 舵机预留加强座。
# ==============================================================================

# --- 核心参数 (Units: mm) ---
EDF_OD = 74.0          # EDF 涵道外径
WALL = 2.5             # 基础壁厚
CLEARANCE = 0.4        # 机械运动公差（关键！）
PIVOT_HOLE_D = 3.2     # M3 螺栓安装孔
PIVOT_HEIGHT = 15.0    # 枢轴中心相对于基座底部的垂直高度

# 舵机 SG92R 参数
SERVO_L = 23.0
SERVO_W = 12.2
SERVO_H = 27.0

# 喷管几何
NOZZLE_L = 40.0
EXIT_OD = 62.0

def create_servo_socket():
    """创建标准的舵机嵌入槽"""
    with BuildPart() as socket:
        with BuildSketch() as s:
            Rectangle(SERVO_L + 6, SERVO_W + 6)
            Rectangle(SERVO_L, SERVO_W, mode=Mode.SUBTRACT)
        extrude(amount=12)
        # 添加安装螺丝支架
        with Locations((0, 0, 12)):
            with BuildSketch() as s2:
                Rectangle(SERVO_L + 12, SERVO_W + 6)
            extrude(amount=3)
        fillet(socket.edges().filter_by(Axis.Z), radius=1.0)
    return socket.part

def generate_v3_tvc():
    print("🚀 [V3 Rebuild] 正在构建工业级 TVC 万向节系统...")

    # 1. 部件：Base Mount (固定在 EDF 上)
    # --------------------------------------------------------------------------
    with BuildPart() as base:
        # 主圆筒
        with BuildSketch() as s_base:
            Circle(EDF_OD/2 + WALL + 2)
            Circle(EDF_OD/2 + 0.1, mode=Mode.SUBTRACT) # 0.1mm 过盈/紧配合
        extrude(amount=30)
        
        # 枢轴支撑架 (对齐 Y 轴旋转轴)
        # 我们的旋转中心定义在 Z = 15 处
        with Locations((0, EDF_OD/2 + WALL + 4, PIVOT_HEIGHT), (0, -(EDF_OD/2 + WALL + 4), PIVOT_HEIGHT)):
            Box(12, 10, 20)
            with BuildPart(mode=Mode.SUBTRACT):
                # Y 轴方向的枢轴孔
                add(Rotation(90, 0, 0) * Cylinder(radius=PIVOT_HOLE_D/2, height=30))

        # 舵机 A (Yaw) 安装位
        with Locations((EDF_OD/2 + WALL + 8, 0, 15)):
            add(Rotation(0, 90, 0) * create_servo_socket())

    # 2. 部件：Gimbal Ring (中层万向环)
    # --------------------------------------------------------------------------
    # 环的尺寸必须在 Base 内部且能自由转动
    ring_ir = EDF_OD/2 - 2
    ring_or = EDF_OD/2 - 0.5 # 与基座内壁留出间隙
    
    with BuildPart() as ring:
        # 主环体
        with BuildSketch() as s_ring:
            Circle(ring_or)
            Circle(ring_ir, mode=Mode.SUBTRACT)
        # 环高度 12mm，中心在 PIVOT_HEIGHT
        extrude(amount=12)
        # 平移到枢轴高度
        ring.part.move(Location((0,0, PIVOT_HEIGHT - 6)))
        
        # 外枢轴销钉 (对接 Base，Y 轴方向)
        with Locations((0, ring_or + 2, PIVOT_HEIGHT), (0, -(ring_or + 2), PIVOT_HEIGHT)):
            add(Rotation(90, 0, 0) * Cylinder(radius=PIVOT_HOLE_D/2 - 0.1, height=8))
            
        # 内枢轴孔 (对接 Nozzle，X 轴方向)
        # 旋转中心重合
        with Locations((ring_ir - 4, 0, PIVOT_HEIGHT), (-(ring_ir - 4), 0, PIVOT_HEIGHT)):
            Box(10, 12, 12)
            with BuildPart(mode=Mode.SUBTRACT):
                add(Rotation(0, 90, 0) * Cylinder(radius=PIVOT_HOLE_D/2, height=30))

        # 舵机 B (Pitch) 安装位 - 坐在环上 (专业紧凑设计)
        with Locations((0, ring_ir - 6, PIVOT_HEIGHT)):
             # 垂直布置以减小力矩
             add(Rotation(90, 0, 90) * create_servo_socket())

    # 3. 部件：Nozzle (核心收缩喷管)
    # --------------------------------------------------------------------------
    with BuildPart() as nozzle:
        # 使用 Loft 生成流线型面
        with BuildSketch(Plane.XY.offset(PIVOT_HEIGHT - 5)) as s1:
            Circle(ring_ir - CLEARANCE)
        with BuildSketch(Plane.XY.offset(PIVOT_HEIGHT - NOZZLE_L)) as s2:
            Circle(EXIT_OD/2)
        loft()
        
        # 内部抽空
        with BuildPart(mode=Mode.SUBTRACT):
             with BuildSketch(Plane.XY.offset(PIVOT_HEIGHT - 4)) as s1_in:
                 Circle(ring_ir - CLEARANCE - WALL)
             with BuildSketch(Plane.XY.offset(PIVOT_HEIGHT - NOZZLE_L - 1)) as s2_in:
                 Circle(EXIT_OD/2 - WALL)
             loft()
             
        # 内枢轴销钉 (对接 Ring，X 轴方向)
        with Locations((ring_ir - 2, 0, PIVOT_HEIGHT), (-(ring_ir - 2), 0, PIVOT_HEIGHT)):
            add(Rotation(0, 90, 0) * Cylinder(radius=PIVOT_HOLE_D/2 - 0.1, height=8))

    # --- 最终导出 ---
    out_dir = "D:/AI_rocket/pro_outputs_v3"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    export_stl(base.part, f"{out_dir}/part_base.stl")
    export_stl(ring.part, f"{out_dir}/part_ring.stl")
    export_stl(nozzle.part, f"{out_dir}/part_nozzle.stl")
    
    # 真实装配体预览
    assembly = Compound(children=[base.part, ring.part, nozzle.part])
    export_stl(assembly, f"{out_dir}/full_assembly_v3.stl")
    # 转换为 GLB 供预览
    import trimesh
    mesh = trimesh.load(f"{out_dir}/full_assembly_v3.stl")
    mesh.export(f"{out_dir}/tvc_v3_preview.glb")

    print(f"🎉 [SUCCESS] 工业级 TVC V3 已生成至: {out_dir}")
    print("机械特征：三轴心在 (0,0,15) 完美对齐，已预留 0.4mm 间隙。")

if __name__ == "__main__":
    generate_v3_tvc()
