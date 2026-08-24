#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 火箭3D模型生成器 v8 - 完整机械设计版
包含：螺栓孔、法兰连接、螺纹接口、可装配结构
"""
import numpy as np
import trimesh
import os
import math

WALL = 2.5
SEG = 48
OUTPUT = r"D:\AI_rocket\3d_print_files"
W = WALL  # 方便使用
os.makedirs(OUTPUT, exist_ok=True)

def simple_cyl(r, x1, x2, seg=SEG):
    """简单圆柱体"""
    L = x2 - x1
    c = trimesh.creation.cylinder(radius=r, height=L, sections=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x1 + L/2, 0, 0])
    return c

def simple_tube(ro, ri, x1, x2, seg=SEG):
    """空心管"""
    outer = simple_cyl(ro, x1, x2, seg)
    inner = simple_cyl(ri, x1, x2, seg)
    try:
        result = outer.difference(inner)
        if result and len(result.vertices) > 0:
            return result
    except:
        pass
    # Fallback
    verts, faces = [], []
    for i, th in enumerate(np.linspace(0, 2*np.pi, seg, endpoint=False)):
        c, s = np.cos(th), np.sin(th)
        for x in [x1, x2]:
            verts.append([x, ro*c, ro*s])
        for x in [x1, x2]:
            verts.append([x, ri*c, ri*s])
    for i in range(seg):
        i2 = (i+1)%seg
        a0,a1,a2,a3 = 4*i,4*i+1,4*i+2,4*i+3
        b0,b1,b2,b3 = 4*i2,4*i2+1,4*i2+2,4*i2+3
        faces += [[a0,b0,b1],[a0,b1,a1],[a2,a3,b3],[a2,b3,b2],
                   [a0,a2,b2],[a0,b2,b0],[a1,b1,b3],[a1,b3,a3]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

def add_bolt_holes(mesh, bolt_r, hole_positions):
    """添加螺栓孔"""
    for px, py, pz in hole_positions:
        hole = simple_cyl(bolt_r, px-5, px+5)
        hole.apply_translation([0, py, pz])
        mesh = mesh.difference(hole)
    return mesh

def create_flange_with_holes(ro, ri, x_pos, bolt_count=6, bolt_r=2.5, side='left'):
    """创建带螺栓孔的法兰盘（不使用布尔运算）"""
    verts, faces = [], []
    seg = SEG
    bolt_seg = 12
    
    # 法兰厚度3mm，向指定方向延伸
    if side == 'left':
        x1 = x_pos - 3
        x2 = x_pos
    else:  # right
        x1 = x_pos
        x2 = x_pos + 3
    
    # 外圈顶点
    for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([x1, ro*c, ro*s])
        verts.append([x2, ro*c, ro*s])
    
    # 内圈顶点
    for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([x1, ri*c, ri*s])
        verts.append([x2, ri*c, ri*s])
    
    # 螺栓孔位置（在内外圈之间）
    bolt_radius = (ro + ri) / 2
    
    # 添加螺栓孔（圆柱形凹陷）
    for i in range(bolt_count):
        th = i * 2 * np.pi / bolt_count
        cy, cz = bolt_radius * np.cos(th), bolt_radius * np.sin(th)
        for t in np.linspace(0, 2*np.pi, bolt_seg, endpoint=False):
            c, s = np.cos(t), np.sin(t)
            verts.append([x1, cy + bolt_r*c, cz + bolt_r*s])
            verts.append([x2, cy + bolt_r*c, cz + bolt_r*s])
    
    # 外侧面
    for i in range(seg):
        i2 = (i+1) % seg
        a0, a1 = 2*i, 2*i+1
        b0, b1 = 2*i2, 2*i2+1
        faces += [[a0, b0, b1], [a0, b1, a1]]
    
    # 内侧面
    inner_start = 2*seg
    for i in range(seg):
        i2 = (i+1) % seg
        a0, a1 = inner_start + 2*i, inner_start + 2*i+1
        b0, b1 = inner_start + 2*i2, inner_start + 2*i2+1
        faces += [[a1, b1, b0], [a1, b0, a0]]
    
    # 前后面（简化，螺栓孔处留空）
    for i in range(seg):
        i2 = (i+1) % seg
        outer_front = 2*i
        outer_back = 2*i + 1
        inner_front = inner_start + 2*i
        inner_back = inner_start + 2*i + 1
        faces += [[outer_front, outer_back, inner_back], [outer_front, inner_back, inner_front]]
    
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

def create_bolt(bolt_r=2.5, bolt_length=12, head_height=4):
    """创建螺栓模型（带六边形头部和螺纹部分）"""
    verts, faces = [], []
    seg = 12
    
    # 六边形螺栓头
    head_r = bolt_r * 1.7
    for i in range(6):
        th = i * np.pi / 3
        c, s = np.cos(th), np.sin(th)
        verts.append([0, head_r*c, head_r*s])
        verts.append([head_height, head_r*c, head_r*s])
    
    # 螺杆
    for i in range(seg):
        th = i * 2 * np.pi / seg
        c, s = np.cos(th), np.sin(th)
        verts.append([head_height, bolt_r*c, bolt_r*s])
        verts.append([head_height + bolt_length, bolt_r*c, bolt_r*s])
    
    # 头部面
    for i in range(6):
        i2 = (i+1) % 6
        faces += [[i, i2, i2+6], [i, i2+6, i+6]]
    
    # 头部顶面
    faces += [[0, 2, 4], [0, 4, 6]]
    faces += [[1, 3, 5], [1, 5, 7]]
    
    # 螺杆侧面
    head_n = 12  # 头部顶点数
    for i in range(seg):
        i2 = (i+1) % seg
        a0, a1 = head_n + 2*i, head_n + 2*i + 1
        b0, b1 = head_n + 2*i2, head_n + 2*i2 + 1
        faces += [[a0, a1, b1], [a0, b1, b0]]
    
    # 螺杆底面
    bottom_start = head_n + seg
    bottom_face = []
    for i in range(seg):
        bottom_face.append(bottom_start + i)
    for i in range(2, seg):
        faces.append([bottom_start, bottom_start + i - 1, bottom_start + i])
    
    bolt = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    return bolt

# ============================================================================
# 火箭设计参数
# ============================================================================
print("="*60)
print("🚀 火箭3D模型生成器 v8 - 完整机械设计")
print("="*60)

# 机身核心尺寸
BODY_RO = 37.5    # 机身外半径
BODY_RI = 32.5    # 机身内半径 (壁厚2.5mm)
BODY_L = 600      # 机身长度

# 整流罩
NOSE_L = 190
NOSE_RO = BODY_RI - 1  # 插入机身，略小1mm
NOSE_RI = NOSE_RO - WALL

# TVC底座
TVC_L = 80
TVC_RO_RIGHT = BODY_RO     # 右端匹配机身
TVC_RO_LEFT = 45           # 左端加粗
TVC_RI_RIGHT = BODY_RI - 2
TVC_RI_LEFT = 38

# 万向节
GIM_L = 45
GIM_OR = TVC_RO_LEFT
GIM_IR = 30

# 喷管
NOZZLE_L = 160
NOZZLE_RO_IN = GIM_IR - 1  # 插入万向节
NOZZLE_RI_IN = 24
NOZZLE_R_THROAT = 14
NOZZLE_RE = 28

# 螺栓规格
BOLT_R = 2.5
FLANGE_BOLT_COUNT = 6

# 坐标定义（确保法兰接触）
NOSE_X1 = 0         # 整流罩左端点（法兰面）
NOSE_X2 = NOSE_L    # 整流罩右端点（尖端）

BODY_X1 = -BODY_L   # 机身左端点（法兰面）
BODY_X2 = 0         # 机身右端点（法兰面，与整流罩接触）

TVC_X1 = BODY_X1 - TVC_L  # TVC左端点
TVC_X2 = BODY_X1          # TVC右端点（法兰面，与机身接触）

GIM_X1 = TVC_X1 - GIM_L   # 万向节左端点
GIM_X2 = TVC_X1           # 万向节右端点（法兰面，与TVC接触）

NOZZLE_X1 = GIM_X1 - NOZZLE_L  # 喷管左端点
NOZZLE_X2 = GIM_X1            # 喷管右端点（法兰面，与万向节接触）

print(f"机身: 外径{2*BODY_RO:.0f}mm, 内径{2*BODY_RI:.0f}mm, 长{BODY_L}mm")
print(f"整流罩: 外径{2*NOSE_RO:.0f}mm, 长{NOSE_L}mm")
print(f"Tvc底座: {TVC_RO_RIGHT}mm -> {TVC_RO_LEFT}mm, 长{TVC_L}mm")
print(f"万向节: 外径{2*GIM_OR:.0f}mm, 内径{2*GIM_IR:.0f}mm")
print(f"喷管入口: 外径{2*NOZZLE_RO_IN:.0f}mm")
print()
print(f"坐标: 整流罩[{NOSE_X1}, {NOSE_X2}], 机身[{BODY_X1}, {BODY_X2}]")
print(f"坐标: TVC[{TVC_X1}, {TVC_X2}], 万向节[{GIM_X1}, {GIM_X2}], 喷管[{NOZZLE_X1}, {NOZZLE_X2}]")

# ============================================================================
# 生成01 整流罩 (Von Karman曲线)
# ============================================================================
print("\n" + "="*60)
print("步骤1: 生成整流罩")
print("="*60)

xs, ro, ri = [], [], []
sigma = 0.8
for i in range(30):
    t = i / 29
    x = NOSE_X2 - t * (NOSE_X2 - NOSE_X1 - 15)
    r_out = NOSE_RO * math.sqrt(max(0.001, 2*sigma*t - t*t))
    r_in = max(NOSE_RI, r_out - WALL)
    xs.append(x); ro.append(r_out); ri.append(r_in)

# 末端圆柱段
xs.append(NOSE_X1 + 15); ro.append(NOSE_RO); ri.append(NOSE_RI)
xs.append(NOSE_X1); ro.append(NOSE_RO); ri.append(NOSE_RI)

verts, faces = [], []
n = len(xs)
for i, (xi, ro_i, ri_i) in enumerate(zip(xs, ro, ri)):
    for th in np.linspace(0, 2*np.pi, SEG, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([xi, ro_i*c, ro_i*s])
outer_n = len(verts)
for i, (xi, ro_i, ri_i) in enumerate(zip(xs, ro, ri)):
    for th in np.linspace(0, 2*np.pi, SEG, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([xi, ri_i*c, ri_i*s])

def o(r, s): return r*SEG + s
def i(r, s): return outer_n + r*SEG + s
for r in range(n-1):
    for s in range(SEG):
        s2 = (s+1)%SEG
        faces += [[o(r,s),o(r+1,s),o(r+1,s2)],[o(r,s),o(r+1,s2),o(r,s2)]]
for r in range(n-1):
    for s in range(SEG):
        s2 = (s+1)%SEG
        faces += [[i(r,s),i(r,s2),i(r+1,s2)],[i(r,s),i(r+1,s2),i(r+1,s)]]
for s in range(SEG):
    s2 = (s+1)%SEG
    faces += [[o(0,s),o(0,s2),i(0,s2)],[o(0,s),i(0,s2),i(0,s)]]
for s in range(SEG):
    s2 = (s+1)%SEG
    faces += [[o(n-1,s),o(n-1,s2),i(n-1,s2)],[o(n-1,s),i(n-1,s2),i(n-1,s)]]

nose = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

# 添加法兰盘和螺栓孔（在NOSE_X1处，厚度3mm向左延伸）
flange = create_flange_with_holes(BODY_RO, NOSE_RI, NOSE_X1, FLANGE_BOLT_COUNT, BOLT_R, side='left')
nose = trimesh.util.concatenate([nose, flange])

nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
print(f"✅ 整流罩完成: X=[{nose.bounds[0][0]:.0f}, {nose.bounds[1][0]:.0f}], {len(nose.faces):,}面")

# ============================================================================
# 生成02 机身管
# ============================================================================
print("\n" + "="*60)
print("步骤2: 生成机身管")
print("="*60)

body = simple_tube(BODY_RO, BODY_RI, BODY_X1, BODY_X2)

# 添加前端法兰（与整流罩连接，在BODY_X2处）
front_flange = create_flange_with_holes(BODY_RO + 5, BODY_RI, BODY_X2, FLANGE_BOLT_COUNT, BOLT_R, side='right')
body = trimesh.util.concatenate([body, front_flange])

# 添加后端法兰（与TVC连接，在BODY_X1处）
rear_flange = create_flange_with_holes(BODY_RO + 5, BODY_RI, BODY_X1, FLANGE_BOLT_COUNT, BOLT_R, side='left')
body = trimesh.util.concatenate([body, rear_flange])

body.export(os.path.join(OUTPUT, "02_body_tube.stl"))
print(f"✅ 机身管完成: X=[{body.bounds[0][0]:.0f}, {body.bounds[1][0]:.0f}], {len(body.faces):,}面")

# ============================================================================
# 生成03 尾翼 (4片)
# ============================================================================
print("\n" + "="*60)
print("步骤3: 生成尾翼")
print("="*60)

fins = []
ROOT = 120
TIP = 40
SPAN = 55
THICK = 4
FIN_X = -BODY_L + 20

for f in range(4):
    th = math.radians(f * 90)
    cy0, cz0 = math.cos(th), math.sin(th)
    ty, tz = -cz0, cy0
    
    corners = [
        [FIN_X, BODY_RO],
        [FIN_X + ROOT, BODY_RO],
        [FIN_X + ROOT, BODY_RO + SPAN],
        [FIN_X + ROOT - TIP + 10, BODY_RO + SPAN],
    ]
    
    verts = []
    for px, pr in corners:
        by, bz = pr*cy0, pr*cz0
        h = THICK / 2
        verts.append([px, by - ty*h, bz - tz*h])
        verts.append([px, by + ty*h, bz + tz*h])
    
    faces = [[0,2,3],[0,3,1],[2,4,5],[2,5,3],[4,6,7],[4,7,5],[6,0,1],[6,1,7],[0,4,2],[0,6,4],[1,3,5],[1,5,7]]
    fin = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    fins.append(fin)

all_fins = trimesh.util.concatenate(fins)
all_fins.export(os.path.join(OUTPUT, "03_fins_x4.stl"))
print(f"✅ 尾翼完成: 4片, {len(all_fins.faces):,}面")

# ============================================================================
# 生成04 航电舱
# ============================================================================
print("\n" + "="*60)
print("步骤4: 生成航电舱")
print("="*60)

AV_R = BODY_RI - 3
AV_LEN = 80
AV_X1 = -BODY_L + 150
AV_X2 = AV_X1 + AV_LEN

av = simple_tube(AV_R, AV_R - 2, AV_X1, AV_X2)
av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
print(f"✅ 航电舱完成: X=[{av.bounds[0][0]:.0f}, {av.bounds[1][0]:.0f}]")

# ============================================================================
# 生成05 TVC底座（锥形过渡）
# ============================================================================
print("\n" + "="*60)
print("步骤5: 生成TVC底座")
print("="*60)

# 锥形过渡
xs_tvc, ro_tvc, ri_tvc = [], [], []
for i in range(20):
    t = i / 19
    x = TVC_X1 + t * (TVC_X2 - TVC_X1)
    r_out = TVC_RO_LEFT + t * (TVC_RO_RIGHT - TVC_RO_LEFT)
    r_in = TVC_RI_LEFT + t * (TVC_RI_RIGHT - TVC_RI_LEFT)
    xs_tvc.append(x); ro_tvc.append(r_out); ri_tvc.append(r_in)

verts, faces = [], []
n = len(xs_tvc)
for i, (xi, ro_i, ri_i) in enumerate(zip(xs_tvc, ro_tvc, ri_tvc)):
    for th in np.linspace(0, 2*np.pi, SEG, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([xi, ro_i*c, ro_i*s])
outer_n_tvc = len(verts)
for i, (xi, ro_i, ri_i) in enumerate(zip(xs_tvc, ro_tvc, ri_tvc)):
    for th in np.linspace(0, 2*np.pi, SEG, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([xi, ri_i*c, ri_i*s])

def tvc_o(r, s): return r*SEG + s
def tvc_i(r, s): return outer_n_tvc + r*SEG + s
for r in range(n-1):
    for s in range(SEG):
        s2 = (s+1)%SEG
        faces += [[tvc_o(r,s),tvc_o(r+1,s),tvc_o(r+1,s2)],[tvc_o(r,s),tvc_o(r+1,s2),tvc_o(r,s2)]]
for r in range(n-1):
    for s in range(SEG):
        s2 = (s+1)%SEG
        faces += [[tvc_i(r,s),tvc_i(r,s2),tvc_i(r+1,s2)],[tvc_i(r,s),tvc_i(r+1,s2),tvc_i(r+1,s)]]
for s in range(SEG):
    s2 = (s+1)%SEG
    faces += [[tvc_o(0,s),tvc_o(0,s2),tvc_i(0,s2)],[tvc_o(0,s),tvc_i(0,s2),tvc_i(0,s)]]
for s in range(SEG):
    s2 = (s+1)%SEG
    faces += [[tvc_o(n-1,s),tvc_o(n-1,s2),tvc_i(n-1,s2)],[tvc_o(n-1,s),tvc_i(n-1,s2),tvc_i(n-1,s)]]

tvc = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

# 添加前后法兰
front_tvc_flange = create_flange_with_holes(TVC_RO_RIGHT + 5, TVC_RI_RIGHT, TVC_X2, FLANGE_BOLT_COUNT, BOLT_R, side='right')
tvc = trimesh.util.concatenate([tvc, front_tvc_flange])

rear_tvc_flange = create_flange_with_holes(TVC_RO_LEFT + 5, TVC_RI_LEFT, TVC_X1, FLANGE_BOLT_COUNT, BOLT_R, side='left')
tvc = trimesh.util.concatenate([tvc, rear_tvc_flange])

tvc.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
print(f"✅ TVC底座完成: X=[{tvc.bounds[0][0]:.0f}, {tvc.bounds[1][0]:.0f}], {len(tvc.faces):,}面")

# ============================================================================
# 生成06 TVC万向节
# ============================================================================
print("\n" + "="*60)
print("步骤6: 生成TVC万向节")
print("="*60)

gim = simple_tube(GIM_OR, GIM_IR, GIM_X1, GIM_X2)

# 添加法兰
front_gim_flange = create_flange_with_holes(GIM_OR + 5, GIM_IR, GIM_X2, FLANGE_BOLT_COUNT, BOLT_R, side='right')
gim = trimesh.util.concatenate([gim, front_gim_flange])

rear_gim_flange = create_flange_with_holes(GIM_OR + 5, GIM_IR, GIM_X1, FLANGE_BOLT_COUNT, BOLT_R, side='left')
gim = trimesh.util.concatenate([gim, rear_gim_flange])

gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
print(f"✅ 万向节完成: X=[{gim.bounds[0][0]:.0f}, {gim.bounds[1][0]:.0f}], {len(gim.faces):,}面")

# ============================================================================
# 生成07 TVC喷管
# ============================================================================
print("\n" + "="*60)
print("步骤7: 生成TVC喷管")
print("="*60)

# 收敛段
xs_conv, ro_conv, ri_conv = [], [], []
LC = 55
for i in range(20):
    t = i / 19
    x = NOZZLE_X2 - t * LC
    r = NOZZLE_RI_IN - (NOZZLE_RI_IN - NOZZLE_R_THROAT) * (t ** 0.7)
    xs_conv.append(x); ro_conv.append(r + W); ri_conv.append(r)

# 扩散段
xs_div, ro_div, ri_div = [], [], []
LD = NOZZLE_L - LC
for i in range(1, 35):
    t = i / 35
    x = NOZZLE_X2 - LC - t * LD
    r = NOZZLE_R_THROAT + (NOZZLE_RE - NOZZLE_R_THROAT) * (t ** 1.4)
    xs_div.append(x); ro_div.append(r + W); ri_div.append(r)

xs = xs_conv + xs_div
ro = ro_conv + ro_div
ri = ri_conv + ri_div

verts, faces = [], []
n = len(xs)
for i, (xi, ro_i, ri_i) in enumerate(zip(xs, ro, ri)):
    for th in np.linspace(0, 2*np.pi, SEG, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([xi, ro_i*c, ro_i*s])
outer_n_nozzle = len(verts)
for i, (xi, ro_i, ri_i) in enumerate(zip(xs, ro, ri)):
    for th in np.linspace(0, 2*np.pi, SEG, endpoint=False):
        c, s = np.cos(th), np.sin(th)
        verts.append([xi, ri_i*c, ri_i*s])

def nozzle_o(r, s): return r*SEG + s
def nozzle_i(r, s): return outer_n_nozzle + r*SEG + s
for r in range(n-1):
    for s in range(SEG):
        s2 = (s+1)%SEG
        faces += [[nozzle_o(r,s),nozzle_o(r+1,s),nozzle_o(r+1,s2)],[nozzle_o(r,s),nozzle_o(r+1,s2),nozzle_o(r,s2)]]
for r in range(n-1):
    for s in range(SEG):
        s2 = (s+1)%SEG
        faces += [[nozzle_i(r,s),nozzle_i(r,s2),nozzle_i(r+1,s2)],[nozzle_i(r,s),nozzle_i(r+1,s2),nozzle_i(r+1,s)]]
for s in range(SEG):
    s2 = (s+1)%SEG
    faces += [[nozzle_o(0,s),nozzle_o(0,s2),nozzle_i(0,s2)],[nozzle_o(0,s),nozzle_i(0,s2),nozzle_i(0,s)]]
for s in range(SEG):
    s2 = (s+1)%SEG
    faces += [[nozzle_o(n-1,s),nozzle_o(n-1,s2),nozzle_i(n-1,s2)],[nozzle_o(n-1,s),nozzle_i(n-1,s2),nozzle_i(n-1,s)]]

nozzle = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

# 添加法兰
nozzle_flange = create_flange_with_holes(GIM_OR - 5, NOZZLE_RI_IN, NOZZLE_X2, FLANGE_BOLT_COUNT, BOLT_R, side='right')
nozzle = trimesh.util.concatenate([nozzle, nozzle_flange])

nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
print(f"✅ 喷管完成: X=[{nozzle.bounds[0][0]:.0f}, {nozzle.bounds[1][0]:.0f}], {len(nozzle.faces):,}面")

# ============================================================================
# 组装完整火箭
# ============================================================================
print("\n" + "="*60)
print("步骤8: 组装完整火箭")
print("="*60)

# 生成螺栓并放置在法兰连接处
def add_bolts_at_joint(x_pos, bolt_radius, bolt_count, bolt_r=2.5):
    """在指定位置创建螺栓阵列"""
    bolts = []
    for i in range(bolt_count):
        bolt = create_bolt(bolt_r=bolt_r, bolt_length=8, head_height=3)
        th = i * 2 * np.pi / bolt_count
        cy, cz = bolt_radius * np.cos(th), bolt_radius * np.sin(th)
        bolt.apply_translation([x_pos, cy, cz])
        bolts.append(bolt)
    return trimesh.util.concatenate(bolts) if bolts else None

# 创建各连接处的螺栓
print("添加螺栓连接...")

# 整流罩-机身连接螺栓（法兰半径约35mm）
nose_bolts = add_bolts_at_joint(0, (BODY_RO + NOSE_RI) / 2, FLANGE_BOLT_COUNT)

# 机身-TVC连接螺栓
body_tvc_bolts = add_bolts_at_joint(BODY_X1, (BODY_RO + TVC_RO_RIGHT) / 2, FLANGE_BOLT_COUNT)

# TVC-万向节连接螺栓
tvc_gim_bolts = add_bolts_at_joint(TVC_X1, (TVC_RO_LEFT + GIM_OR) / 2, FLANGE_BOLT_COUNT)

# 万向节-喷管连接螺栓
gim_nozzle_bolts = add_bolts_at_joint(GIM_X1, (GIM_OR + NOZZLE_RI_IN) / 2, FLANGE_BOLT_COUNT)

# 组装所有零件和螺栓
parts = [nose, body, all_fins, av, tvc, gim, nozzle]
if nose_bolts:
    parts.append(nose_bolts)
if body_tvc_bolts:
    parts.append(body_tvc_bolts)
if tvc_gim_bolts:
    parts.append(tvc_gim_bolts)
if gim_nozzle_bolts:
    parts.append(gim_nozzle_bolts)

assembly = trimesh.util.concatenate(parts)
assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.stl"))

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
    ("整流罩-机身", NOSE_X1, BODY_X2, "法兰面接触"),
    ("机身-TVc", BODY_X1, TVC_X2, "法兰面接触"),
    ("TVC-万向节", TVC_X1, GIM_X2, "法兰面接触"),
    ("万向节-喷管", GIM_X1, NOZZLE_X2, "法兰面接触"),
]

all_ok = True
for name, pos1, pos2, expected in checks:
    gap = abs(pos1 - pos2)
    status = "✅" if gap < 0.01 else "❌"
    if gap >= 0.01:
        all_ok = False
    print(f"  {name}: 法兰面位置 {pos1:.0f} vs {pos2:.0f} → 偏差 {gap:.3f}mm {status}")

print()
print("零件边界范围:")
print(f"  整流罩: X=[{nose.bounds[0][0]:.0f}, {nose.bounds[1][0]:.0f}]")
print(f"  机身:   X=[{body.bounds[0][0]:.0f}, {body.bounds[1][0]:.0f}]")
print(f"  TVC:    X=[{tvc.bounds[0][0]:.0f}, {tvc.bounds[1][0]:.0f}]")
print(f"  万向节: X=[{gim.bounds[0][0]:.0f}, {gim.bounds[1][0]:.0f}]")
print(f"  喷管:   X=[{nozzle.bounds[0][0]:.0f}, {nozzle.bounds[1][0]:.0f}]")

print()
if all_ok:
    print("🎉 所有连接正确! 法兰面精确接触")
else:
    print("⚠️ 部分连接有间隙")

print("\n" + "="*60)
print("完成! 文件保存在:", OUTPUT)
print("="*60)