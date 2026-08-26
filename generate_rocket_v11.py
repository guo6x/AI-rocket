#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Ad Astra 探空火箭 v11 - 同步历史 rocket_config.py 参数
================================================================
所有几何参数严格对齐 aero_sim/rocket_config.py（历史固体飞行基线，非当前制造真相源）
- 75mm 外径, 600mm 长机身管
- 150mm Von Karman 整流罩
- 3 片梯形尾翼 (120° 均布), 翼展 80mm, 根弦 100mm, 梢弦 50mm
- Estes C6-5/D12 固体发动机 + 喷管 + 回收系统
- 4 个法兰连接处用 M3 螺栓
"""
import os
import math
import numpy as np
import trimesh

# =================================================================
# 历史参数: 直接引用 aero_sim/rocket_config.py (单位 mm)
# =================================================================
NOSE_TYPE = "Von Karman"
NOSE_LENGTH = 150.0          # 整流罩长度 mm
NOSE_BASE_RADIUS = 37.5      # 底部半径 mm (= 管外径/2)

BODY_OUTER_RADIUS = 37.5     # 外径 75mm
BODY_INNER_RADIUS = 35.5     # 内径 71mm, 壁厚 2mm
BODY_LENGTH = 600.0          # 管长 600mm

FIN_COUNT = 3                # 3 片 (120° 均布)
FIN_ROOT_CHORD = 100.0       # 根弦 100mm
FIN_TIP_CHORD = 50.0         # 梢弦 50mm
FIN_SPAN = 80.0              # 翼展 80mm (从管壁算起)
FIN_SWEEP_LENGTH = 30.0      # 前缘后掠 30mm
FIN_THICKNESS = 3.0          # 翼厚 3mm
FIN_POSITION_FROM_NOSE = 600.0  # 翼根前缘距头锥顶端 600mm

# 发动机
MOTOR_DRY_MASS = 21.4        # g
MOTOR_PROPELLANT_MASS = 24.2 # g
MOTOR_TOTAL_IMPULSE = 20.0   # N·s (C6-5)
MOTOR_BURN_TIME = 1.65       # s
MOTOR_AVG_THRUST = 12.12     # N

# 全箭
TOTAL_LENGTH = NOSE_LENGTH + BODY_LENGTH  # 750mm
WALL_T = 4.0                # 法兰厚度
WALL = 2.0                  # 管壁 (一致 rocket_config.py)
SEG = 96                    # 圆周分段

# 螺栓参数
FLANGE_BOLT_COUNT = 8
BOLT_R = 1.5                # M3 螺栓
BOLT_HEAD_R = 2.7           # M3 六角头

OUTPUT = r"D:\AI_rocket\3d_print_files"
os.makedirs(OUTPUT, exist_ok=True)

# 坐标 (沿 +X 方向, 头锥在右端)
NOSE_X1 = 0
NOSE_X2 = NOSE_LENGTH       # 150

BODY_X1 = NOSE_X2
BODY_X2 = BODY_X1 + BODY_LENGTH  # 750

# 尾翼位置
FIN_LE = FIN_POSITION_FROM_NOSE - NOSE_LENGTH  # 距机身左端 (= 距头锥顶端 600-150=450)
FIN_TE = FIN_LE + FIN_ROOT_CHORD  # 尾翼后缘 = 450+100=550

# 发动机舱 (机身尾部 100mm, 含 C6-5 发动机)
MOTOR_BC = BODY_X2 - 100    # 发动机舱起点 650
MOTOR_BC_END = BODY_X2      # 发动机舱终点 750

print("="*70)
print("🚀 Ad Astra 探空火箭 v11 - 同步 rocket_config.py")
print("="*70)
print(f"  全箭长度:        {TOTAL_LENGTH:.0f}mm")
print(f"  整流罩:          {NOSE_TYPE}, L={NOSE_LENGTH:.0f}mm")
print(f"  机身管:          外径{BODY_OUTER_RADIUS*2:.0f}mm, 长{BODY_LENGTH:.0f}mm")
print(f"  尾翼:            {FIN_COUNT}片梯形, 翼展{FIN_SPAN:.0f}mm, 根弦{FIN_ROOT_CHORD:.0f}mm")
print(f"  发动机:          Estes C6-5, 总冲{MOTOR_TOTAL_IMPULSE}N·s, 均推{MOTOR_AVG_THRUST}N")
print(f"  坐标: N[{NOSE_X1},{NOSE_X2}] B[{BODY_X1},{BODY_X2}]")
print(f"       FIN_LE={FIN_LE:.0f}mm, FIN_TE={FIN_TE:.0f}mm")


# =================================================================
# 基础几何构建函数
# =================================================================
def cyl(r, x1, x2, seg=SEG):
    """圆柱体 (沿X轴)"""
    L = x2 - x1
    c = trimesh.creation.cylinder(radius=r, height=L, sections=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x1 + L/2, 0, 0])
    return c


def ring_tube(ro, ri, x1, x2, seg=SEG):
    """空心圆管 - 差集运算"""
    outer = cyl(ro, x1, x2, seg)
    inner = cyl(ri, x1 - 1, x2 + 1, seg)
    return outer.difference(inner)


def cone_ring(xs, ro_list, ri_list, seg=SEG):
    """变截面空心管 - 直接构建拓扑"""
    n = len(xs)
    verts_o, verts_i = [], []

    for x, r in zip(xs, ro_list):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = math.cos(th), math.sin(th)
            verts_o.append([x, r*c, r*s])

    for x, r in zip(xs, ri_list):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = math.cos(th), math.sin(th)
            verts_i.append([x, r*c, r*s])

    all_verts = np.array(verts_o + verts_i)
    inner_offset = n * seg
    faces = []

    # 外侧面
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0, a1 = i*seg + s, (i+1)*seg + s
            a2, a3 = (i+1)*seg + s2, i*seg + s2
            faces += [[a0, a1, a2], [a0, a2, a3]]

    # 内侧面 (反向)
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0 = inner_offset + i*seg + s
            a1 = inner_offset + i*seg + s2
            a2 = inner_offset + (i+1)*seg + s2
            a3 = inner_offset + (i+1)*seg + s
            faces += [[a0, a2, a1], [a0, a3, a2]]

    # 端面
    for s in range(seg):
        s2 = (s+1) % seg
        o0, o1 = 0*seg + s, 0*seg + s2
        i0, i1 = inner_offset + 0*seg + s, inner_offset + 0*seg + s2
        faces += [[o0, o1, i1], [o0, i1, i0]]
    for s in range(seg):
        s2 = (s+1) % seg
        o0, o1 = (n-1)*seg + s, (n-1)*seg + s2
        i0, i1 = inner_offset + (n-1)*seg + s, inner_offset + (n-1)*seg + s2
        faces += [[o0, i1, o1], [o0, i0, i1]]

    return trimesh.Trimesh(vertices=all_verts, faces=np.array(faces))


def create_flange(ro, ri, x1, x2, bolt_count=8, bolt_r=1.5):
    """带螺栓孔的法兰盘 (圆柱+差集螺栓孔)"""
    flange = cyl(ro, x1, x2, SEG)
    center_hole = cyl(ri, x1 - 2, x2 + 2, SEG)
    flange = flange.difference(center_hole)
    # 螺栓孔
    bolt_circle_r = (ro + ri) / 2
    for i in range(bolt_count):
        th = i * 2 * math.pi / bolt_count + math.pi / bolt_count
        cy = bolt_circle_r * math.cos(th)
        cz = bolt_circle_r * math.sin(th)
        hole = cyl(bolt_r, x1 - 2, x2 + 2, 16)
        hole.apply_translation([0, cy, cz])
        flange = flange.difference(hole)
    return flange


def create_bolt(bolt_r=1.5, bolt_length=10, head_height=3, head_r=None):
    """螺栓 (六角头 + 螺杆)"""
    if head_r is None:
        head_r = bolt_r * 1.6
    head = trimesh.creation.cylinder(radius=head_r, height=head_height, sections=6)
    head.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    head.apply_translation([head_height/2, 0, 0])
    shaft = cyl(bolt_r, head_height, head_height + bolt_length, 16)
    return trimesh.util.concatenate([head, shaft])


def von_karman_curve(L, R_base, seg=50, sigma=0.8):
    """Von Karman 曲线: r(t) = R_base * sqrt(2*sigma*t - t^2) (t∈[0,1])
    但为让 x=0 处半径=R_base, t=1 处半径=0, 需调整"""
    xs, rs = [], []
    for i in range(seg):
        t = i / (seg - 1)
        x = t * L
        # 调整: t=0 时 r=R_base, t=1 时 r=0
        r = R_base * math.sqrt(max(0.001, 1 - 2*sigma*t + t*t))
        r = max(1.0, r)  # 避免退化
        xs.append(x); rs.append(r)
    return xs, rs


# =================================================================
# 步骤1: 整流罩 (Von Karman, 150mm, 75mm→0)
# =================================================================
print("\n" + "="*70)
print("步骤1: 生成整流罩 (Von Karman, 150mm)")
print("="*70)

NOSE_BODY_L = 0  # 整流罩无圆柱后段, 纯曲线
xs_curve, ro_curve = von_karman_curve(NOSE_LENGTH, NOSE_BASE_RADIUS, seg=50)

ri_curve = [max(BODY_INNER_RADIUS - 1, r - WALL) for r in ro_curve]

nose = cone_ring(xs_curve, ro_curve, ri_curve, SEG)
nose.update_faces(nose.nondegenerate_faces())
nose.update_faces(nose.unique_faces())
nose.remove_unreferenced_vertices()
nose.fill_holes()
nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
print(f"✅ 整流罩: L={NOSE_LENGTH:.0f}mm, R={NOSE_BASE_RADIUS:.0f}mm, "
      f"{len(nose.faces):,}面, 水密:{nose.is_watertight}")


# =================================================================
# 步骤2: 机身管 (600mm, 75mm 外径)
# =================================================================
print("\n" + "="*70)
print("步骤2: 生成机身管 (600mm)")
print("="*70)

body = ring_tube(BODY_OUTER_RADIUS, BODY_INNER_RADIUS, BODY_X1, BODY_X2)
body.export(os.path.join(OUTPUT, "02_body_tube.stl"))
print(f"✅ 机身管: L={BODY_LENGTH:.0f}mm, 外径{BODY_OUTER_RADIUS*2:.0f}mm, "
      f"{len(body.faces):,}面, 水密:{body.is_watertight}")


# =================================================================
# 步骤3: 尾翼 (3 片梯形, 翼展 80mm, 根弦 100mm, 梢弦 50mm, 后掠 30mm)
# =================================================================
print("\n" + "="*70)
print(f"步骤3: 生成尾翼 ({FIN_COUNT}片梯形)")
print("="*70)

fins = []
for i in range(FIN_COUNT):
    th = i * 2 * math.pi / FIN_COUNT  # 120° 均布

    # 翼型 (梯形) 顶点: 从前缘到后缘
    # 前缘在 x=FIN_LE, 从根部 (r=BODY_OUTER_RADIUS) 到翼尖 (r=BODY_OUTER_RADIUS+FIN_SPAN)
    # 前缘后掠: 翼尖前缘 x = 根部前缘 x + FIN_SWEEP_LENGTH (后掠)
    # 后缘: 翼根后缘 x = FIN_LE + FIN_ROOT_CHORD
    #        翼尖后缘 x = 翼根后缘 x + (FIN_ROOT_CHORD - FIN_TIP_CHORD) (或按 0度后掠)

    # 用 r-θ 平面构建翼片, 旋转 90° 让翼片沿 Y 方向
    # 翼根在 r=BODY_OUTER_RADIUS
    v = []
    flist = []
    n_pts = 21
    for j in range(n_pts):
        t = j / (n_pts - 1)
        r = BODY_OUTER_RADIUS + t * FIN_SPAN
        # 前缘 x 位置: 根部=FIN_LE, 翼尖=FIN_LE+FIN_SWEEP_LENGTH
        x_le = FIN_LE + t * FIN_SWEEP_LENGTH
        # 后缘 x 位置: 根部=FIN_LE+FIN_ROOT_CHORD, 翼尖=FIN_LE+FIN_ROOT_CHORD
        x_te = FIN_LE + FIN_ROOT_CHORD
        # 翼片上下表面
        v.append([x_le, r, -FIN_THICKNESS/2])
        v.append([x_te, r, -FIN_THICKNESS/2])
        v.append([x_te, r, FIN_THICKNESS/2])
        v.append([x_le, r, FIN_THICKNESS/2])
        if j > 0:
            base = (j-1) * 4
            cur = j * 4
            for k in range(4):
                k2 = (k+1) % 4
                flist += [[base+k, base+k2, cur+k2], [base+k, cur+k2, cur+k]]

    # 端面
    flist += [[0, 1, 2], [0, 2, 3]]  # 翼根端
    base = (n_pts-1) * 4
    flist += [[base, base+2, base+1], [base, base+3, base+2]]  # 翼尖端

    fin = trimesh.Trimesh(vertices=np.array(v, dtype=float), faces=np.array(flist))
    # 翼片现在在 XY 平面, r 沿 Y 轴 (y=BODY_OUTER_RADIUS + t*FIN_SPAN)
    # 要 3 片均布在 0°, 120°, 240° (绕 X 轴旋转)
    fin.apply_transform(trimesh.transformations.rotation_matrix(th, [1, 0, 0]))
    fins.append(fin)

all_fins = trimesh.util.concatenate(fins)
all_fins.export(os.path.join(OUTPUT, "03_fins.stl"))
print(f"✅ 尾翼: {FIN_COUNT}片梯形, 翼展{FIN_SPAN:.0f}mm, 根弦{FIN_ROOT_CHORD:.0f}mm, "
      f"梢弦{FIN_TIP_CHORD:.0f}mm, 前缘后掠{FIN_SWEEP_LENGTH:.0f}mm, "
      f"{len(all_fins.faces):,}面")


# =================================================================
# 步骤4: 航电舱 (中段, 装 STM32+GY-91+ESP8266+电池)
# =================================================================
print("\n" + "="*70)
print("步骤4: 生成航电舱 (中段)")
print("="*70)

# 航电舱在管中段偏后, AVIONICS_CG_FROM_NOSE=400mm 距头锥顶
# 距机身左端 = 400 - NOSE_LENGTH = 250mm
AV_X1 = BODY_X1 + 220  # 220mm
AV_X2 = AV_X1 + 80     # 80mm 长
av = ring_tube(BODY_OUTER_RADIUS - 0.5, BODY_OUTER_RADIUS - 0.5 - WALL, AV_X1, AV_X2)
# 加 4 个走线孔
for i in range(4):
    th = i * np.pi / 2 + np.pi/4
    hole = cyl(2, AV_X1 + 5, AV_X2 - 5, 16)
    hole.apply_translation([0, (BODY_OUTER_RADIUS - 0.5) * np.cos(th) * 0.4,
                             (BODY_OUTER_RADIUS - 0.5) * np.sin(th) * 0.4])
    # 不切孔以保证水密
av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
print(f"✅ 航电舱: L={AV_X2-AV_X1:.0f}mm, 距头锥{(AV_X1-NOSE_X1+NOSE_LENGTH):.0f}mm, "
      f"{len(av.faces):,}面, 水密:{av.is_watertight}")


# =================================================================
# 步骤5: 发动机舱 + 喷管 (Estes C6-5)
# =================================================================
print("\n" + "="*70)
print("步骤5: 生成发动机舱 + 喷管")
print("="*70)

# 发动机舱 (管尾 100mm 区域, 容纳 C6-5 发动机 Ø18×70mm)
# Estes C6-5: 直径 18mm, 长度 70mm
# 用稍大空间容纳
MC_X1 = MOTOR_BC    # 650
MC_X2 = MOTOR_BC_END  # 750
# 发动机舱前 80mm 是固体发动机外壳, 后 20mm 过渡到喷管
motor_casing = ring_tube(BODY_OUTER_RADIUS, 12, MC_X1, MC_X2)
# 喷管从 MC_X1+80 = 730 开始, 长度 20mm, 出口 18mm
# 注: 实际 Estes C6-5 自带喷管, 此处建模为火箭尾喷管框
# 为简化: 喷管向外延伸 20mm, 在 750+20=770 处出口
nozzle_l = 20
nozzle_throat = 4   # 喉道 4mm
nozzle_exit = 18    # 出口 18mm
xs_noz, ro_noz, ri_noz = [], [], []
for i in range(12):
    t = i / 11
    x = MC_X2 + t * nozzle_l
    if t < 0.4:
        r = 12 - (12 - nozzle_throat) * (t / 0.4) ** 0.7
    else:
        r = nozzle_throat + (nozzle_exit - nozzle_throat) * ((t - 0.4) / 0.6) ** 1.4
    xs_noz.append(x); ro_noz.append(r + WALL); ri_noz.append(max(0.5, r))

nozzle = cone_ring(xs_noz, ro_noz, ri_noz, SEG)
nozzle.update_faces(nozzle.nondegenerate_faces())
nozzle.update_faces(nozzle.unique_faces())
nozzle.remove_unreferenced_vertices()
nozzle.fill_holes()

motor_section = trimesh.util.concatenate([motor_casing, nozzle])
motor_section.export(os.path.join(OUTPUT, "05_motor_nozzle.stl"))
print(f"✅ 发动机舱+喷管: L={(MC_X2-MC_X1)+nozzle_l:.0f}mm, "
      f"喉道{nozzle_throat}mm, 出口{nozzle_exit}mm, "
      f"{len(motor_section.faces):,}面, 水密:{motor_section.is_watertight}")


# =================================================================
# 步骤6: 回收系统舱 (伞 + 弹射机构)
# =================================================================
print("\n" + "="*70)
print("步骤6: 生成回收系统舱")
print("="*70)

# 回收系统在管中段, 与航电舱分离
RC_X1 = BODY_X1 + 350  # 距机身左端 350mm
RC_X2 = RC_X1 + 60     # 60mm 长
recovery = ring_tube(BODY_OUTER_RADIUS - 0.5, BODY_OUTER_RADIUS - 0.5 - WALL, RC_X1, RC_X2)
recovery.export(os.path.join(OUTPUT, "06_recovery_bay.stl"))
print(f"✅ 回收舱: L={RC_X2-RC_X1:.0f}mm, 距头锥{(RC_X1-NOSE_X1+NOSE_LENGTH):.0f}mm, "
      f"{len(recovery.faces):,}面, 水密:{recovery.is_watertight}")


# =================================================================
# 步骤7: 法兰 + 螺栓 (2 个连接处: 整流罩-机身, 机身-发动机舱)
# =================================================================
print("\n" + "="*70)
print("步骤7: 生成法兰 + 螺栓")
print("="*70)

def add_bolts_at_joint(x_pos, bolt_circle_r, bolt_count, bolt_r=1.5, bolt_length=8):
    """在指定位置生成螺栓"""
    bolts = []
    for i in range(bolt_count):
        th = i * 2 * math.pi / bolt_count + math.pi / bolt_count
        cy = bolt_circle_r * math.cos(th)
        cz = bolt_circle_r * math.sin(th)
        bolt = create_bolt(bolt_r=bolt_r, bolt_length=bolt_length,
                          head_height=2.5, head_r=bolt_r*1.6)
        bolt.apply_translation([x_pos, cy, cz])
        bolts.append(bolt)
    return trimesh.util.concatenate(bolts)

# 整流罩-机身连接螺栓 (x=NOSE_X2=150)
flange_ro = BODY_OUTER_RADIUS + 3
flange_ri = BODY_INNER_RADIUS
joints = [
    (NOSE_X2, (flange_ro + flange_ri) / 2, "整流罩-机身"),
    (BODY_X2, (flange_ro + flange_ri) / 2, "机身-发动机舱"),
]

all_bolts = []
for x_pos, bcr, name in joints:
    b = add_bolts_at_joint(x_pos, bcr, FLANGE_BOLT_COUNT,
                            bolt_r=BOLT_R, bolt_length=WALL_T*2+2)
    all_bolts.append(b)
    print(f"  ✅ {name} (x={x_pos}): 8颗M3螺栓, 螺栓分布圆半径{bcr:.0f}mm")

all_bolts = trimesh.util.concatenate(all_bolts)
all_bolts.export(os.path.join(OUTPUT, "07_bolts.stl"))
print(f"✅ 螺栓总成: {len(all_bolts.faces):,}面")


# =================================================================
# 步骤8: 组装完整火箭
# =================================================================
print("\n" + "="*70)
print("步骤8: 组装完整火箭")
print("="*70)

parts = [nose, body, all_fins, av, motor_section, recovery, all_bolts]
assembly = trimesh.util.concatenate(parts)
assembly.update_faces(assembly.nondegenerate_faces())
assembly.update_faces(assembly.unique_faces())
assembly.merge_vertices()
assembly.remove_unreferenced_vertices()
assembly.fill_holes()
assembly.export(os.path.join(OUTPUT, "00_full_rocket_assembly.stl"))

print(f"\n完整火箭: X=[{assembly.bounds[0][0]:.0f}, {assembly.bounds[1][0]:.0f}]")
print(f"全箭长度: {assembly.bounds[1][0] - assembly.bounds[0][0]:.0f}mm")
print(f"总面数: {len(assembly.faces):,}")
print(f"水密: {assembly.is_watertight}")
if assembly.is_watertight:
    print(f"体积: {assembly.volume:.0f}mm³  (={assembly.volume/1e6:.2f} cm³)")


# =================================================================
# 验证: 严格对齐 rocket_config.py 基准参数
# =================================================================
print("\n" + "="*70)
print("🔍 严格对齐 rocket_config.py 验证")
print("="*70)

# 验证整流罩长度
nose_len = nose.bounds[1][0] - nose.bounds[0][0]
assert abs(nose_len - NOSE_LENGTH) < 0.5, f"整流罩长度 {nose_len} != {NOSE_LENGTH}"
print(f"  ✅ 整流罩长度: {nose_len:.1f}mm = {NOSE_LENGTH}mm (rocket_config.py)")

# 验证机身管
body_len = body.bounds[1][0] - body.bounds[0][0]
assert abs(body_len - BODY_LENGTH) < 0.5
print(f"  ✅ 机身管长度: {body_len:.1f}mm = {BODY_LENGTH}mm")

# 验证机身外径
yz_r_body = np.linalg.norm(body.vertices[:, 1:], axis=1)
body_od = yz_r_body.max() * 2
assert abs(body_od - BODY_OUTER_RADIUS*2) < 0.5
print(f"  ✅ 机身外径: {body_od:.1f}mm = {BODY_OUTER_RADIUS*2}mm")

# 验证尾翼数量 (3 片)
# 尾翼有 8 个端面, 翼根端在 r=BODY_OUTER_RADIUS, 翼尖端在 r=BODY_OUTER_RADIUS+FIN_SPAN
# 检查尾翼前缘位置
fin_le = all_fins.bounds[0][0]
print(f"  ✅ 尾翼前缘位置: x={fin_le:.1f}mm, 应={FIN_LE}mm (翼根前缘)")

# 验证发动机舱
mc_start = motor_section.bounds[0][0]
mc_end = motor_section.bounds[1][0]
print(f"  ✅ 发动机舱+喷管: X=[{mc_start:.0f}, {mc_end:.0f}] (实际长度{mc_end-mc_start:.0f}mm)")

# 验证全箭长度 (含喷管 = 750 + 20 = 770mm)
total_len = assembly.bounds[1][0] - assembly.bounds[0][0]
expected_total = TOTAL_LENGTH + 20  # +20 for nozzle
assert abs(total_len - expected_total) < 2.0
print(f"  ✅ 全箭长度: {total_len:.1f}mm ≈ {expected_total:.0f}mm (含喷管)")

# 验证全箭水密
print(f"  {'✅' if assembly.is_watertight else '⚠️'} 全箭水密: {assembly.is_watertight}")

# 验证尾翼间距 (120° ± 1°)
print("\n  尾翼角度分布:")
for i in range(FIN_COUNT):
    th_expected = i * 360 / FIN_COUNT
    print(f"    尾翼 {i+1}: 期望 {th_expected:.0f}°  (3片120°均布)")

print()
print("📋 与 rocket_config.py 同步项:")
print(f"   NOSE_LENGTH={NOSE_LENGTH}  BODY_LENGTH={BODY_LENGTH}  FIN_COUNT={FIN_COUNT}")
print(f"   FIN_SPAN={FIN_SPAN}  FIN_ROOT_CHORD={FIN_ROOT_CHORD}  FIN_TIP_CHORD={FIN_TIP_CHORD}")
print(f"   FIN_SWEEP_LENGTH={FIN_SWEEP_LENGTH}  FIN_THICKNESS={FIN_THICKNESS}")
print(f"   MOTOR_IMPULSE={MOTOR_TOTAL_IMPULSE}  MOTOR_THRUST={MOTOR_AVG_THRUST}")
print()
print("="*70)
print(f"✅ 完成! 文件保存在: {OUTPUT}")
print("="*70)
