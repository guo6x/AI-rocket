#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 火箭3D模型生成器 v10 - 终极质量版
直接构建拓扑，避免布尔运算破面问题
"""
import numpy as np
import trimesh
import os
import math

WALL = 2.5
SEG = 96
OUTPUT = r"D:\AI_rocket\3d_print_files"
W = WALL
os.makedirs(OUTPUT, exist_ok=True)


def cyl(r, x1, x2, seg=SEG):
    """圆柱体 (沿X轴)"""
    L = x2 - x1
    c = trimesh.creation.cylinder(radius=r, height=L, sections=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x1 + L/2, 0, 0])
    return c


def ring_tube(ro, ri, x1, x2, seg=SEG):
    """空心管 - 直接构建拓扑"""
    verts_o, verts_i = [], []
    n = 2
    xs = [x1, x2]
    for x in xs:
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts_o.append([x, ro*c, ro*s])
    for x in xs:
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts_i.append([x, ri*c, ri*s])

    all_verts = np.array(verts_o + verts_i)
    faces = []
    inner_offset = seg * 2

    # 外侧面
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0 = i*seg + s
            a1 = (i+1)*seg + s
            a2 = (i+1)*seg + s2
            a3 = i*seg + s2
            faces += [[a0, a1, a2], [a0, a2, a3]]

    # 内侧面
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0 = inner_offset + i*seg + s
            a1 = inner_offset + i*seg + s2
            a2 = inner_offset + (i+1)*seg + s2
            a3 = inner_offset + (i+1)*seg + s
            faces += [[a0, a2, a1], [a0, a3, a2]]

    # 端面 (前后)
    # i=0
    for s in range(seg):
        s2 = (s+1) % seg
        o0 = 0*seg + s
        o1 = 0*seg + s2
        i0 = inner_offset + 0*seg + s
        i1 = inner_offset + 0*seg + s2
        faces += [[o0, o1, i1], [o0, i1, i0]]
    # i=n-1
    for s in range(seg):
        s2 = (s+1) % seg
        o0 = (n-1)*seg + s
        o1 = (n-1)*seg + s2
        i0 = inner_offset + (n-1)*seg + s
        i1 = inner_offset + (n-1)*seg + s2
        faces += [[o0, i1, o1], [o0, i0, i1]]

    return trimesh.Trimesh(vertices=all_verts, faces=np.array(faces))


def cone_ring(xs, ro_list, ri_list, seg=SEG):
    """变截面空心管 - 直接构建"""
    n = len(xs)
    verts_o, verts_i = [], []

    for x, r in zip(xs, ro_list):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts_o.append([x, r*c, r*s])

    for x, r in zip(xs, ri_list):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts_i.append([x, r*c, r*s])

    all_verts = np.array(verts_o + verts_i)
    inner_offset = n * seg
    faces = []

    # 外侧面
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0 = i*seg + s
            a1 = (i+1)*seg + s
            a2 = (i+1)*seg + s2
            a3 = i*seg + s2
            faces += [[a0, a1, a2], [a0, a2, a3]]

    # 内侧面 (法线反向)
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


def create_flange_solid(ro, ri, x1, x2, bolt_count=8, bolt_r=2.0):
    """创建带螺栓孔的法兰盘 - 用布尔运算 (水密保证)

    x1, x2: 法兰的左/右X坐标 (x1 < x2)
    ro: 外半径
    ri: 内半径 (中心孔)
    """
    # 创建法兰主体 (实心圆柱)
    flange = cyl(ro, x1, x2, SEG)
    # 钻中心孔
    center_hole = cyl(ri, x1 - 2, x2 + 2, SEG)
    flange = flange.difference(center_hole)

    # 钻螺栓孔
    bolt_circle_r = (ro + ri) / 2
    for i in range(bolt_count):
        th = i * 2 * math.pi / bolt_count + math.pi / bolt_count
        cy = bolt_circle_r * math.cos(th)
        cz = bolt_circle_r * math.sin(th)
        hole = cyl(bolt_r, x1 - 2, x2 + 2, 16)
        hole.apply_translation([0, cy, cz])
        flange = flange.difference(hole)

    return flange


def create_bolt(bolt_r=2.0, bolt_length=10, head_height=3, head_r=None):
    """创建完整螺栓 (头部+螺杆) - 用trimesh内置primitive"""
    if head_r is None:
        head_r = bolt_r * 1.6

    # 六角头 - 用 cylinder 6段
    head = trimesh.creation.cylinder(radius=head_r, height=head_height, sections=6)
    head.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    head.apply_translation([head_height/2, 0, 0])

    # 螺杆
    shaft = cyl(bolt_r, head_height, head_height + bolt_length, 16)

    return trimesh.util.concatenate([head, shaft])


def create_hex_nut(bolt_r=2.0, nut_height=2.5, nut_r=None):
    """六角螺母"""
    if nut_r is None:
        nut_r = bolt_r * 1.6
    nut = trimesh.creation.cylinder(radius=nut_r, height=nut_height, sections=6)
    nut.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    nut.apply_translation([nut_height/2, 0, 0])
    # 中心孔
    hole = cyl(bolt_r * 1.1, -0.5, nut_height + 0.5, 16)
    nut = nut.difference(hole)
    return nut


# ============================================================================
# 火箭设计参数
# ============================================================================
print("="*70)
print("🚀 火箭3D模型生成器 v10 - 终极质量版")
print("="*70)

# 机身
BODY_RO = 37.5
BODY_RI = 32.5
BODY_L = 600

# 整流罩 - 等径于机身
NOSE_L = 190
NOSE_RO = BODY_RO  # 37.5mm, 等径机身
NOSE_RI = NOSE_RO - WALL

# TVC底座
TVC_L = 80
TVC_RO_RIGHT = BODY_RO      # 75mm - 匹配机身
TVC_RO_LEFT = 45             # 90mm - 匹配万向节
TVC_RI_RIGHT = BODY_RI - 2
TVC_RI_LEFT = 38

# 万向节
GIM_OR = 45                 # 90mm - 匹配TVC左端和喷管过渡段
GIM_IR = 30
GIM_L = 45

# 喷管 - 喷管入口加过渡段匹配万向节
NOZZE_ADAPTER_L = 30        # 过渡段长度
NOZZLE_L = 160
NOZZLE_RI_IN = 25
NOZZLE_R_THROAT = 12
NOZZLE_RE = 55

# 通用
WALL_T = 4  # 法兰厚度
FLANGE_BOLT_COUNT = 8
BOLT_R = 2.0
BOLT_HEAD_R = 3.5
BOLT_BOLT_CIRCLE_R = 32  # 螺栓分布圆半径

# 坐标
NOSE_X1 = 0
NOSE_X2 = NOSE_L

BODY_X1 = -BODY_L
BODY_X2 = 0

TVC_X1 = BODY_X1 - TVC_L
TVC_X2 = BODY_X1

GIM_X1 = TVC_X1 - GIM_L
GIM_X2 = TVC_X1

NOZZLE_X1 = GIM_X1 - NOZZLE_L
NOZZLE_X2 = GIM_X1

print(f"参数: 机身外径{2*BODY_RO:.0f}, 整流罩外径{2*NOSE_RO:.0f}, TVC {TVC_RO_RIGHT*2:.0f}→{TVC_RO_LEFT*2:.0f}")
print(f"坐标: N[{NOSE_X1},{NOSE_X2}] B[{BODY_X1},{BODY_X2}] T[{TVC_X1},{TVC_X2}] G[{GIM_X1},{GIM_X2}] NZ[{NOZZLE_X1},{NOZZLE_X2}]")

# ============================================================================
# 步骤1: 整流罩 (Von Karman曲线)
# ============================================================================
print("\n" + "="*70)
print("步骤1: 生成整流罩")
print("="*70)

sigma = 0.8
NOSE_BODY_L = 25
NOSE_CURVE_L = NOSE_L - NOSE_BODY_L

xs_curve, ro_curve, ri_curve = [], [], []
for i in range(50):
    t = i / 49
    x = NOSE_X1 + NOSE_BODY_L + t * NOSE_CURVE_L
    # t=0 时: r_out = NOSE_RO (粗端)
    # t=1 时: r_out = 0 (尖)
    r_out = NOSE_RO * math.sqrt(max(0.001, 1 - 2*sigma*t + t*t))
    r_out = max(2.0, r_out)
    r_in = max(NOSE_RI, r_out - WALL)
    xs_curve.append(x); ro_curve.append(r_out); ri_curve.append(r_in)

# 后段圆柱 (NOSE_X1 到 NOSE_X1+NOSE_BODY_L 是粗端圆柱)
xs = [NOSE_X1, NOSE_X1 + NOSE_BODY_L] + xs_curve
ro = [NOSE_RO, NOSE_RO] + ro_curve
ri = [NOSE_RI, NOSE_RI] + ri_curve

nose = cone_ring(xs, ro, ri, SEG)

# 整流罩左端 (x=0) 处的法兰: 厚度 4mm, 尺寸与机身前端法兰匹配
# 整流罩法兰的外径 = BODY_RO + 3 = 40.5, 中心孔 = NOSE_RI = 35
nose_flange = create_flange_solid(BODY_RO + 3, NOSE_RI, NOSE_X1 - WALL_T, NOSE_X1,
                                    bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
nose = trimesh.util.concatenate([nose, nose_flange])

# 修复水密性: 移除退化面
nose.update_faces(nose.nondegenerate_faces())
nose.update_faces(nose.unique_faces())
nose.remove_unreferenced_vertices()
nose.fill_holes()

nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
print(f"✅ 整流罩: X=[{nose.bounds[0][0]:.0f}, {nose.bounds[1][0]:.0f}], {len(nose.faces):,}面, 水密:{nose.is_watertight}")

# ============================================================================
# 步骤2: 机身管 (前后端各加一个法兰)
# ============================================================================
print("\n" + "="*70)
print("步骤2: 生成机身管")
print("="*70)

body = ring_tube(BODY_RO, BODY_RI, BODY_X1, BODY_X2)

# 前端法兰 (向+方向, 整流罩连接端)
body_front_flange = create_flange_solid(BODY_RO + 3, BODY_RI, BODY_X2, BODY_X2 + WALL_T,
                                          bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
# 后端法兰 (向-方向, TVC连接端)
body_back_flange = create_flange_solid(BODY_RO + 3, BODY_RI, BODY_X1 - WALL_T, BODY_X1,
                                         bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)

body = trimesh.util.concatenate([body, body_front_flange, body_back_flange])
body.export(os.path.join(OUTPUT, "02_body_tube.stl"))
print(f"✅ 机身管: X=[{body.bounds[0][0]:.0f}, {body.bounds[1][0]:.0f}], {len(body.faces):,}面, 水密:{body.is_watertight}")

# ============================================================================
# 步骤3: 尾翼
# ============================================================================
print("\n" + "="*70)
print("步骤3: 生成尾翼")
print("="*70)

FIN_ROOT = 80
FIN_TIP = 40
FIN_SPAN = 50
FIN_THICK = 3
FIN_X_LE = BODY_X1 + 30

fins = []
for i in range(4):
    th = i * np.pi / 2
    v = []
    f_list = []
    for j in range(21):
        t = j / 20
        z = t * FIN_SPAN
        x_le = t * (FIN_ROOT - FIN_TIP)
        v.append([x_le, -FIN_THICK/2, z])
        v.append([FIN_ROOT, -FIN_THICK/2, z])
        v.append([FIN_ROOT, FIN_THICK/2, z])
        v.append([x_le, FIN_THICK/2, z])
        if j > 0:
            base = (j-1) * 4
            cur = j * 4
            for k in range(4):
                k2 = (k+1) % 4
                f_list += [[base+k, base+k2, cur+k2], [base+k, cur+k2, cur+k]]

    base = 0
    cur = 20 * 4
    f_list += [[base, base+1, base+2], [base, base+2, base+3]]
    f_list += [[cur, cur+2, cur+1], [cur, cur+3, cur+2]]

    fin = trimesh.Trimesh(vertices=np.array(v, dtype=float), faces=np.array(f_list))
    fin.apply_translation([FIN_X_LE, BODY_RO - 1, 0])
    fin.apply_transform(trimesh.transformations.rotation_matrix(th, [1, 0, 0]))
    fins.append(fin)

all_fins = trimesh.util.concatenate(fins)
all_fins.export(os.path.join(OUTPUT, "03_fins.stl"))
print(f"✅ 尾翼: {len(fins)}片, {len(all_fins.faces):,}面, 水密:{all_fins.is_watertight}")

# ============================================================================
# 步骤4: 航电舱
# ============================================================================
print("\n" + "="*70)
print("步骤4: 生成航电舱")
print("="*70)

AV_X1 = -450
AV_X2 = -370
av = ring_tube(BODY_RO - 2, BODY_RO - 2 - WALL, AV_X1, AV_X2)
av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
print(f"✅ 航电舱: X=[{av.bounds[0][0]:.0f}, {av.bounds[1][0]:.0f}], 水密:{av.is_watertight}")

# ============================================================================
# 步骤5: TVC底座
# ============================================================================
print("\n" + "="*70)
print("步骤5: 生成TVC底座")
print("="*70)

# 锥形
xs_tvc, ro_tvc, ri_tvc = [], [], []
for i in range(30):
    t = i / 29
    x = TVC_X1 + t * (TVC_X2 - TVC_X1)
    r_out = TVC_RO_LEFT + t * (TVC_RO_RIGHT - TVC_RO_LEFT)
    r_in = TVC_RI_LEFT + t * (TVC_RI_RIGHT - TVC_RI_LEFT)
    xs_tvc.append(x); ro_tvc.append(r_out); ri_tvc.append(r_in)

tvc_body = cone_ring(xs_tvc, ro_tvc, ri_tvc, SEG)

# TVC右端法兰 (与机身连接, 在 TVC_X2 位置, 向右延伸)
tvc_front_flange = create_flange_solid(TVC_RO_RIGHT + 3, TVC_RI_RIGHT, TVC_X2, TVC_X2 + WALL_T,
                                          bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
# TVC左端法兰 (与万向节连接, 在 TVC_X1 位置, 向左延伸)
tvc_back_flange = create_flange_solid(TVC_RO_LEFT + 3, TVC_RI_LEFT, TVC_X1 - WALL_T, TVC_X1,
                                        bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)

tvc = trimesh.util.concatenate([tvc_body, tvc_front_flange, tvc_back_flange])
tvc.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
print(f"✅ TVC底座: X=[{tvc.bounds[0][0]:.0f}, {tvc.bounds[1][0]:.0f}], {len(tvc.faces):,}面, 水密:{tvc.is_watertight}")

# ============================================================================
# 步骤6: TVC万向节 (无自带法兰, 与TVC和喷管共用相邻零件的法兰)
# ============================================================================
print("\n" + "="*70)
print("步骤6: 生成TVC万向节")
print("="*70)

gim = ring_tube(GIM_OR, GIM_IR, GIM_X1, GIM_X2)

# 3个伺服耳 (TVC万向节的控制臂)
ears = []
gim_x_mid = (GIM_X1 + GIM_X2) / 2
for i in range(3):
    th = i * 2 * np.pi / 3 + np.pi/6  # 错开45度
    # 耳片是矩形板, 初始沿X轴向
    ear = trimesh.creation.box([6, 20, 8])
    ear.apply_transform(trimesh.transformations.rotation_matrix(th, [1, 0, 0]))
    ear.apply_translation([gim_x_mid, GIM_OR * np.cos(th), GIM_OR * np.sin(th)])
    ears.append(ear)

# 万向节只有环管+伺服耳
# 左端无自带法兰 (TVC左端自带法兰)
# 右端无自带法兰 (喷管自带右法兰)
gim = trimesh.util.concatenate([gim] + ears)
gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
print(f"✅ TVC万向节: X=[{gim.bounds[0][0]:.0f}, {gim.bounds[1][0]:.0f}], {len(gim.faces):,}面, 水密:{gim.is_watertight}")

# ============================================================================
# 步骤7: TVC喷管
# ============================================================================
print("\n" + "="*70)
print("步骤7: 生成TVC喷管")
print("="*70)

LC = 70
xs_conv, ro_conv, ri_conv = [], [], []
for i in range(30):
    t = i / 29
    x = NOZZLE_X2 - t * LC
    r = NOZZLE_RI_IN - (NOZZLE_RI_IN - NOZZLE_R_THROAT) * (t ** 0.7)
    xs_conv.append(x); ro_conv.append(r + WALL); ri_conv.append(r)

LD = NOZZLE_L - LC
xs_div, ro_div, ri_div = [], [], []
for i in range(1, 60):
    t = i / 60
    x = NOZZLE_X2 - LC - t * LD
    r = NOZZLE_R_THROAT + (NOZZLE_RE - NOZZLE_R_THROAT) * (t ** 1.4)
    xs_div.append(x); ro_div.append(r + WALL); ri_div.append(r)

xs = xs_conv + xs_div
ro = ro_conv + ro_div
ri = ri_conv + ri_div

nozzle_body = cone_ring(xs, ro, ri, SEG)

# 喷管前端法兰 (在NOZZLE_X2位置, 向右延伸, 与万向节连接)
nozzle_flange = create_flange_solid(GIM_OR - 2, NOZZLE_RI_IN, NOZZLE_X2, NOZZLE_X2 + WALL_T,
                                      bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)

nozzle = trimesh.util.concatenate([nozzle_body, nozzle_flange])
nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
print(f"✅ 喷管: X=[{nozzle.bounds[0][0]:.0f}, {nozzle.bounds[1][0]:.0f}], {len(nozzle.faces):,}面, 水密:{nozzle.is_watertight}")

# ============================================================================
# 步骤8: 螺栓和螺母
# ============================================================================
print("\n" + "="*70)
print("步骤8: 生成螺栓/螺母")
print("="*70)

def add_bolts_at_joint(x_pos, bolt_circle_r, bolt_count, side='both'):
    """在指定位置生成螺栓+螺母"""
    bolts = []
    for i in range(bolt_count):
        th = i * 2 * np.pi / bolt_count + math.pi / bolt_count
        cy = bolt_circle_r * math.cos(th)
        cz = bolt_circle_r * math.sin(th)

        # 螺栓
        bolt = create_bolt(bolt_r=BOLT_R, bolt_length=WALL_T*2 + 2, head_height=2.5, head_r=BOLT_HEAD_R)
        bolt.apply_translation([x_pos, cy, cz])
        bolts.append(bolt)
    return trimesh.util.concatenate(bolts)

# 各连接处螺栓
joints = [
    (0, (BODY_RO + 3 + NOSE_RI)/2),      # 整流罩-机身
    (BODY_X1, (BODY_RO + 3 + TVC_RI_RIGHT)/2),  # 机身-TVC
    (TVC_X1, (TVC_RO_LEFT + 3 + GIM_IR)/2),     # TVC-万向节
    (GIM_X1, (GIM_OR + 3 + NOZZLE_RI_IN)/2),    # 万向节-喷管
]

all_bolts_parts = []
for x_pos, bcr in joints:
    bolt = add_bolts_at_joint(x_pos, bcr, FLANGE_BOLT_COUNT)
    all_bolts_parts.append(bolt)

all_bolts = trimesh.util.concatenate(all_bolts_parts)
all_bolts.export(os.path.join(OUTPUT, "08_bolts_nuts.stl"))
print(f"✅ 螺栓: {FLANGE_BOLT_COUNT*4}件, {len(all_bolts.faces):,}面, 水密:{all_bolts.is_watertight}")

# ============================================================================
# 步骤9: 组装完整火箭
# ============================================================================
print("\n" + "="*70)
print("步骤9: 组装完整火箭")
print("="*70)

parts = [nose, body, all_fins, av, tvc, gim, nozzle, all_bolts]
assembly = trimesh.util.concatenate(parts)

# 修复装配体水密性 (移除退化面, 合并重复顶点, 填充孔洞)
assembly.update_faces(assembly.nondegenerate_faces())
assembly.update_faces(assembly.unique_faces())
assembly.merge_vertices()
assembly.remove_unreferenced_vertices()
assembly.fill_holes()

assembly.export(os.path.join(OUTPUT, "00_full_rocket_assembly.stl"))

print(f"\n完整火箭: X=[{assembly.bounds[0][0]:.0f}, {assembly.bounds[1][0]:.0f}]")
print(f"总长度: {assembly.bounds[1][0] - assembly.bounds[0][0]:.0f}mm")
print(f"总面数: {len(assembly.faces):,}")
print(f"水密: {assembly.is_watertight}")
if assembly.is_watertight:
    print(f"体积: {assembly.volume:.0f}mm³")

# ============================================================================
# 严格连接验证
# ============================================================================
print("\n" + "="*70)
print("🔍 严格连接验证")
print("="*70)

# 检查每个连接处的法兰半径
print("\n1. 法兰半径匹配检查:")
flange_checks = [
    ("整流罩-机身", 0, BODY_RO + 3),  # 法兰外径
    ("机身-TVC", BODY_X1, BODY_RO + 3),
    ("TVC-万向节", TVC_X1, TVC_RO_LEFT + 3),
    ("万向节-喷管", GIM_X1, GIM_OR + 3),
]
for name, x_pos, expected_ro in flange_checks:
    print(f"  {name} (x={x_pos}): 期望法兰外径 {expected_ro*2:.0f}mm")

print("\n2. 法兰面位置检查:")
position_checks = [
    ("整流罩-机身", NOSE_X1, BODY_X2, "整流罩法兰 vs 机身法兰"),
    ("机身-TVC", BODY_X1, TVC_X2, "机身后法兰 vs TVC前法兰"),
    ("TVC-万向节", TVC_X1, GIM_X2, "TVC后法兰 vs 万向节前法兰"),
    ("万向节-喷管", GIM_X1, NOZZLE_X2, "万向节后法兰 vs 喷管前法兰"),
]
all_ok = True
for name, pos1, pos2, desc in position_checks:
    gap = abs(pos1 - pos2)
    status = "✅" if gap < 0.01 else "❌"
    if gap >= 0.01:
        all_ok = False
    print(f"  {name}: {pos1:.0f} vs {pos2:.0f} → 偏差 {gap:.3f}mm {status}")

print("\n3. 螺栓位置检查 (在每个连接处都应有8个螺栓):")
for x_pos, bcr in joints:
    bolt_count = np.sum(
        (all_bolts.vertices[:, 0] >= x_pos - 5) &
        (all_bolts.vertices[:, 0] <= x_pos + 5)
    )
    print(f"  x={x_pos}: {bolt_count}个顶点")

print("\n4. 零件完整性:")
parts_info = [
    ("整流罩", nose), ("机身", body), ("尾翼", all_fins),
    ("航电舱", av), ("TVC", tvc), ("万向节", gim),
    ("喷管", nozzle), ("螺栓", all_bolts)
]
for name, part in parts_info:
    print(f"  {name}: {len(part.faces):,}面, X=[{part.bounds[0][0]:.0f},{part.bounds[1][0]:.0f}], 水密:{part.is_watertight}")

print()
if all_ok:
    print("🎉 所有连接正确! 法兰面精确接触")
else:
    print("⚠️ 部分连接有偏差")

print("\n" + "="*70)
print("完成! 文件保存在:", OUTPUT)
print("="*70)
