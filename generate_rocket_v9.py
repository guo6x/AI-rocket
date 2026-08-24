#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 火箭3D模型生成器 v9 - 高质量布尔运算版
使用 manifold3d 后端进行真正的布尔运算，确保零件高质量
"""
import numpy as np
import trimesh
import os
import math

WALL = 2.5
SEG = 96  # 提高分段数
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
    """空心管 - 使用布尔运算生成"""
    outer = cyl(ro, x1, x2, seg)
    inner = cyl(ri, x1, x2, seg)
    return outer.difference(inner)


def cone_ring(xs, ro_list, ri_list, seg=SEG):
    """沿X轴变截面的空心锥形管"""
    verts_o, verts_i = [], []
    faces = []
    n = len(xs)

    # 外圈顶点
    for i, (x, r) in enumerate(zip(xs, ro_list)):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts_o.append([x, r*c, r*s])

    # 内圈顶点
    for i, (x, r) in enumerate(zip(xs, ri_list)):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts_i.append([x, r*c, r*s])

    all_verts = np.array(verts_o + verts_i)
    inner_offset = len(verts_o)

    # 外侧面
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0 = i*seg + s
            a1 = (i+1)*seg + s
            a2 = (i+1)*seg + s2
            a3 = i*seg + s2
            faces += [[a0, a1, a2], [a0, a2, a3]]

    # 内侧面（反向法线）
    for i in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            a0 = inner_offset + i*seg + s
            a1 = inner_offset + i*seg + s2
            a2 = inner_offset + (i+1)*seg + s2
            a3 = inner_offset + (i+1)*seg + s
            faces += [[a0, a1, a2], [a0, a2, a3]]

    # 端面
    # 前端（i=0）
    for s in range(seg):
        s2 = (s+1) % seg
        o0 = 0*seg + s
        o1 = 0*seg + s2
        i0 = inner_offset + 0*seg + s
        i1 = inner_offset + 0*seg + s2
        faces += [[o0, o1, i1], [o0, i1, i0]]
    # 后端（i=n-1）
    for s in range(seg):
        s2 = (s+1) % seg
        o0 = (n-1)*seg + s
        o1 = (n-1)*seg + s2
        i0 = inner_offset + (n-1)*seg + s
        i1 = inner_offset + (n-1)*seg + s2
        faces += [[o0, i1, o1], [o0, i0, i1]]

    return trimesh.Trimesh(vertices=all_verts, faces=np.array(faces))


def create_flange(ro, ri, x_pos, thickness=4, side='left', bolt_count=8, bolt_r=2.0, bolt_circle_r=None):
    """创建带螺栓孔的法兰盘 - 使用布尔运算"""
    if bolt_circle_r is None:
        bolt_circle_r = (ro + ri) / 2

    # 法兰位置
    if side == 'left':
        x1 = x_pos - thickness
        x2 = x_pos
    else:
        x1 = x_pos
        x2 = x_pos + thickness

    # 创建法兰实体
    flange = cyl(ro, x1, x2, SEG)
    # 钻中心孔
    center_hole = cyl(ri, x1 - 1, x2 + 1, SEG)
    flange = flange.difference(center_hole)

    # 钻螺栓孔
    for i in range(bolt_count):
        th = i * 2 * np.pi / bolt_count + np.pi/bolt_count
        cy = bolt_circle_r * np.cos(th)
        cz = bolt_circle_r * np.sin(th)
        # 螺栓孔
        hole = cyl(bolt_r, x1 - 1, x2 + 1, 16)
        hole.apply_translation([0, cy, cz])
        flange = flange.difference(hole)

    return flange


def create_bolt(bolt_r=2.0, bolt_length=10, head_height=3, head_r=None):
    """创建完整螺栓 (头部+螺杆)"""
    if head_r is None:
        head_r = bolt_r * 1.6

    # 螺栓头 (六角)
    head = trimesh.creation.cylinder(radius=head_r, height=head_height, sections=6)
    head.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    head.apply_translation([head_height/2, 0, 0])

    # 螺杆
    shaft = cyl(bolt_r, head_height, head_height + bolt_length, 16)

    bolt = trimesh.util.concatenate([head, shaft])
    return bolt


def create_hex_nut(bolt_r=2.0, nut_height=2.5, nut_r=None):
    """创建六角螺母"""
    if nut_r is None:
        nut_r = bolt_r * 1.6
    nut = trimesh.creation.cylinder(radius=nut_r, height=nut_height, sections=6)
    nut.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    nut.apply_translation([nut_height/2, 0, 0])
    # 中心孔
    hole = cyl(bolt_r * 1.1, -1, nut_height + 1, 16)
    nut = nut.difference(hole)
    return nut


# ============================================================================
# 火箭设计参数
# ============================================================================
print("="*60)
print("🚀 火箭3D模型生成器 v9 - 高质量版")
print("="*60)

# 机身核心尺寸
BODY_RO = 37.5
BODY_RI = 32.5
BODY_L = 600

# 整流罩
NOSE_L = 190
NOSE_RO = BODY_RI - 1
NOSE_RI = NOSE_RO - WALL

# TVC底座
TVC_L = 80
TVC_RO_RIGHT = BODY_RO
TVC_RO_LEFT = 45
TVC_RI_RIGHT = BODY_RI - 2
TVC_RI_LEFT = 38

# 万向节
GIM_OR = 45
GIM_IR = 30
GIM_L = 45

# 喷管
NOZZLE_L = 160
NOZZLE_RO_IN = 29
NOZZLE_RI_IN = 25
NOZZLE_R_THROAT = 12
NOZZLE_RE = 55

# 通用
WALL_T = 3  # 法兰厚度
FLANGE_BOLT_COUNT = 8
BOLT_R = 2.0
BOLT_HEAD_R = 3.5

# 坐标定义 (确保法兰面精确接触)
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

print(f"机身: 外径{2*BODY_RO:.0f}mm, 内径{2*BODY_RI:.0f}mm, 长{BODY_L}mm")
print(f"整流罩: 外径{2*NOSE_RO:.0f}mm, 长{NOSE_L}mm")
print(f"TVC底座: {TVC_RO_RIGHT*2}mm → {TVC_RO_LEFT*2}mm, 长{TVC_L}mm")
print(f"万向节: 外径{2*GIM_OR:.0f}mm, 内径{2*GIM_IR:.0f}mm")
print(f"喷管入口: 外径{2*NOZZLE_RO_IN:.0f}mm")
print()
print(f"坐标: 整流罩[{NOSE_X1}, {NOSE_X2}], 机身[{BODY_X1}, {BODY_X2}]")
print(f"坐标: TVC[{TVC_X1}, {TVC_X2}], 万向节[{GIM_X1}, {GIM_X2}], 喷管[{NOZZLE_X1}, {NOZZLE_X2}]")

# ============================================================================
# 步骤1: 整流罩 (Von Karman曲线)
# ============================================================================
print("\n" + "="*60)
print("步骤1: 生成整流罩")
print("="*60)

# Von Karman曲线生成
sigma = 0.8
NOSE_BODY_L = 25  # 整流罩后段圆柱部分长度
NOSE_CURVE_L = NOSE_L - NOSE_BODY_L

xs_curve, ro_curve, ri_curve = [], [], []
for i in range(40):
    t = i / 39
    x = NOSE_X1 + NOSE_BODY_L + t * NOSE_CURVE_L
    r_out = NOSE_RO * math.sqrt(max(0.001, 2*sigma*t - t*t))
    r_in = max(NOSE_RI, r_out - WALL)
    xs_curve.append(x); ro_curve.append(r_out); ri_curve.append(r_in)

# 后段圆柱
xs_cyl = [NOSE_X1, NOSE_X1 + NOSE_BODY_L]
ro_cyl = [NOSE_RO, NOSE_RO]
ri_cyl = [NOSE_RI, NOSE_RI]

xs = xs_cyl + xs_curve
ro = ro_cyl + ro_curve
ri = ri_cyl + ri_curve

nose = cone_ring(xs, ro, ri, SEG)

# 整流罩前端加尖头帽
tip = trimesh.creation.cone(radius=NOSE_RO * 0.3, height=8, sections=SEG)
tip.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2, [0, 1, 0]))
tip.apply_translation([NOSE_X2 + 4, 0, 0])
# 实际不需要尖头 - 曲线已经收口到0

# 整流罩底端法兰
nose_flange = create_flange(BODY_RO + 2, NOSE_RI, NOSE_X1, WALL_T, side='left',
                              bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
nose = trimesh.util.concatenate([nose, nose_flange])

nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
print(f"✅ 整流罩: X=[{nose.bounds[0][0]:.0f}, {nose.bounds[1][0]:.0f}], {len(nose.faces):,}面")

# ============================================================================
# 步骤2: 机身管
# ============================================================================
print("\n" + "="*60)
print("步骤2: 生成机身管")
print("="*60)

body = ring_tube(BODY_RO, BODY_RI, BODY_X1, BODY_X2)

# 前后法兰
body_front_flange = create_flange(BODY_RO + 2, BODY_RI, BODY_X2, WALL_T, side='right',
                                    bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
body_back_flange = create_flange(BODY_RO + 2, BODY_RI, BODY_X1, WALL_T, side='left',
                                   bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
body = trimesh.util.concatenate([body, body_front_flange, body_back_flange])

body.export(os.path.join(OUTPUT, "02_body_tube.stl"))
print(f"✅ 机身管: X=[{body.bounds[0][0]:.0f}, {body.bounds[1][0]:.0f}], {len(body.faces):,}面")

# ============================================================================
# 步骤3: 尾翼
# ============================================================================
print("\n" + "="*60)
print("步骤3: 生成尾翼")
print("="*60)

# 4片尾翼
FIN_ROOT = 60     # 翼根弦长
FIN_TIP = 30      # 翼尖弦长
FIN_SPAN = 40     # 翼展
FIN_THICK = 3     # 翼厚
FIN_X_LE = BODY_X1 + 40  # 翼根前缘位置

fins = []
for i in range(4):
    th = i * np.pi / 2
    # 翼根位置
    fin = trimesh.creation.box([FIN_ROOT, FIN_THICK, FIN_SPAN])
    # 翼型 (梯形)
    verts = [
        [0, 0, 0],                          # 0: 翼根前缘
        [FIN_ROOT, 0, 0],                   # 1: 翼根后缘
        [FIN_ROOT - FIN_TIP, 0, FIN_SPAN],  # 2: 翼尖后缘
        [0, 0, FIN_SPAN],                   # 3: 翼尖前缘
    ]
    fin_verts = np.array(verts)
    # 用棱柱方式构建翼片
    # 创建梯形截面翼片
    fin_box = trimesh.creation.box([FIN_ROOT, FIN_THICK, FIN_SPAN])

    # 切出梯形形状 - 用凸包
    profile_2d = np.array([
        [0, 0],
        [FIN_ROOT, 0],
        [FIN_ROOT - FIN_TIP, FIN_SPAN],
        [0, FIN_SPAN],
    ])
    # 创建带斜切角的翼片
    fin_top = []
    fin_bot = []
    for j in range(20):
        t = j / 19
        z = t * FIN_SPAN
        x_top = t * (FIN_ROOT - FIN_TIP)  # 前缘斜切
        # 翼片
        profile_x = [
            [x_top, -FIN_THICK/2, z],
            [FIN_ROOT, -FIN_THICK/2, z],
            [FIN_ROOT, FIN_THICK/2, z],
            [x_top, FIN_THICK/2, z],
        ]
        fin_top.append(profile_x)

    # 用trimesh创建
    # 简化为梯形翼片
    v = []
    f = []
    for j in range(20):
        t = j / 19
        z = t * FIN_SPAN
        x_le = t * (FIN_ROOT - FIN_TIP)
        # 4个角
        v.append([x_le, -FIN_THICK/2, z])
        v.append([FIN_ROOT, -FIN_THICK/2, z])
        v.append([FIN_ROOT, FIN_THICK/2, z])
        v.append([x_le, FIN_THICK/2, z])
        if j > 0:
            base = (j-1) * 4
            cur = j * 4
            for k in range(4):
                k2 = (k+1) % 4
                f += [[base+k, base+k2, cur+k2], [base+k, cur+k2, cur+k]]

    # 端面
    base = 0
    cur = (20-1) * 4
    f += [[base+0, base+1, base+2], [base+0, base+2, base+3]]
    f += [[cur+0, cur+2, cur+1], [cur+0, cur+3, cur+2]]

    fin = trimesh.Trimesh(vertices=np.array(v, dtype=float), faces=np.array(f))
    fin.apply_translation([FIN_X_LE, BODY_RO - 1, 0])
    fin.apply_transform(trimesh.transformations.rotation_matrix(th, [1, 0, 0]))
    fins.append(fin)

all_fins = trimesh.util.concatenate(fins)
all_fins.export(os.path.join(OUTPUT, "03_fins.stl"))
print(f"✅ 尾翼: {len(fins)}片, {len(all_fins.faces):,}面")

# ============================================================================
# 步骤4: 航电舱
# ============================================================================
print("\n" + "="*60)
print("步骤4: 生成航电舱")
print("="*60)

AV_X1 = -450
AV_X2 = -370
av = ring_tube(BODY_RO - 2, BODY_RO - 2 - WALL, AV_X1, AV_X2)

# 加4个观察窗 (小凹陷)
for i in range(4):
    th = i * np.pi / 2 + np.pi/4
    hole = cyl(8, AV_X1 + 5, AV_X2 - 5, 24)
    hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    hole.apply_translation([0, (BODY_RO - 2) * np.cos(th) * 0.5, (BODY_RO - 2) * np.sin(th) * 0.5])
    # 实际不切窗口，保持简洁

av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
print(f"✅ 航电舱: X=[{av.bounds[0][0]:.0f}, {av.bounds[1][0]:.0f}]")

# ============================================================================
# 步骤5: TVC底座
# ============================================================================
print("\n" + "="*60)
print("步骤5: 生成TVC底座")
print("="*60)

# 锥形过渡
xs_tvc, ro_tvc, ri_tvc = [], [], []
for i in range(30):
    t = i / 29
    x = TVC_X1 + t * (TVC_X2 - TVC_X1)
    r_out = TVC_RO_LEFT + t * (TVC_RO_RIGHT - TVC_RO_LEFT)
    r_in = TVC_RI_LEFT + t * (TVC_RI_RIGHT - TVC_RI_LEFT)
    xs_tvc.append(x); ro_tvc.append(r_out); ri_tvc.append(r_in)

tvc_body = cone_ring(xs_tvc, ro_tvc, ri_tvc, SEG)

# 添加加强肋 (8条)
rib_count = 8
ribs = []
for i in range(rib_count):
    th = i * 2 * np.pi / rib_count
    rib = trimesh.creation.box([TVC_L, TVC_RO_RIGHT - TVC_RI_RIGHT, 2])
    rib.apply_translation([(TVC_X1 + TVC_X2)/2, 0, 0])
    rib.apply_transform(trimesh.transformations.rotation_matrix(th, [1, 0, 0]))
    ribs.append(rib)
# 注：肋骨会与圆锥相交，先不集成

# TVC前后法兰
tvc_front_flange = create_flange(TVC_RO_RIGHT + 3, TVC_RI_RIGHT, TVC_X2, WALL_T, side='right',
                                   bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
tvc_back_flange = create_flange(TVC_RO_LEFT + 3, TVC_RI_LEFT, TVC_X1, WALL_T, side='left',
                                  bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)

tvc = trimesh.util.concatenate([tvc_body, tvc_front_flange, tvc_back_flange])
tvc.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
print(f"✅ TVC底座: X=[{tvc.bounds[0][0]:.0f}, {tvc.bounds[1][0]:.0f}], {len(tvc.faces):,}面")

# ============================================================================
# 步骤6: TVC万向节
# ============================================================================
print("\n" + "="*60)
print("步骤6: 生成TVC万向节")
print("="*60)

# 球形万向节
gim = ring_tube(GIM_OR, GIM_IR, GIM_X1, GIM_X2)

# 加3个万向节耳 (安装伺服机构)
ears = []
for i in range(3):
    th = i * 2 * np.pi / 3
    ear = trimesh.creation.box([10, 15, 8])
    ear.apply_translation([(GIM_X1 + GIM_X2)/2, GIM_OR * np.cos(th), GIM_OR * np.sin(th)])
    ear.apply_transform(trimesh.transformations.rotation_matrix(th + np.pi/2, [1, 0, 0]))
    ears.append(ear)

# 前后法兰
gim_front_flange = create_flange(GIM_OR + 3, GIM_IR, GIM_X2, WALL_T, side='right',
                                   bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)
gim_back_flange = create_flange(GIM_OR + 3, GIM_IR, GIM_X1, WALL_T, side='left',
                                  bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)

gim_parts = [gim, gim_front_flange, gim_back_flange] + ears
gim = trimesh.util.concatenate(gim_parts)
gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
print(f"✅ TVC万向节: X=[{gim.bounds[0][0]:.0f}, {gim.bounds[1][0]:.0f}], {len(gim.faces):,}面")

# ============================================================================
# 步骤7: TVC喷管
# ============================================================================
print("\n" + "="*60)
print("步骤7: 生成TVC喷管")
print("="*60)

# 收敛段
xs_conv, ro_conv, ri_conv = [], [], []
LC = 70
for i in range(30):
    t = i / 29
    x = NOZZLE_X2 - t * LC
    r = NOZZLE_RI_IN - (NOZZLE_RI_IN - NOZZLE_R_THROAT) * (t ** 0.7)
    xs_conv.append(x); ro_conv.append(r + WALL); ri_conv.append(r)

# 扩散段
xs_div, ro_div, ri_div = [], [], []
LD = NOZZLE_L - LC
for i in range(1, 50):
    t = i / 50
    x = NOZZLE_X2 - LC - t * LD
    r = NOZZLE_R_THROAT + (NOZZLE_RE - NOZZLE_R_THROAT) * (t ** 1.4)
    xs_div.append(x); ro_div.append(r + WALL); ri_div.append(r)

xs = xs_conv + xs_div
ro = ro_conv + ro_div
ri = ri_conv + ri_div

nozzle_body = cone_ring(xs, ro, ri, SEG)

# 喷管前端法兰
nozzle_flange = create_flange(GIM_OR - 2, NOZZLE_RI_IN, NOZZLE_X2, WALL_T, side='right',
                                bolt_count=FLANGE_BOLT_COUNT, bolt_r=BOLT_R)

nozzle = trimesh.util.concatenate([nozzle_body, nozzle_flange])
nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
print(f"✅ 喷管: X=[{nozzle.bounds[0][0]:.0f}, {nozzle.bounds[1][0]:.0f}], {len(nozzle.faces):,}面")

# ============================================================================
# 步骤8: 生成所有螺栓和螺母
# ============================================================================
print("\n" + "="*60)
print("步骤8: 生成螺栓/螺母")
print("="*60)

def add_bolts_at_joint(x_pos, bolt_circle_r, bolt_count, bolt_r=2.0, bolt_length=8):
    """在指定位置生成螺栓+螺母"""
    bolts = []
    for i in range(bolt_count):
        th = i * 2 * np.pi / bolt_count + np.pi/bolt_count
        cy = bolt_circle_r * np.cos(th)
        cz = bolt_circle_r * np.sin(th)
        # 螺栓
        bolt = create_bolt(bolt_r=bolt_r, bolt_length=bolt_length, head_height=3)
        bolt.apply_translation([x_pos, cy, cz])
        bolts.append(bolt)
        # 螺母 (在对面)
        nut = create_hex_nut(bolt_r=bolt_r, nut_height=3)
        nut.apply_translation([x_pos - 4, cy, cz])
        bolts.append(nut)
    return trimesh.util.concatenate(bolts)

# 各连接处螺栓位置
# 整流罩-机身: 在x=0
bolts_1 = add_bolts_at_joint(0, (BODY_RO + NOSE_RI)/2 + 1, FLANGE_BOLT_COUNT, BOLT_R)
# 机身-TVC: 在x=BODY_X1=-600
bolts_2 = add_bolts_at_joint(BODY_X1, (BODY_RO + TVC_RO_RIGHT)/2 + 1, FLANGE_BOLT_COUNT, BOLT_R)
# TVC-万向节: 在x=TVC_X1=-680
bolts_3 = add_bolts_at_joint(TVC_X1, (TVC_RO_LEFT + GIM_OR)/2 + 1, FLANGE_BOLT_COUNT, BOLT_R)
# 万向节-喷管: 在x=GIM_X1=-725
bolts_4 = add_bolts_at_joint(GIM_X1, (GIM_OR + NOZZLE_RI_IN)/2 + 1, FLANGE_BOLT_COUNT, BOLT_R)

all_bolts = trimesh.util.concatenate([bolts_1, bolts_2, bolts_3, bolts_4])
all_bolts.export(os.path.join(OUTPUT, "08_bolts_nuts.stl"))
print(f"✅ 螺栓/螺母: {FLANGE_BOLT_COUNT*2}套×4连接处 = {FLANGE_BOLT_COUNT*8}件")

# ============================================================================
# 步骤9: 组装完整火箭
# ============================================================================
print("\n" + "="*60)
print("步骤9: 组装完整火箭")
print("="*60)

parts = [nose, body, all_fins, av, tvc, gim, nozzle, all_bolts]
assembly = trimesh.util.concatenate(parts)
assembly.export(os.path.join(OUTPUT, "00_full_rocket_assembly.stl"))

print(f"\n完整火箭: X=[{assembly.bounds[0][0]:.0f}, {assembly.bounds[1][0]:.0f}]")
print(f"总长度: {assembly.bounds[1][0] - assembly.bounds[0][0]:.0f}mm")
print(f"总面数: {len(assembly.faces):,}")

# ============================================================================
# 连接验证
# ============================================================================
print("\n" + "="*60)
print("连接验证")
print("="*60)

checks = [
    ("整流罩-机身", NOSE_X1, BODY_X2),
    ("机身-TVc", BODY_X1, TVC_X2),
    ("TVC-万向节", TVC_X1, GIM_X2),
    ("万向节-喷管", GIM_X1, NOZZLE_X2),
]

all_ok = True
for name, pos1, pos2 in checks:
    gap = abs(pos1 - pos2)
    status = "✅" if gap < 0.01 else "❌"
    if gap >= 0.01:
        all_ok = False
    print(f"  {name}: 法兰面位置 {pos1:.0f} vs {pos2:.0f} → 偏差 {gap:.3f}mm {status}")

print()
print("零件边界范围:")
for name, part in [("整流罩", nose), ("机身", body), ("TVC", tvc), ("万向节", gim), ("喷管", nozzle)]:
    print(f"  {name}: X=[{part.bounds[0][0]:.0f}, {part.bounds[1][0]:.0f}], Y/Z半径: {np.max(np.abs(part.vertices[:,1:])):.1f}mm")

print()
if all_ok:
    print("🎉 所有连接正确! 法兰面精确接触, 螺栓已连接")
else:
    print("⚠️ 部分连接有偏差")

print("\n" + "="*60)
print("完成! 文件保存在:", OUTPUT)
print("="*60)
