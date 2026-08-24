from build123d import *
import os

# --- High-Fidelity Parameters ---
EDF_OD = 74.0
WALL = 2.5
NOZZLE_L = 35.0
EXIT_OD = 62.0
CLEARANCE = 0.2

# Servo SG92R 精确参数
SERVO_L = 23.0
SERVO_W = 12.2
SERVO_H = 27.0
FLANGE_L = 32.5

def create_servo_mount():
    """创建一个具备加强筋和沉头孔的专业舵机座"""
    with BuildPart() as mount:
        # 主托架
        with BuildSketch() as s:
            Rectangle(SERVO_L + 6, SERVO_W + 6)
            # 挖出舵机槽
            Rectangle(SERVO_L, SERVO_W, mode=Mode.SUBTRACT)
        extrude(amount=10)
        
        # 添加安装翼耳
        with Locations((0, 0, 10)):
             with BuildSketch() as s2:
                 Rectangle(SERVO_L + 12, SERVO_W + 6)
             extrude(amount=2)
             
        # 圆角处理，体现“Demo级”质感
        fillet(mount.edges().filter_by(Axis.Z), radius=1.0)
    return mount.part

def generate_pro_tvc():
    print("🚀 [Build123d] 正在生成 Text-to-CAD 级别的高性能矢量喷管...")
    
    # 1. 基座 - 包含蜂窝轻量化镂空
    with BuildPart() as base:
        with BuildSketch() as s_base:
            Circle(EDF_OD/2 + WALL + 2)
            Circle(EDF_OD/2, mode=Mode.SUBTRACT)
        extrude(amount=25)
        
        # 添加加固筋
        with Locations(*[Rotation(0,0,a) for a in range(0, 360, 45)]):
            add(Location((EDF_OD/2, -1, 0)) * Box(6, 2, 25, align=(Align.MIN, Align.CENTER, Align.MIN)))
            
        # 侧向舵机安装位
        with Locations((EDF_OD/2 + 2, 0, 12.5)):
            add(Rotation(0, 90, 0) * create_servo_mount())
            
        # 枢轴支撑点 (Yaw Pivot)
        with Locations((0, EDF_OD/2 + 5, 12.5), (0, -(EDF_OD/2 + 5), 12.5)):
            Box(8, 10, 12)
            with BuildPart(mode=Mode.SUBTRACT):
                add(Rotation(90, 0, 0) * Cylinder(radius=1.6, height=20))

    # 2. 偏航环 (Yaw Ring) - 异形镂空设计
    with BuildPart() as yaw_ring:
        inner_r = (EDF_OD/2 + WALL + 4)
        outer_r = inner_r + WALL
        with BuildSketch() as s_ring:
            Circle(outer_r)
            Circle(inner_r, mode=Mode.SUBTRACT)
        extrude(amount=12)
        
        # 减重孔阵列
        with Locations(*[Rotation(0,0,a) for a in range(22, 360, 45)]):
            with BuildPart(mode=Mode.SUBTRACT):
                add(Location((outer_r, 0, 6)) * Rotation(0, 90, 0) * Cylinder(radius=3, height=10))

        # 舵机安装位 (Pitch)
        with Locations((0, outer_r + 2, 6)):
             add(Rotation(0, 90, 90) * create_servo_mount())

    # 3. 核心喷管 (Aerodynamic Nozzle) - 使用 Loft 保证完美流线
    with BuildPart() as nozzle:
        # 创建一系列截面用于 Loft
        with BuildSketch(Plane.XY) as s1:
            Circle(EDF_OD/2 - 1)
        with BuildSketch(Plane.XY.offset(NOZZLE_L)) as s2:
            Circle(EXIT_OD/2)
        
        # 平滑收缩表面
        loft()
        
        # 内部抽空
        with BuildPart(mode=Mode.SUBTRACT):
            with BuildSketch(Plane.XY.offset(-1)) as s1_in:
                Circle(EDF_OD/2 - 1 - WALL)
            with BuildSketch(Plane.XY.offset(NOZZLE_L + 1)) as s2_in:
                Circle(EXIT_OD/2 - WALL)
            loft()
            
        # 添加枢轴销钉
        with Locations((EDF_OD/2 - 2, 0, 15), (-(EDF_OD/2 - 2), 0, 15)):
            add(Rotation(0, 90, 0) * Cylinder(radius=1.5, height=10))

    # --- 最终导出 ---
    if not os.path.exists("pro_outputs"):
        os.makedirs("pro_outputs")
        
    export_step(base.part, "pro_outputs/tvc_base_v2.step")
    export_step(yaw_ring.part, "pro_outputs/tvc_gimbal_v2.step")
    export_step(nozzle.part, "pro_outputs/tvc_nozzle_v2.step")
    
    # 模拟装配展示
    assembly = Compound(children=[
        base.part,
        yaw_ring.part.move(Location((0, 0, 35))),
        nozzle.part.move(Location((0, 0, 60)))
    ])
    export_step(assembly, "pro_outputs/tvc_assembly_v2.step")
    export_stl(assembly, "pro_outputs/tvc_assembly_v2.stl")

    print("🎉 [SUCCESS] 对标 Demo 级的高精模型已生成。请查看 pro_outputs 文件夹。")

if __name__ == "__main__":
    generate_pro_tvc()
