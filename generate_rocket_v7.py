#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v7.0 [修复版]
==============================================================================
修复问题:
  ✅ 机身-TVc底座 100mm间隙 -> 修正为紧密连接
  ✅ 万向节-喷管 30mm间隙 -> 修正为紧密连接
  ✅ TVC-万向节 30mm间隙 -> 修正为紧密连接
  ✅ 机身-尾翼 5mm间隙 -> 修正为紧密连接
  ✅ 加强肋导致的半径偏差 -> 修正为不影响外径

设计原则:
  +X = 火箭尖头方向 (右侧)
  零件从右到左依次连接, 无间隙
==============================================================================
"""
import numpy as np
import trimesh
import os
import math
from datetime import datetime

# ============================================================================
# 核心参数
# ============================================================================
BODY_R = 37.5          # 机身半径 (不含肋条)
BODY_D = BODY_R * 2    # 75mm
WALL = 2.5             # 壁厚
SEG = 48
OUTPUT = r"D:\AI_rocket\3d_print_files"
os.makedirs(OUTPUT, exist_ok=True)

# ============================================================================
# 零件长度定义
# ============================================================================
L_NOSE = 190    # 整流罩
L_BODY = 630    # 机身
L_AV = 120      # 航电舱
L_TVC = 85      # TVC底座
L_GIM = 50      # 万向节
L_NOZ = 180     # 喷管

# ============================================================================
# 精确坐标计算 (从右到左, 紧密连接)
# ============================================================================
# 整流罩: 0 ~ 190 (+X 方向)
X_NOSE_TIP = L_NOSE      # 190 尖点
X_NOSE_BASE = 0          # 0 法兰端

# 机身: -630 ~ 0 (左端到右端, 右端接整流罩)
X_BODY_LEFT = -L_BODY    # -630 机身左端
X_BODY_RIGHT = 0         # 0 机身右端

# 航电舱: 嵌入机身内部, 位置在机身中段
X_AV_START = X_BODY_LEFT + 150  # -480 (距左端150mm)
X_AV_END = X_AV_START + L_AV     # -360

# TVC底座: 直接接在机身左端
X_TVC_LEFT = X_BODY_LEFT - L_TVC  # -630 - 85 = -715
X_TVC_RIGHT = X_BODY_LEFT         # -630 (与机身左端对齐)

# 万向节: 直接接在TVC底座左端
X_GIM_LEFT = X_TVC_LEFT - L_GIM   # -715 - 50 = -765
X_GIM_RIGHT = X_TVC_LEFT          # -715

# 喷管: 直接接在万向节左端
X_NOZ_LEFT = X_GIM_LEFT - L_NOZ   # -765 - 180 = -945
X_NOZ_RIGHT = X_GIM_LEFT          # -765

print(f"坐标计算:")
print(f"  整流罩: {X_NOSE_BASE:.0f} ~ {X_NOSE_TIP:.0f} (L={L_NOSE})")
print(f"  机身:   {X_BODY_LEFT:.0f} ~ {X_BODY_RIGHT:.0f} (L={L_BODY})")
print(f"  航电舱: {X_AV_START:.0f} ~ {X_AV_END:.0f} (L={L_AV})")
print(f"  TVC底:  {X_TVC_LEFT:.0f} ~ {X_TVC_RIGHT:.0f} (L={L_TVC})")
print(f"  万向节: {X_GIM_LEFT:.0f} ~ {X_GIM_RIGHT:.0f} (L={L_GIM})")
print(f"  喷管:   {X_NOZ_LEFT:.0f} ~ {X_NOZ_RIGHT:.0f} (L={L_NOZ})")
print(f"  总长:   {X_NOSE_TIP - X_NOZ_LEFT:.0f}mm")
print()

# ============================================================================
# 几何工具
# ============================================================================
def make_cylinder(radius, x1, x2, seg=SEG):
    """创建圆柱, x1 到 x2"""
    L = x2 - x1
    c = trimesh.creation.cylinder(radius=radius, height=L, sections=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x1 + L/2, 0, 0])
    return c

def make_tube(outer_r, inner_r, x1, x2, seg=SEG):
    """创建空心管, x1 到 x2"""
    L = x2 - x1
    outer = trimesh.creation.cylinder(radius=outer_r, height=L, sections=seg)
    inner = trimesh.creation.cylinder(radius=inner_r, height=L, sections=seg)
    outer.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    inner.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    outer.apply_translation([x1 + L/2, 0, 0])
    inner.apply_translation([x1 + L/2, 0, 0])
    try:
        result = outer.difference(inner)
        if result is not None and len(result.vertices) > 0:
            return result
    except:
        pass
    # fallback: 手动
    return _manual_tube(outer_r, inner_r, x1, x2, seg)

def _manual_tube(ro, ri, x1, x2, seg):
    verts, faces = [], []
    for i, theta in enumerate(np.linspace(0, 2*np.pi, seg, endpoint=False)):
        c, s = np.cos(theta), np.sin(theta)
        for x in [x1, x2]:
            verts.append([x, ro*c, ro*s])
        for x in [x1, x2]:
            verts.append([x, ri*c, ri*s])
    for i in range(seg):
        i2 = (i+1) % seg
        A0,A1,A2,A3 = 4*i, 4*i+1, 4*i+2, 4*i+3
        B0,B1,B2,B3 = 4*i2, 4*i2+1, 4*i2+2, 4*i2+3
        faces += [[A0,B0,B1],[A0,B1,A1],[A2,A3,B3],[A2,B3,B2],
                   [A0,A2,B2],[A0,B2,B0],[A1,B1,B3],[A1,B3,A3]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

def make_ring(r, x1, x2, seg=SEG):
    """创建实心圆柱环"""
    return make_cylinder(r, x1, x2, seg)

def add_holes_along_circle(mesh, n_holes, hole_r, circle_r, x_plane, tan_y=1, tan_z=0):
    """在 x=x_plane 平面添加 n_holes 个孔"""
    holes = []
    for i in range(n_holes):
        theta = math.radians(i * 360.0 / n_holes)
        hy = circle_r * math.cos(theta) * tan_y
        hz = circle_r * math.sin(theta) * tan_z
        h = make_cylinder(hole_r, x_plane - 5, x_plane + 5, seg=8)
        h.apply_translation([0, hy, hz])
        holes.append(h)
    return holes

def make_revolve(xs, ro_arr, ri_arr, seg=SEG):
    """旋转体, xs=[], ro_arr=[], ri_arr=[]"""
    n = len(xs)
    verts = []
    for xi, ro, ri in zip(xs, ro_arr, ri_arr):
        for theta in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
            verts.append([xi, ro*c, ro*s])
    outer_n = len(verts)
    for xi, ro, ri in zip(xs, ro_arr, ri_arr):
        for theta in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
            verts.append([xi, ri*c, ri*s])
    faces = []
    def o(r, s): return r*seg + s
    def i(r, s): return outer_n + r*seg + s
    for r in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            faces += [[o(r,s),o(r+1,s),o(r+1,s2)],[o(r,s),o(r+1,s2),o(r,s2)]]
    for r in range(n-1):
        for s in range(seg):
            s2 = (s+1) % seg
            faces += [[i(r,s),i(r,s2),i(r+1,s2)],[i(r,s),i(r+1,s2),i(r+1,s)]]
    for s in range(seg):
        s2 = (s+1) % seg
        faces += [[o(0,s),o(0,s2),i(0,s2)],[o(0,s),i(0,s2),i(0,s)]]
    for s in range(seg):
        s2 = (s+1) % seg
        faces += [[o(n-1,s),o(n-1,s2),i(n-1,s2)],[o(n-1,s),i(n-1,s2),i(n-1,s)]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

# ============================================================================
# 01. 整流罩
# ============================================================================
def build_nose():
    """Von Karman曲线, 带法兰和螺栓孔"""
    all_parts = []
    
    # Von Karman 主体
    n = 50
    xs, ro, ri = [], [], []
    for i in range(n):
        t = i / (n - 1)  # 0=尖端, 1=底部
        x = X_NOSE_TIP - t * (L_NOSE - 15)  # 尖端到 base
        sigma = 0.8
        r_out = BODY_R * math.sqrt(max(0.001, 2*sigma*t - t*t))
        r_in = max(0.5, r_out - WALL)
        xs.append(x); ro.append(r_out); ri.append(r_in)
    
    nose_body = make_revolve(xs, ro, ri)
    all_parts.append(nose_body)
    
    # 法兰 (插入机身部分, x=15 到 x=0)
    flange = make_tube(BODY_R - 1, BODY_R - WALL - 1, X_NOSE_BASE, X_NOSE_BASE + 15)
    all_parts.append(flange)
    
    # 法兰端面盘
    end_cap = make_cylinder(BODY_R - WALL - 1, X_NOSE_BASE, X_NOSE_BASE + 3)
    all_parts.append(end_cap)
    
    # O型圈槽 (x=18 附近)
    groove = make_tube(BODY_R + 0.5, BODY_R - 1.5, X_NOSE_BASE + 5, X_NOSE_BASE + 9)
    all_parts.append(groove)
    
    # 6个M3螺栓孔 (x=15 平面, 60°均布)
    for i in range(6):
        theta = math.radians(i * 60)
        hy = (BODY_R - 8) * math.cos(theta)
        hz = (BODY_R - 8) * math.sin(theta)
        hole = make_cylinder(1.5, X_NOSE_BASE + 10, X_NOSE_BASE + 20, seg=8)
        hole.apply_translation([0, hy, hz])
        all_parts.append(hole)
    
    nose = trimesh.util.concatenate(all_parts)
    nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
    nose.export(os.path.join(OUTPUT, "01_nose_cone.glb"))
    b = nose.bounds
    print(f"  01 整流罩: X=[{b[0][0]:.0f},{b[1][0]:.0f}] Ø{BODY_D:.0f}mm L={b[1][0]-b[0][0]:.0f}mm ✅")
    return nose

# ============================================================================
# 02. 机身管
# ============================================================================
def build_body():
    """空心管 + 加强肋(内嵌不外扩) + 穿线孔"""
    all_parts = []
    
    # 主空心管
    body = make_tube(BODY_R, BODY_R - WALL, X_BODY_LEFT, X_BODY_RIGHT)
    all_parts.append(body)
    
    # 加强肋 (内部, 不影响外径)
    rib_inner_r = 3  # 内部肋条
    rib_circle_r = BODY_R - WALL - rib_inner_r/2
    for i in range(4):
        theta = math.radians(i * 90)
        rib = make_tube(rib_inner_r, 0, X_BODY_LEFT + 10, X_BODY_RIGHT - 10, seg=12)
        v = rib.vertices.copy()
        v[:, 1] += rib_circle_r * math.cos(theta)
        v[:, 2] += rib_circle_r * math.sin(theta)
        rib.vertices = v
        all_parts.append(rib)
    
    # 穿线孔 (机身两侧, Ø6mm)
    wire_hole_x = [-480, -380, -280]
    for wx in wire_hole_x:
        for sign in [-1, 1]:
            hole = make_cylinder(3, wx - 8, wx + 8, seg=10)
            hole.apply_translation([0, (BODY_R + 2) * sign, 0])
            all_parts.append(hole)
    
    # 机身两端螺栓孔 (4×M5, 贯穿)
    for x_bolt in [X_BODY_RIGHT - 10, X_BODY_LEFT + 10]:
        for i in range(4):
            theta = math.radians(i * 90 + 45)
            by = (BODY_R - 5) * math.cos(theta)
            bz = (BODY_R - 5) * math.sin(theta)
            hole = make_cylinder(2.5, x_bolt - 20, x_bolt + 20, seg=8)
            hole.apply_translation([0, by, bz])
            all_parts.append(hole)
    
    body_all = trimesh.util.concatenate(all_parts)
    body_all.export(os.path.join(OUTPUT, "02_body_tube.stl"))
    body_all.export(os.path.join(OUTPUT, "02_body_tube.glb"))
    b = body_all.bounds
    max_r = max(abs(b[1][1]), abs(b[1][2]))
    print(f"  02 机身管: X=[{b[0][0]:.0f},{b[1][0]:.0f}] Ø{max_r*2:.0f}mm L={L_BODY}mm ✅")
    return body_all

# ============================================================================
# 03. 尾翼 ×4
# ============================================================================
def build_fins():
    """梯形后掠翼 + 根部加强 + M4螺栓孔"""
    fins_list = []
    ROOT_CHORD = 150
    TIP_CHORD = 50
    SPAN = 65
    THICK = 5
    
    fin_start_x = X_BODY_LEFT + 5
    root_end_x = fin_start_x + ROOT_CHORD
    sweep = (ROOT_CHORD - TIP_CHORD) / 2 + 10
    tip_start_x = fin_start_x + sweep
    
    for f in range(4):
        theta = math.radians(f * 90)
        cy0, cz0 = math.cos(theta), math.sin(theta)
        ty, tz = -cz0, cy0  # 切线
        
        # 4角坐标
        corners = [
            [fin_start_x, BODY_R],
            [root_end_x, BODY_R],
            [root_end_x, BODY_R + SPAN],
            [tip_start_x, BODY_R + SPAN],
        ]
        
        verts = []
        for px, pr in corners:
            by, bz = pr*cy0, pr*cz0
            h = THICK / 2 * (1.5 if px < fin_start_x + 30 else 1.0)  # 根部加厚
            verts.append([px, by - ty*h, bz - tz*h])
            verts.append([px, by + ty*h, bz + tz*h])
        
        faces = [
            [0,2,3],[0,3,1],[2,4,5],[2,5,3],
            [4,6,7],[4,7,5],[6,0,1],[6,1,7],
            [0,4,2],[0,6,4],[1,3,5],[1,5,7]
        ]
        fin = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
        fins_list.append(fin)
        
        # M4螺栓孔 (根弦上3个)
        for bt in [0.25, 0.5, 0.75]:
            bx = fin_start_x + bt * ROOT_CHORD
            hole = make_cylinder(2, fin_start_x - 5, fin_start_x + 5, seg=8)
            hole.apply_translation([bx, 0, 0])
            v = hole.vertices.copy()
            new = np.zeros_like(v)
            new[:, 0] = v[:, 0]
            new[:, 1] = v[:, 1]*cy0 - v[:, 2]*cz0
            new[:, 2] = v[:, 1]*cz0 + v[:, 2]*cy0
            hole.vertices = new
            fins_list.append(hole)
    
    fins = trimesh.util.concatenate(fins_list)
    fins.export(os.path.join(OUTPUT, "03_fins_x4.stl"))
    fins.export(os.path.join(OUTPUT, "03_fins_x4.glb"))
    b = fins.bounds
    print(f"  03 尾翼×4: X=[{b[0][0]:.0f},{b[1][0]:.0f}] 根弦{ROOT_CHORD} 翼展{SPAN} ✅")
    return fins

# ============================================================================
# 04. 航电舱
# ============================================================================
def build_avionics():
    """嵌入机身的内部舱, 带检修盖板和线缆出口"""
    all_parts = []
    AV_R = BODY_R - WALL - 3  # 32mm, 略小于机身内径
    AV_WALL = 2.0
    
    # 外壳
    shell = make_tube(AV_R, AV_R - AV_WALL, X_AV_START, X_AV_END)
    all_parts.append(shell)
    
    # 左右端盖
    for ex in [X_AV_START - 3, X_AV_END]:
        cap = make_cylinder(AV_R - AV_WALL + 0.5, ex, ex + 3)
        all_parts.append(cap)
    
    # 检修盖板 (x = X_AV_START + 30)
    hatch_x = X_AV_START + 30
    hatch_r = AV_R * 0.7
    hatch = make_cylinder(hatch_r, hatch_x, hatch_x + 4)
    all_parts.append(hatch)
    
    # 6个M3螺丝孔
    for i in range(6):
        theta = math.radians(i * 60)
        hy = (hatch_r + 4) * math.cos(theta)
        hz = (hatch_r + 4) * math.sin(theta)
        hole = make_cylinder(1.5, hatch_x - 2, hatch_x + 2, seg=8)
        hole.apply_translation([0, hy, hz])
        all_parts.append(hole)
    
    # 线缆出口 (两侧)
    for sign in [-1, 1]:
        port = make_cylinder(4, X_AV_START + X_AV_END - X_AV_START, X_AV_START + X_AV_END - X_AV_START + 8)
        port.apply_translation([0, (AV_R + 5) * sign, 0])
        all_parts.append(port)
    
    av = trimesh.util.concatenate(all_parts)
    av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
    av.export(os.path.join(OUTPUT, "04_avionics_bay.glb"))
    b = av.bounds
    print(f"  04 航电舱: X=[{b[0][0]:.0f},{b[1][0]:.0f}] Ø{AV_R*2:.0f}mm L={L_AV}mm ✅")
    return av

# ============================================================================
# 05. TVC底座
# ============================================================================
def build_tvc_base():
    """法兰盘 + 中心孔 + 轴承座 + 舵机安装"""
    all_parts = []
    FLANGE_R = BODY_R + 8  # 45.5mm
    CENTER_HOLE_R = 22
    L = L_TVC
    
    # 主法兰
    main = make_tube(FLANGE_R, CENTER_HOLE_R, X_TVC_LEFT, X_TVC_RIGHT)
    all_parts.append(main)
    
    # 连接法兰 (右端)
    attach = make_tube(BODY_R + 3, CENTER_HOLE_R, X_TVC_RIGHT - 12, X_TVC_RIGHT)
    all_parts.append(attach)
    
    # 4×M5贯穿螺栓孔
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        by = (FLANGE_R - 5) * math.cos(theta)
        bz = (FLANGE_R - 5) * math.sin(theta)
        hole = make_cylinder(2.5, X_TVC_LEFT - 15, X_TVC_LEFT + 15, seg=8)
        hole.apply_translation([0, by, bz])
        all_parts.append(hole)
    
    # 4个轴承座 (径向伸出)
    for i in range(4):
        theta = math.radians(i * 90)
        bcy = (FLANGE_R + 12) * math.cos(theta)
        bcz = (FLANGE_R + 12) * math.sin(theta)
        bearing = make_cylinder(10, X_TVC_LEFT + L/2 - 8, X_TVC_LEFT + L/2 + 8, seg=16)
        v = bearing.vertices.copy()
        v[:, 1] += bcy
        v[:, 2] += bcz
        bearing.vertices = v
        all_parts.append(bearing)
        
        # 轴承孔
        bore = make_cylinder(5, X_TVC_LEFT + L/2 - 15, X_TVC_LEFT + L/2 + 15, seg=12)
        bore.apply_translation([0, bcy, bcz])
        all_parts.append(bore)
    
    # 4个舵机安装孔
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        scy = (CENTER_HOLE_R + 8) * math.cos(theta)
        scz = (CENTER_HOLE_R + 8) * math.sin(theta)
        servo = make_cylinder(3, X_TVC_LEFT + 5, X_TVC_LEFT + 20, seg=10)
        servo.apply_translation([0, scy, scz])
        all_parts.append(servo)
    
    base = trimesh.util.concatenate(all_parts)
    base.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
    base.export(os.path.join(OUTPUT, "05_tvc_base.glb"))
    b = base.bounds
    print(f"  05 TVC底座: X=[{b[0][0]:.0f},{b[1][0]:.0f}] Ø{FLANGE_R*2:.0f}mm L={L}mm ✅")
    return base

# ============================================================================
# 06. TVC万向节
# ============================================================================
def build_gimbal():
    """双环 + 枢轴 + 舵机臂"""
    all_parts = []
    OUTER_R = BODY_R + 2  # 39.5mm
    INNER_R = OUTER_R - 10
    L = L_GIM
    MID_X = X_GIM_LEFT + L/2
    
    # 外环
    outer_ring = make_tube(OUTER_R, OUTER_R - 8, X_GIM_LEFT + 5, X_GIM_RIGHT - 5)
    all_parts.append(outer_ring)
    
    # 内环
    inner_ring = make_tube(INNER_R, INNER_R - 6, X_GIM_LEFT + 15, X_GIM_RIGHT - 15)
    all_parts.append(inner_ring)
    
    # 4个枢轴螺栓孔
    for i in range(4):
        theta = math.radians(i * 90)
        pcy = (OUTER_R + 12) * math.cos(theta)
        pcz = (OUTER_R + 12) * math.sin(theta)
        pivot = make_cylinder(4, MID_X - 5, MID_X + 5, seg=14)
        pivot.apply_translation([0, pcy, pcz])
        all_parts.append(pivot)
        
        # 螺栓通孔
        bore = make_cylinder(2.5, MID_X - 20, MID_X + 20, seg=10)
        bore.apply_translation([0, pcy, pcz])
        all_parts.append(bore)
    
    # 4个舵机连接臂
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        acy = (INNER_R + 18) * math.cos(theta)
        acz = (INNER_R + 18) * math.sin(theta)
        arm = make_cylinder(5, MID_X - 5, MID_X + 5, seg=12)
        arm.apply_translation([0, acy, acz])
        all_parts.append(arm)
    
    gimbal = trimesh.util.concatenate(all_parts)
    gimbal.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
    gimbal.export(os.path.join(OUTPUT, "06_tvc_gimbal.glb"))
    b = gimbal.bounds
    print(f"  06 TVC万向节: X=[{b[0][0]:.0f},{b[1][0]:.0f}] Ø{OUTER_R*2:.0f}mm L={L}mm ✅")
    return gimbal

# ============================================================================
# 07. TVC喷管
# ============================================================================
def build_nozzle():
    """收敛-扩散喷管 + 法兰 + O型圈槽"""
    all_parts = []
    R_IN = 30      # 入口
    R_TH = 16      # 喉道
    R_EX = 26      # 出口
    W = 4
    L_CONV = 50
    L_DIV = L_CONV * 2
    FLANGE_IN_R = R_IN + 12
    FLANGE_EX_R = R_EX + 10
    
    x_inlet = X_NOZ_RIGHT  # -765
    x_throat = x_inlet - L_CONV
    x_exit = x_throat - L_DIV
    x_flange_in_end = x_inlet + 15
    x_flange_ex_start = x_exit - 12
    
    # 入口法兰
    flange_in = make_tube(FLANGE_IN_R, R_IN, x_inlet, x_flange_in_end)
    all_parts.append(flange_in)
    
    # 入口法兰8个M5螺栓孔
    for i in range(8):
        theta = math.radians(i * 45)
        by = (FLANGE_IN_R - 5) * math.cos(theta)
        bz = (FLANGE_IN_R - 5) * math.sin(theta)
        hole = make_cylinder(2.5, x_inlet - 5, x_flange_in_end + 5, seg=8)
        hole.apply_translation([0, by, bz])
        all_parts.append(hole)
    
    # 入口O型圈槽
    seal_in = make_tube(FLANGE_IN_R - 4, FLANGE_IN_R - 8, x_inlet + 5, x_inlet + 9)
    all_parts.append(seal_in)
    
    # 收敛-扩散段
    xs, ro_arr, ri_arr = [], [], []
    n_conv, n_div = 25, 40
    
    for i in range(n_conv):
        t = i / (n_conv - 1)
        x = x_inlet - t * L_CONV
        ri_val = R_IN - (R_IN - R_TH) * (t ** 0.7)
        xs.append(x); ro_arr.append(ri_val + W); ri_arr.append(ri_val)
    
    for i in range(1, n_div + 1):
        t = i / n_div
        x = x_throat - t * L_DIV
        ri_val = R_TH + (R_EX - R_TH) * (t ** 1.3)
        xs.append(x); ro_arr.append(ri_val + W); ri_arr.append(ri_val)
    
    nozzle_body = make_revolve(xs, ro_arr, ri_arr)
    all_parts.append(nozzle_body)
    
    # 喉道加强环
    throat = make_tube(R_TH + W + 3, R_TH, x_throat - 4, x_throat + 4)
    all_parts.append(throat)
    
    # 出口法兰
    flange_ex = make_tube(FLANGE_EX_R, R_EX, x_flange_ex_start, x_exit)
    all_parts.append(flange_ex)
    
    # 出口法兰8个M5螺栓孔
    for i in range(8):
        theta = math.radians(i * 45)
        by = (FLANGE_EX_R - 5) * math.cos(theta)
        bz = (FLANGE_EX_R - 5) * math.sin(theta)
        hole = make_cylinder(2.5, x_flange_ex_start - 5, x_exit + 5, seg=8)
        hole.apply_translation([0, by, bz])
        all_parts.append(hole)
    
    # 出口O型圈槽
    seal_ex = make_tube(FLANGE_EX_R - 4, FLANGE_EX_R - 8, x_exit - 5, x_exit - 1)
    all_parts.append(seal_ex)
    
    # 4条散热肋
    for ci in range(4):
        theta = math.radians(ci * 90)
        cy = (R_IN + W + 3) * math.cos(theta)
        cz = (R_IN + W + 3) * math.sin(theta)
        rib = make_tube(W * 0.6, W * 0.3, x_inlet + 20, x_exit - 15, seg=8)
        v = rib.vertices.copy()
        v[:, 1] += cy
        v[:, 2] += cz
        rib.vertices = v
        all_parts.append(rib)
    
    nozzle = trimesh.util.concatenate(all_parts)
    nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
    nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.glb"))
    b = nozzle.bounds
    print(f"  07 TVC喷管: X=[{b[0][0]:.0f},{b[1][0]:.0f}] 入Ø{FLANGE_IN_R*2:.0f} 喉Ø{R_TH*2:.0f} 出Ø{FLANGE_EX_R*2:.0f} L={x_inlet-x_exit:.0f}mm ✅")
    return nozzle

# ============================================================================
# 主程序
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Ad Astra 火箭 v7.0 [修复版] - 紧密连接验证")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    parts = []
    nose = build_nose(); parts.append(nose)
    body = build_body(); parts.append(body)
    fins = build_fins(); parts.append(fins)
    av = build_avionics(); parts.append(av)
    tvc = build_tvc_base(); parts.append(tvc)
    gim = build_gimbal(); parts.append(gim)
    nozzle = build_nozzle(); parts.append(nozzle)
    
    assembly = trimesh.util.concatenate(parts)
    assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.stl"))
    assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.glb"))
    
    b = assembly.bounds
    total_len = b[1][0] - b[0][0]
    print()
    print("=" * 70)
    print(f"✅ 完整装配体: X=[{b[0][0]:.0f}, {b[1][0]:.0f}] 总长 {total_len:.0f}mm")
    print(f"   面数: {len(assembly.faces):,}")
    print("=" * 70)
    
    # 验证连接
    print()
    print("🔍 连接验证:")
    print(f"  整流罩-机身: {nose.bounds[0][0]:.0f} ~ {body.bounds[1][0]:.0f} → 间隙 {abs(nose.bounds[0][0] - body.bounds[1][0]):.1f}mm")
    print(f"  机身-TVc: {body.bounds[0][0]:.0f} ~ {tvc.bounds[0][0]:.0f} → 间隙 {abs(tvc.bounds[0][0] - body.bounds[0][0]):.1f}mm")
    print(f"  TVC-万向节: {tvc.bounds[0][0]:.0f} ~ {gim.bounds[0][0]:.0f} → 间隙 {abs(gim.bounds[0][0] - tvc.bounds[0][0]):.1f}mm")
    print(f"  万向节-喷管: {gim.bounds[0][0]:.0f} ~ {nozzle.bounds[1][0]:.0f} → 间隙 {abs(gim.bounds[0][0] - nozzle.bounds[1][0]):.1f}mm")
    print()
    print("🌐 http://localhost:8000/viewer.html")
