#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v3.0
=============================================================================
设计原则:
  +X 轴 = 前进方向（火箭尖头在右边）
  YZ 平面 = 径向截面（圆形）
  所有零件沿 X 轴依次组装

零件顺序 (从右到左):
  01 整流罩 (nose cone)  -> 最右端
  02 机身管 (body tube)  -> 中间主体
    └ 尾翼 ×3 (fins)     -> 贴在机身管尾部
  03 TVC底座 (base)      -> 机身管与万向环之间
  04 TVC万向环 (gimbal)  -> 喷管与底座之间
  05 TVC喷管 (nozzle)    -> 最左端
=============================================================================
"""

import numpy as np
import trimesh
import os
import math
from datetime import datetime

# ============================================================================
# 参数表（所有尺寸: mm）
# ============================================================================
R = 37.5          # 机身半径
D = 75.0          # 机身直径
WALL = 2.5        # 默认壁厚

CONFIG = {
    "nose": {
        "length": 180.0,     # 整流罩长度（沿X轴）
        "base_r": R,         # 底部半径 = 机身半径
        "thickness": 2.0,
        "flange_length": 12.0,  # 插入机身的法兰
    },
    "body": {
        "length": 400.0,     # 机身管长度
        "outer_r": R,
        "inner_r": R - WALL,
        "wall": WALL,
        "ring_count": 3,     # 内部加强环数量
    },
    "fins": {
        "count": 3,
        "root_chord": 100.0,  # 根部弦长
        "tip_chord": 50.0,    # 尖部弦长
        "span": 50.0,         # 翼展（从机身表面向外）
        "thickness": 3.0,
    },
    "tvc_base": {
        "diameter": 90.0,
        "length": 30.0,
        "edf_inner_r": 32.0,  # EDF风扇内径（40mm风扇）
        "lug_count": 4,       # 固定耳数量
    },
    "tvc_gimbal": {
        "outer_r": 38.0,
        "ring_thickness": 8.0,
        "pivot_d": 6.0,       # 枢轴直径
        "servo_lug_size": 15.0,
    },
    "tvc_nozzle": {
        "inlet_d": 70.0,
        "throat_d": 38.0,      # 喉道直径
        "exit_d": 58.0,        # 出口直径
        "convergent_length": 35.0,
        "divergent_length": 55.0,
        "wall": 3.0,
    },
}

OUTPUT_DIR = r"D:\AI_rocket\3d_print_files"
SEG_CIRCLE = 64  # 圆形截面的段数

# ============================================================================
# 工具函数
# ============================================================================

def make_cylinder(radius, length, x_start=0, segments=SEG_CIRCLE):
    """创建一个圆柱，沿X轴方向，从x_start到x_start+length"""
    c = trimesh.creation.cylinder(radius=radius, height=length,
                                  sections=segments, segmented=False)
    # trimesh cylinder 默认沿 Z 轴，需要旋转到 X 轴
    c.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi/2, [0, 1, 0]))  # 绕Y轴转90度，使Z→X
    # 此时圆柱中心在原点，长度沿X轴
    c.apply_translation([x_start + length/2, 0, 0])
    return c

def make_hollow_tube(outer_r, inner_r, length, x_start=0, segments=SEG_CIRCLE):
    """创建空心圆管"""
    outer = make_cylinder(outer_r, length, x_start, segments)
    inner = make_cylinder(inner_r, length, x_start, segments)
    tube = outer.difference(inner)
    return tube

def revolve_profile(profile_xy, segments=SEG_CIRCLE):
    """
    绕 X 轴旋转生成 3D 模型
    profile_xy: [(x, r), (x, r), ...] 从尖端到底部的截面轮廓
                x 为沿轴坐标，r 为该位置的半径
    """
    # 生成绕 X 轴的旋转体（用 trimesh 的 revolve）
    profile = np.array(profile_xy, dtype=float)
    # trimesh.revolve 需要 2D 曲线，绕第一个轴旋转
    # 使用三角面片近似
    verts = []
    faces = []
    n = len(profile)
    for i, theta in enumerate(np.linspace(0, 2*np.pi, segments, endpoint=False)):
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        for j in range(n):
            x, r = profile[j]
            y = r * cos_t
            z = r * sin_t
            verts.append([x, y, z])
    verts.append([profile[-1][0], 0, 0])  # 底部中心（用于封口）
    verts.append([profile[0][0], 0, 0])   # 顶部中心（用于封口）
    idx_bottom = len(verts) - 2
    idx_top = len(verts) - 1

    # 侧面
    for i in range(segments):
        i2 = (i + 1) % segments
        for j in range(n - 1):
            v1 = i * n + j
            v2 = i * n + (j + 1)
            v3 = i2 * n + j
            v4 = i2 * n + (j + 1)
            faces.append([v1, v2, v4])
            faces.append([v1, v4, v3])

    # 底部封口
    for i in range(segments):
        i2 = (i + 1) % segments
        v1 = i * n + (n - 1)
        v2 = i2 * n + (n - 1)
        faces.append([v1, idx_bottom, v2])

    # 顶部封口
    for i in range(segments):
        i2 = (i + 1) % segments
        v1 = i * n
        v2 = i2 * n
        faces.append([v1, v2, idx_top])

    verts = np.array(verts, dtype=float)
    faces = np.array(faces, dtype=int)
    return trimesh.Trimesh(vertices=verts, faces=faces)

# ============================================================================
# 01. 整流罩 - Von Karman 曲线
# ============================================================================
def make_nose_cone():
    cfg = CONFIG["nose"]
    L = cfg["length"]
    Rb = cfg["base_r"]
    flange_len = cfg["flange_length"]

    # Von Karman 曲线: r(x) = Rb * sqrt(1 - (x/L)^2)^0.5
    # 但我们需要"尖头向右"，所以 x 从 0 (尖点) 到 L (底部)
    # 实际公式: r(x) = Rb * sqrt( (x/L) * (2 - x/L) )  -- Von Karman ogive
    # 简化: 使用幂律曲线，形状更自然
    n_points = 40
    profile = []
    for i in range(n_points):
        t = i / (n_points - 1)  # 0 = 尖点, 1 = 底部
        x = t * L               # x=0 在尖点, x=L 在底部
        # Von Karman ogive: r = Rb * sqrt(2*sigma*t - t^2), sigma=0.75
        sigma = 0.75
        r = Rb * math.sqrt(max(0, 2*sigma*t - t*t))
        # 在尖点添加很小的半径以避免零半径问题
        if r < 0.3:
            r = 0.3
        profile.append((x, r))  # x 从0到L（尖点在x=0）

    # 生成外壳（带一定厚度的实体）
    # 先生成实体再做一个略小的挖掉
    outer = revolve_profile(profile)
    # 内部轮廓（减厚度）
    inner_profile = []
    for i in range(n_points):
        x, r = profile[i]
        inner_r = r - cfg["thickness"]
        if inner_r < 0.5:
            inner_r = 0.5
        inner_profile.append((x + cfg["thickness"]*0.5, inner_r))
    inner = revolve_profile(inner_profile)
    nose = outer.difference(inner)

    # 在底部添加法兰（插入机身的部分）
    flange_r = Rb - 1.0  # 比机身略小，便于插入
    flange = make_cylinder(flange_r, flange_len, x_start=L)
    # 法兰稍微缩一点，与机身配合
    nose = trimesh.util.concatenate([nose, flange])

    nose.export(os.path.join(OUTPUT_DIR, "01_nose_cone.stl"))
    nose.export(os.path.join(OUTPUT_DIR, "01_nose_cone.glb"))
    print(f"   整流罩: x=0 ~ {L+flange_len:.0f}mm, 顶点数: {len(nose.vertices)}, 面数: {len(nose.faces)}")
    return nose, L + flange_len  # 返回零件和沿X轴占用长度


# ============================================================================
# 02. 机身管 - 空心圆柱 + 内部加强环
# ============================================================================
def make_body_tube(x_start=0):
    cfg = CONFIG["body"]
    L = cfg["length"]

    # 空心管
    tube = make_hollow_tube(cfg["outer_r"], cfg["inner_r"], L, x_start)

    # 内部加强环
    rings = []
    ring_positions = np.linspace(x_start + 50, x_start + L - 50, cfg["ring_count"])
    for rx in ring_positions:
        ring = make_cylinder(cfg["inner_r"] - 0.5, 5.0, x_start=rx - 2.5)
        inner_hole = make_cylinder(cfg["inner_r"] - 8.0, 5.2, x_start=rx - 2.6)
        ring = ring.difference(inner_hole)
        rings.append(ring)

    if rings:
        body = trimesh.util.concatenate([tube] + rings)
    else:
        body = tube

    body.export(os.path.join(OUTPUT_DIR, "02_body_tube.stl"))
    body.export(os.path.join(OUTPUT_DIR, "02_body_tube.glb"))
    print(f"   机身管: x={x_start:.0f} ~ {x_start+L:.0f}mm, 顶点数: {len(body.vertices)}, 面数: {len(body.faces)}")
    return body, L


# ============================================================================
# 03. 尾翼 - 3片，带翼型截面
# ============================================================================
def make_fins(x_start_body, body_length):
    cfg = CONFIG["fins"]
    fin_count = cfg["count"]
    RC = cfg["root_chord"]
    TC = cfg["tip_chord"]
    SP = cfg["span"]
    THICK = cfg["thickness"]

    # 尾翼位置：在机身管的尾端（x_start_body 到 x_start_body + body_length）
    # 尾翼的根部从距尾端 RC 的位置开始
    fin_root_start_x = x_start_body + body_length - RC  # 尾翼根部起点

    # 构建一片尾翼的形状（梯形翼型）
    # 根部弦长 RC，尖部弦长 TC，翼展 SP
    # 从机身表面 (r=R) 向外延伸 SP
    # 创建一个梯形轮廓作为基础

    # 尾翼的顶点（在 XY 平面，之后旋转到圆周位置）
    # 坐标: x = 沿机身方向, y = 从机身高出的径向距离
    # 前缘后掠：根部前缘 x=0, 尖部前缘 x = (RC-TC)/2 (后掠)
    # 简单梯形：后缘垂直
    leading_sweep = (RC - TC) / 2.0  # 后掠量

    # 创建尾翼的 2D 轮廓（在 X-Y 平面，Y 是径向向外）
    # 四个角:
    #   A = 根前缘 (x=fin_root_start_x, y=R)
    #   B = 根后缘 (x=fin_root_start_x+RC, y=R)
    #   C = 尖后缘 (x=fin_root_start_x+RC, y=R+SP)
    #   D = 尖前缘 (x=fin_root_start_x+leading_sweep, y=R+SP)

    A = [fin_root_start_x, R]
    B = [fin_root_start_x + RC, R]
    C = [fin_root_start_x + RC, R + SP]
    D = [fin_root_start_x + leading_sweep, R + SP]

    # 用挤出方式创建尾翼：在 X-Y 平面画多边形，沿 Z 方向挤出厚度
    # 然后整体旋转到圆周位置

    # 用简单的长方体近似（带后掠的楔形）
    fins_list = []
    for i in range(fin_count):
        angle = (i * 360.0 / fin_count)  # 度，尾翼沿圆周均布
        # 创建尾翼几何体：使用三角面片
        verts = []
        faces = []

        # 每个尾翼由 8 个顶点组成（两侧面各4个）
        # 厚度方向: 垂直于径向方向
        # 使用局部坐标系: u = 周向方向, v = 径向向外, w = 沿机身
        # 简化: 直接在全局坐标创建

        theta = math.radians(angle)
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        # 尾翼厚度方向（圆周切线方向）
        tangent_y = -sin_t
        tangent_z = cos_t

        half_t = THICK / 2.0

        # 8 个顶点: 在 A,B,C,D 基础上，±half_t 沿 tangent 方向
        for p in [A, B, C, D]:
            px, pr = p
            # 点在圆周上的 Y, Z 坐标 (pr 是径向距离)
            base_y = pr * cos_t
            base_z = pr * sin_t
            # 两个面（正面和背面）
            verts.append([px, base_y - tangent_y*half_t, base_z - tangent_z*half_t])
            verts.append([px, base_y + tangent_y*half_t, base_z + tangent_z*half_t])

        # index: A1=0, A2=1, B1=2, B2=3, C1=4, C2=5, D1=6, D2=7
        # 底部面 (root): A1, A2, B2, B1
        faces.append([0, 2, 3])
        faces.append([0, 3, 1])
        # 后缘面 (trailing edge): B1, B2, C2, C1
        faces.append([2, 4, 5])
        faces.append([2, 5, 3])
        # 尖端面 (tip): C1, C2, D2, D1
        faces.append([4, 6, 7])
        faces.append([4, 7, 5])
        # 前缘面 (leading edge): D1, D2, A2, A1
        faces.append([6, 0, 1])
        faces.append([6, 1, 7])
        # 侧面1: A1, D1, C1, B1
        faces.append([0, 6, 4])
        faces.append([0, 4, 2])
        # 侧面2: A2, B2, C2, D2
        faces.append([1, 3, 5])
        faces.append([1, 5, 7])

        verts = np.array(verts, dtype=float)
        faces = np.array(faces, dtype=int)
        fin = trimesh.Trimesh(vertices=verts, faces=faces)
        fins_list.append(fin)

    fins = trimesh.util.concatenate(fins_list)
    fins.export(os.path.join(OUTPUT_DIR, "03_fins_x3.stl"))
    fins.export(os.path.join(OUTPUT_DIR, "03_fins_x3.glb"))
    print(f"   尾翼 ×3: 翼展 {SP:.0f}mm, 根弦 {RC:.0f}mm, 后掠 {leading_sweep:.0f}mm")
    print(f"         位置: x={fin_root_start_x:.0f} ~ {fin_root_start_x+RC:.0f}mm")
    return fins


# ============================================================================
# 04. 航电舱 - 放在机身内部（可视化用）
# ============================================================================
def make_avionics_bay(x_start=0):
    cfg = {"diameter": 68.0, "length": 80.0, "wall": 2.0, "compartments": 2}
    R_av = cfg["diameter"] / 2
    L = cfg["length"]

    shell = make_hollow_tube(R_av, R_av - cfg["wall"], L, x_start)

    # 内部隔板
    partitions = []
    for i in range(1, cfg["compartments"]):
        px = x_start + (i * L / cfg["compartments"])
        part = make_cylinder(R_av - cfg["wall"] - 0.5, 3.0, x_start=px - 1.5)
        partitions.append(part)

    # 顶部盖板
    cap = make_cylinder(R_av - 0.5, 5.0, x_start=x_start + L)
    partitions.append(cap)

    avionics = trimesh.util.concatenate([shell] + partitions)
    avionics.export(os.path.join(OUTPUT_DIR, "04_avionics_bay.stl"))
    avionics.export(os.path.join(OUTPUT_DIR, "04_avionics_bay.glb"))
    print(f"   航电舱: 直径 {cfg['diameter']:.0f}mm, 长 {L:.0f}mm, x={x_start:.0f} ~ {x_start+L:.0f}mm")
    return avionics, L


# ============================================================================
# 05. TVC 底座
# ============================================================================
def make_tvc_base(x_start=0):
    cfg = CONFIG["tvc_base"]
    D_b = cfg["diameter"]
    R_b = D_b / 2
    L = cfg["length"]

    # 主底座圆盘
    base_main = make_hollow_tube(R_b, R_b - WALL, L, x_start)

    # EDF 风扇安装孔（中心通孔）
    edf_hole = make_cylinder(cfg["edf_inner_r"], L + 2, x_start=x_start - 1)
    base_main = base_main.difference(edf_hole)

    # 外侧的固定凸耳
    lugs = []
    for i in range(cfg["lug_count"]):
        theta = math.radians(i * 360.0 / cfg["lug_count"])
        # 小方块作为凸耳
        lug_r_out = R_b + 8.0
        # 使用 cylinder 作凸耳
        lug = trimesh.creation.box([L * 0.8, 16.0, 16.0])
        # 把凸耳放到正确的位置
        cx = x_start + L / 2
        cy = R_b * math.cos(theta) + (lug_r_out - R_b) / 2 * math.cos(theta)
        cz = R_b * math.sin(theta) + (lug_r_out - R_b) / 2 * math.sin(theta)
        lug.apply_translation([cx, cy, cz])
        lugs.append(lug)

    tvc_base = trimesh.util.concatenate([base_main] + lugs)
    tvc_base.export(os.path.join(OUTPUT_DIR, "05_tvc_base.stl"))
    tvc_base.export(os.path.join(OUTPUT_DIR, "05_tvc_base.glb"))
    print(f"   TVC底座: 直径 {D_b:.0f}mm, 长 {L:.0f}mm, x={x_start:.0f} ~ {x_start+L:.0f}mm")
    return tvc_base, L


# ============================================================================
# 06. TVC 万向环
# ============================================================================
def make_tvc_gimbal(x_start=0):
    cfg = CONFIG["tvc_gimbal"]
    R_out = cfg["outer_r"]
    T = cfg["ring_thickness"]
    L = T  # 环的"长度"就是它的厚度

    # 主环（空心圆环在 XY 平面，绕 X 轴为中心）
    # 简化: 用两个圆柱的差
    outer_ring = make_cylinder(R_out, L, x_start)
    inner_hole = make_cylinder(R_out - T, L, x_start)
    ring = outer_ring.difference(inner_hole)

    # 枢轴凸耳（Y 轴方向）
    pivot_ys = []
    pivot_r = cfg["pivot_d"] / 2
    for sign in [-1, 1]:
        # 枢轴 - 垂直于环的小圆柱
        pivot = trimesh.creation.cylinder(radius=pivot_r, height=15.0, sections=32)
        # pivot 默认沿 Z 轴，让它沿 Y 轴
        pivot.apply_transform(trimesh.transformations.rotation_matrix(
            np.pi/2, [1, 0, 0]))
        pivot.apply_translation([x_start + L/2, sign * (R_out + 5.0), 0])
        pivot_ys.append(pivot)

    # 舵机座凸耳（Z 轴方向）
    servo_lugs = []
    for sign in [-1, 1]:
        lug = trimesh.creation.box([T, 12.0, 15.0])
        lug.apply_translation([x_start + L/2, 0, sign * (R_out + 5.0)])
        servo_lugs.append(lug)

    gimbal = trimesh.util.concatenate([ring] + pivot_ys + servo_lugs)
    gimbal.export(os.path.join(OUTPUT_DIR, "06_tvc_gimbal.stl"))
    gimbal.export(os.path.join(OUTPUT_DIR, "06_tvc_gimbal.glb"))
    print(f"   TVC万向环: 外径 {R_out*2:.0f}mm, x={x_start:.0f} ~ {x_start+L:.0f}mm")
    return gimbal, L


# ============================================================================
# 07. TVC 喷管 - 收敛扩散喷管（入口大→喉道小→出口中）
# ============================================================================
def make_tvc_nozzle(x_start=0):
    """
    喷管外形:
      x = x_start                    -> 入口 (inlet)
      x = x_start + conv_len         -> 喉道 (throat)
      x = x_start + conv_len + div_len -> 出口 (exit)

    半径变化:
      inlet -> throat: 从 R_inlet 收敛到 R_throat
      throat -> exit:  从 R_throat 扩散到 R_exit
    """
    cfg = CONFIG["tvc_nozzle"]
    R_in = cfg["inlet_d"] / 2
    R_th = cfg["throat_d"] / 2
    R_ex = cfg["exit_d"] / 2
    L_c = cfg["convergent_length"]
    L_d = cfg["divergent_length"]
    L = L_c + L_d
    W = cfg["wall"]

    # 外壁轮廓
    outer_profile = []
    n_c = 20
    n_d = 30

    # 收敛段 (x_start -> x_start+L_c): 线性从 R_in+W 到 R_th+W
    for i in range(n_c):
        t = i / (n_c - 1)
        x = x_start + t * L_c
        r = (R_in + W) + t * ((R_th + W) - (R_in + W))
        outer_profile.append((x, r))

    # 扩散段 (x_start+L_c -> x_start+L_c+L_d): 曲线从 R_th+W 到 R_ex+W
    for i in range(1, n_d + 1):
        t = i / n_d
        x = x_start + L_c + t * L_d
        # 非线性扩散（更接近真实喷管）
        r = (R_th + W) + t*t * ((R_ex + W) - (R_th + W))
        outer_profile.append((x, r))

    # 内壁轮廓（向内偏移 W）
    inner_profile = []
    for i in range(n_c):
        t = i / (n_c - 1)
        x = x_start + t * L_c
        r = R_in + t * (R_th - R_in)
        inner_profile.append((x, max(r, 1.0)))

    for i in range(1, n_d + 1):
        t = i / n_d
        x = x_start + L_c + t * L_d
        r = R_th + t*t * (R_ex - R_th)
        inner_profile.append((x, max(r, 1.0)))

    # 生成实体
    outer = revolve_profile(outer_profile)
    inner = revolve_profile(inner_profile)
    nozzle = outer.difference(inner)

    nozzle.export(os.path.join(OUTPUT_DIR, "07_tvc_nozzle.stl"))
    nozzle.export(os.path.join(OUTPUT_DIR, "07_tvc_nozzle.glb"))
    print(f"   TVC喷管: 入口 {R_in*2:.0f}mm -> 喉道 {R_th*2:.0f}mm -> 出口 {R_ex*2:.0f}mm")
    print(f"         总长 {L:.0f}mm, x={x_start:.0f} ~ {x_start+L:.0f}mm")
    return nozzle, L


# ============================================================================
# 主程序 - 生成并组装
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Ad Astra 火箭 - 3D 零件生成器 v3.0")
    print("=" * 70)
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 组装顺序: 从右(尖头)到左(喷管) ---
    # x 坐标: 最大值在最右边(整流罩尖点), 最小值在最左边(喷管出口)

    print("🔴 01. 生成整流罩...")
    nose, nose_len = make_nose_cone()
    # 整流罩: x=0 在尖点, x=nose_len 在底部法兰端

    # 机身管起点: 与整流罩底部连接（法兰插入机身）
    # 让机身从 x = nose_len - flange_overlap 开始，向右延伸为负值方向
    # 等等，我想让尖点在右边 (+X 方向)
    # 所以: 整流罩尖点在最右边，机身管在其左边
    # 实际上我的 current nose 生成: x=0 是尖点，x=nose_len 是底部
    # 这意味着"机身管应该在 x>nose_len" 才能在底部之后
    # 但这让"尖点在 x=0"，左边是机身... 不对！
    # 让我翻转: 尖点应该在 +X（右边），机身应该在尖点左侧（x更小的位置）
    # 所以: 先让 nose 生成时 x=0 是底部，x=nose_len 是尖点
    # 这样 nose 的范围是 0 ~ nose_len，尖点在 nose_len（右边）
    # 机身管应该在 nose 的左边（x<0 的区域）

    # 修正：我需要翻转 nose 的坐标系
    # 让我重新定义: 为了简化，我翻转坐标系再生成

    # 重新设计: 让我用统一坐标系
    #   NOSE_MAX = 最右端 (整流罩尖点)
    #   零件依次从 NOSE_MAX 往 -X 方向（向左）延伸
    #   这样尖点 = 最右边, 喷管 = 最左边 (Three.js 中)

    print("\n🔵 02. 生成机身管...")
    # 机身位置: x = -body_length 到 x = 0
    # 然后整流罩在 x = 0 到 x = nose_len（但要反向让尖点在+X）
    # 简化: 让我先生成各零件，之后整体平移
    body, body_len = make_body_tube(x_start=0)
    # body 现在在 x=0 到 x=body_len，需要翻转到 x=-body_len 到 x=0
    body.apply_translation([-body_len, 0, 0])
    # 现在 body: x = -body_len ~ 0

    print("\n🟠 03. 生成尾翼...")
    # 尾翼附着在机身尾部（x = -body_len 到 x = 0 的最左端区域）
    # make_fins 需要知道机身的原始 x_start 和 length
    # 让我重新设计: 直接用翻转后的坐标
    # 机身翻转后的范围: x=-body_len 到 x=0，尾端在 x=-body_len 附近
    # 尾翼根部起点: x = -body_len + (body_len - fin_root_chord) 是错的
    # 正确: 尾翼应该在机身尾部（接近 TVC 的一端 = -body_len 端）
    # 尾翼根部弦长 RC，所以起点应该是 x = -body_len + (从尾部算起的位置)
    # 让尾翼从机身尾部开始往前一小段，弦长 RC
    # 在翻转坐标系: 机身处 x = -body_len ~ 0
    # 尾翼根部位置: 从尾部 (x=-body_len) 往前 RC 长度
    # 即: fin_root_x_start = -body_len + small_margin
    # fin_root_x_end = -body_len + small_margin + RC
    # 但 make_fins 需要原始坐标系参数...让我简化

    # 为了避免坐标混乱，让我重新生成尾翼，使用翻转后的坐标系
    fins_angle = CONFIG["fins"]
    RC_f = fins_angle["root_chord"]
    TC_f = fins_angle["tip_chord"]
    SP_f = fins_angle["span"]
    THICK_f = fins_angle["thickness"]
    sweep_f = (RC_f - TC_f) / 2.0

    # 机身尾部位置: x = -body_len (最左端)
    # 让尾翼从 x = -body_len + 10 开始，向后（朝+X方向）延伸 RC_f
    fin_root_x = -body_len + 10
    # 尾翼的前缘和后缘
    # 根前缘: fin_root_x + sweep_f
    # 根后缘: fin_root_x + RC_f
    # 尖前缘: fin_root_x (这不对，需要重新考虑)

    # 简化尾翼: 根部从 x=fin_root_x 到 x=fin_root_x+RC_f（沿机身）
    # 根部贴在机身表面 (y,z 圆周位置)
    # 尖部比根部短 TC_f，且有后掠 sweep_f
    # 尖部前缘: x = fin_root_x + sweep_f, 尖部后缘: x = fin_root_x + sweep_f + TC_f
    # 但通常: 根部后缘在 x=fin_root_x+RC_f，尖部后缘也在同样位置（后缘垂直）
    # 尖部前缘: x = fin_root_x + RC_f - TC_f + sweep_offset? 让我简化

    # 简化版尾翼: 无后掠的对称梯形
    A = [fin_root_x, R]                           # 根前缘
    B = [fin_root_x + RC_f, R]                    # 根后缘
    C = [fin_root_x + RC_f, R + SP_f]             # 尖后缘
    D = [fin_root_x + (RC_f - TC_f), R + SP_f]    # 尖前缘（后掠）

    fins_list = []
    for i in range(3):
        angle_rad = math.radians(i * 120.0)
        cos_t, sin_t = math.cos(angle_rad), math.sin(angle_rad)
        tangent_y, tangent_z = -sin_t, cos_t
        half_t = THICK_f / 2.0

        verts = []
        for p in [A, B, C, D]:
            px, pr = p
            base_y = pr * cos_t
            base_z = pr * sin_t
            verts.append([px, base_y - tangent_y*half_t, base_z - tangent_z*half_t])
            verts.append([px, base_y + tangent_y*half_t, base_z + tangent_z*half_t])

        faces = []
        # 根部面
        faces.append([0, 2, 3])
        faces.append([0, 3, 1])
        # 后缘面
        faces.append([2, 4, 5])
        faces.append([2, 5, 3])
        # 尖部面
        faces.append([4, 6, 7])
        faces.append([4, 7, 5])
        # 前缘面
        faces.append([6, 0, 1])
        faces.append([6, 1, 7])
        # 侧面1
        faces.append([0, 6, 4])
        faces.append([0, 4, 2])
        # 侧面2
        faces.append([1, 3, 5])
        faces.append([1, 5, 7])

        verts = np.array(verts, dtype=float)
        faces = np.array(faces, dtype=int)
        fins_list.append(trimesh.Trimesh(vertices=verts, faces=faces))

    fins_v3 = trimesh.util.concatenate(fins_list)
    fins_v3.export(os.path.join(OUTPUT_DIR, "03_fins_x3.stl"))
    fins_v3.export(os.path.join(OUTPUT_DIR, "03_fins_x3.glb"))
    print(f"   尾翼位置: x={fin_root_x:.0f} ~ {fin_root_x+RC_f:.0f}mm")

    print("\n🟢 04. 生成航电舱...")
    # 航电舱放在机身内部前端（x = -body_len + 50 左右，朝 +X 方向）
    av_x = -body_len + 200  # 放在机身内部靠前位置
    avionics, av_len = make_avionics_bay(x_start=av_x)

    print("\n🟣 05. 生成 TVC 底座...")
    # TVC 底座: 机身尾部之后（x = -body_len 的左侧，即更负的x）
    tvc_base_x = -body_len
    tvc_base, tvc_b_len = make_tvc_base(x_start=tvc_base_x)

    print("\n🟡 06. 生成 TVC 万向环...")
    tvc_gimbal_x = tvc_base_x - CONFIG["tvc_gimbal"]["ring_thickness"] - 2
    # 修正：万向环应该紧贴 TVC 底座
    tvc_gimbal_x = tvc_base_x - 2  # 让它从 TVC 底座内部开始一点点
    gimbal, gimbal_len = make_tvc_gimbal(x_start=tvc_gimbal_x - gimbal_len/2)

    print("\n🔵 07. 生成 TVC 喷管...")
    # 喷管: 在万向环之后（更左边）
    nozzle_x = tvc_gimbal_x - gimbal_len - 5  # 留出间隙
    nozzle, nozzle_len = make_tvc_nozzle(x_start=nozzle_x)

    # --- 翻转整流罩: 让它尖点在 +X ---
    # 当前 nose: x=0 是尖点, x=nose_len 是底部
    # 需要: 尖点在 +X 方向（最大 x 值）
    # 方案: 翻转 nose（x → -x + nose_len），让底部在 x=0，尖点在 x=nose_len
    # 然后把 nose 整体平移到机身的右端（x=0 处），这样 nose 范围是 0 ~ nose_len
    # 但机身当前是 -body_len ~ 0，所以 nose 在 0 ~ nose_len 是正确的
    # 即 nose 的底部在 x=0，与机身的 x=0 端相连

    # 翻转: 先翻转坐标 (x → -x)，这样 nose 从 [-nose_len, 0]，尖点在 -nose_len
    # 不对，让我重新生成 nose 时直接控制方向
    # 在 make_nose_cone 中，x=0 是尖点，x=nose_len 是底部
    # 要让尖点在 +X（右边），需要: 底部在 x=0, 尖点在 x=nose_len
    # 即: 对每个顶点做 x → nose_len - x
    flip_matrix = np.eye(4)
    flip_matrix[0, 0] = -1  # 翻转 X 轴
    flip_matrix[0, 3] = nose_len  # 平移，使 x=0 → nose_len, x=nose_len → 0
    nose.apply_transform(flip_matrix)
    # 现在 nose: 尖点在 x=nose_len（右边），底部在 x=0，刚好与机身的 x=0 端相接

    # 修正: 需要确认 nose 的底部与机身的 x=0 端匹配
    # 机身外径 R=37.5mm，nose 底部半径=37.5mm，所以直径匹配 ✓

    print("\n🚀 08. 组装完整火箭...")
    # 完整装配体 - 收集所有零件
    all_parts = [nose, body, fins_v3, avionics, tvc_base, gimbal, nozzle]
    assembly = trimesh.util.concatenate(all_parts)

    assembly.export(os.path.join(OUTPUT_DIR, "08_full_rocket_assembly.stl"))
    assembly.export(os.path.join(OUTPUT_DIR, "08_full_rocket_assembly.glb"))

    # 计算总长度
    all_x = []
    for mesh in all_parts:
        all_x.extend(mesh.bounds[:, 0].tolist())
    x_min = min(all_x)
    x_max = max(all_x)
    total_len = x_max - x_min

    print(f"\n   火箭总长度: {total_len:.0f}mm (x={x_min:.0f} ~ {x_max:.0f})")
    print(f"   整流罩: x=0 ~ {nose_len:.0f}mm (尖点在右边)")
    print(f"   机身管: x={-body_len:.0f} ~ 0mm")
    print(f"   TVC底座: x={tvc_base_x:.0f} ~ {tvc_base_x+tvc_b_len:.0f}mm")
    print(f"   喷管: x={nozzle_x:.0f} ~ {nozzle_x+nozzle_len:.0f}mm (出口在左边)")
    print(f"   总面数: {len(assembly.faces):,}")

    print("\n" + "=" * 70)
    print("✅ 所有零件生成完成！")
    print("=" * 70)
    print(f"\n📁 输出目录: {OUTPUT_DIR}")
    print(f"\n🌐 查看: http://localhost:8000/viewer.html")
    print("=" * 70)
