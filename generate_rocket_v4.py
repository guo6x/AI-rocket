#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🚀 Ad Astra 火箭 - 3D 零件生成器 v4.0 (纯几何构建, 无布尔运算)
=============================================================================
坐标系约定:
  +X 轴 = 前进方向 (火箭尖头指向 +X, 在Three.js中显示在右侧)
  Y,Z 轴 = 径向 (圆形截面)
  所有零件沿 X 轴组装

组装顺序 (从右到左):
  [尖点] +X -- 整流罩 -- 机身管 + 尾翼 -- TVC底座 -- 万向环 -- 喷管 -- -X [出口]
=============================================================================
"""
import numpy as np
import trimesh
import os
import math
from datetime import datetime

# ============================================================
# 参数表
# ============================================================
BODY_R = 37.5            # 机身半径 mm
WALL_T = 2.5              # 默认壁厚
OUTPUT_DIR = r"D:\AI_rocket\3d_print_files"
SEG = 48                  # 圆形截面的分段数

CONFIG = {
    "nose":      {"length": 180.0, "flange": 15.0, "thickness": 2.0},
    "body":      {"length": 400.0, "wall": WALL_T},
    "fin":       {"root_chord": 100, "tip_chord": 50, "span": 50, "thickness": 3, "count": 3},
    "avionics":  {"diameter": 68.0, "length": 80.0, "wall": 2.0},
    "tvc_base":  {"diameter": 90.0, "length": 30.0, "edf_d": 64.0},
    "gimbal":    {"outer_d": 76.0, "thickness": 8.0, "pivot_d": 6.0},
    "nozzle":    {"inlet_d": 70, "throat_d": 38, "exit_d": 58,
                  "conv_len": 35, "div_len": 55, "wall": 3.0},
}

# ============================================================
# 核心几何工具
# ============================================================
def build_cylinder_surface(radius, length, x_start=0, segments=SEG,
                           closed=True, inner_radius=0):
    """
    构建空心圆柱 (沿 X 轴方向, 从 x_start 到 x_start+length)
    closed=True: 两端封口 (变成实心圆柱)
    inner_radius>0: 空心, 有内表面
    """
    verts = []
    faces = []
    v0 = 0  # 当前顶点索引偏移

    if inner_radius > 0 and inner_radius < radius:
        # --- 空心管 ---
        # 外表面
        outer_start = v0
        for j, theta in enumerate(np.linspace(0, 2*np.pi, segments, endpoint=False)):
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            verts.append([x_start, radius*cos_t, radius*sin_t])
            verts.append([x_start+length, radius*cos_t, radius*sin_t])
        v0 = len(verts)
        for j in range(segments):
            j2 = (j+1) % segments
            a, b = outer_start + 2*j, outer_start + 2*j + 1
            c, d = outer_start + 2*j2, outer_start + 2*j2 + 1
            faces.append([a, c, d])
            faces.append([a, d, b])

        # 内表面
        inner_start = v0
        for j, theta in enumerate(np.linspace(0, 2*np.pi, segments, endpoint=False)):
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            verts.append([x_start, inner_radius*cos_t, inner_radius*sin_t])
            verts.append([x_start+length, inner_radius*cos_t, inner_radius*sin_t])
        v0 = len(verts)
        for j in range(segments):
            j2 = (j+1) % segments
            a, b = inner_start + 2*j, inner_start + 2*j + 1
            c, d = inner_start + 2*j2, inner_start + 2*j2 + 1
            faces.append([a, b, d])  # 反向, 使法线朝内
            faces.append([a, d, c])

        # 左端环封口 (x=x_start)
        for j in range(segments):
            j2 = (j+1) % segments
            outer_pt = outer_start + 2*j      # 外圈左端
            outer_next = outer_start + 2*j2   # 外圈下一个左端
            inner_pt = inner_start + 2*j      # 内圈左端
            inner_next = inner_start + 2*j2   # 内圈下一个左端
            faces.append([outer_pt, inner_pt, inner_next])
            faces.append([outer_pt, inner_next, outer_next])

        # 右端环封口 (x=x_start+length)
        for j in range(segments):
            j2 = (j+1) % segments
            outer_pt = outer_start + 2*j + 1
            outer_next = outer_start + 2*j2 + 1
            inner_pt = inner_start + 2*j + 1
            inner_next = inner_start + 2*j2 + 1
            faces.append([outer_pt, outer_next, inner_next])
            faces.append([outer_pt, inner_next, inner_pt])

    elif closed:
        # --- 实心圆柱 (带两端封口) ---
        side_start = v0
        # 侧面顶点
        for j, theta in enumerate(np.linspace(0, 2*np.pi, segments, endpoint=False)):
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            verts.append([x_start, radius*cos_t, radius*sin_t])
            verts.append([x_start+length, radius*cos_t, radius*sin_t])
        v0 = len(verts)
        # 侧面三角
        for j in range(segments):
            j2 = (j+1) % segments
            a, b = side_start + 2*j, side_start + 2*j + 1
            c, d = side_start + 2*j2, side_start + 2*j2 + 1
            faces.append([a, c, d])
            faces.append([a, d, b])
        # 左端圆心
        verts.append([x_start, 0, 0])
        center_left = len(verts) - 1
        for j in range(segments):
            j2 = (j+1) % segments
            faces.append([center_left, side_start + 2*j, side_start + 2*j2])
        # 右端圆心
        verts.append([x_start+length, 0, 0])
        center_right = len(verts) - 1
        for j in range(segments):
            j2 = (j+1) % segments
            faces.append([center_right, side_start + 2*j2 + 1, side_start + 2*j + 1])

    else:
        # --- 仅外表面 (不封口) ---
        side_start = v0
        for j, theta in enumerate(np.linspace(0, 2*np.pi, segments, endpoint=False)):
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            verts.append([x_start, radius*cos_t, radius*sin_t])
            verts.append([x_start+length, radius*cos_t, radius*sin_t])
        v0 = len(verts)
        for j in range(segments):
            j2 = (j+1) % segments
            a, b = side_start + 2*j, side_start + 2*j + 1
            c, d = side_start + 2*j2, side_start + 2*j2 + 1
            faces.append([a, c, d])
            faces.append([a, d, b])

    return trimesh.Trimesh(vertices=np.array(verts, dtype=float),
                           faces=np.array(faces, dtype=int))


def build_revolve_shell(profile_outer, profile_inner, segments=SEG):
    """
    旋转体外壳: 外轮廓和内轮廓之间的壁
    profile: [(x, r), ...] 从尖点到底部
    """
    verts = []
    faces = []

    def add_profile(profile):
        """添加一个轮廓的圆周顶点"""
        start_idx = len(verts)
        n = len(profile)
        for theta in np.linspace(0, 2*np.pi, segments, endpoint=False):
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            for xi, ri in profile:
                if ri < 0.01:
                    ri = 0.01
                verts.append([xi, ri*cos_t, ri*sin_t])
        return start_idx, n

    # 外表面
    out_start, n_pts = add_profile(profile_outer)
    for j in range(segments):
        j2 = (j+1) % segments
        for k in range(n_pts - 1):
            a = out_start + j*n_pts + k
            b = out_start + j*n_pts + (k+1)
            c = out_start + j2*n_pts + k
            d = out_start + j2*n_pts + (k+1)
            faces.append([a, c, d])
            faces.append([a, d, b])

    # 内表面
    in_start, _ = add_profile(profile_inner)
    for j in range(segments):
        j2 = (j+1) % segments
        for k in range(n_pts - 1):
            a = in_start + j*n_pts + k
            b = in_start + j*n_pts + (k+1)
            c = in_start + j2*n_pts + k
            d = in_start + j2*n_pts + (k+1)
            faces.append([a, b, d])
            faces.append([a, d, c])

    # 底部环封口 (两个轮廓的最后一个点构成环)
    for j in range(segments):
        j2 = (j+1) % segments
        out_a = out_start + j*n_pts + (n_pts - 1)
        out_b = out_start + j2*n_pts + (n_pts - 1)
        in_a = in_start + j*n_pts + (n_pts - 1)
        in_b = in_start + j2*n_pts + (n_pts - 1)
        faces.append([out_a, out_b, in_b])
        faces.append([out_a, in_b, in_a])

    # 尖部封口 (第一个点构成一个小圆)
    for j in range(segments):
        j2 = (j+1) % segments
        out_a = out_start + j*n_pts
        out_b = out_start + j2*n_pts
        in_a = in_start + j*n_pts
        in_b = in_start + j2*n_pts
        faces.append([out_a, in_a, in_b])
        faces.append([out_a, in_b, out_b])

    return trimesh.Trimesh(vertices=np.array(verts, dtype=float),
                           faces=np.array(faces, dtype=int))


# ============================================================
# 01. 整流罩 (Nose Cone)
# ============================================================
def build_nose(x_base=0):
    """
    整流罩: 底部在 x = x_base, 尖点在 x = x_base + length (+X 方向)
    """
    cfg = CONFIG["nose"]
    L = cfg["length"]
    flange = cfg["flange"]
    thk = cfg["thickness"]

    # Von Karman 曲线
    n_pts = 30
    profile_o = []  # 外轮廓
    profile_i = []  # 内轮廓
    for k in range(n_pts):
        t = k / (n_pts - 1)  # t=0 尖点, t=1 底部
        sigma = 0.8
        r_o = BODY_R * math.sqrt(max(0.001, 2*sigma*t - t*t))
        x = x_base + (1 - t) * L  # 尖点在 x_base + L, 底部在 x_base

        # 内轮廓 (壁厚偏移)
        # 计算径向斜率
        if t < 0.01:
            r_i = max(0.2, r_o - thk*1.5)
        else:
            r_i = max(0.5, r_o - thk)
        profile_o.append((x, r_o))
        profile_i.append((x + thk*0.3, r_i))

    # 构建旋转壳
    shell = build_revolve_shell(profile_o, profile_i)

    # 添加法兰 (底部插入机身的部分)
    flange_r = BODY_R - 2.0
    flange_mesh = build_cylinder_surface(flange_r, flange,
                                         x_start=x_base - flange,
                                         segments=SEG, closed=True)
    nose = trimesh.util.concatenate([shell, flange_mesh])

    nose.export(os.path.join(OUTPUT_DIR, "01_nose_cone.stl"))
    nose.export(os.path.join(OUTPUT_DIR, "01_nose_cone.glb"))
    tip_x = x_base + L
    print(f"  ✅ 整流罩: 尖点 x={tip_x:.0f}mm, 底部 x={x_base:.0f}mm, 总长 {L:.0f}mm")
    return nose


# ============================================================
# 02. 机身管 (Body Tube)
# ============================================================
def build_body(x_start, length):
    """
    机身管: 从 x_start 到 x_start + length (朝 +X 方向延伸)
    注意: 机身应该在整流罩的左边 (更小的 x 值), 所以 x_start 应该是负值
    """
    cfg = CONFIG["body"]
    inner_r = BODY_R - cfg["wall"]
    tube = build_cylinder_surface(BODY_R, length, x_start=x_start,
                                  segments=SEG, closed=False,
                                  inner_radius=inner_r)

    tube.export(os.path.join(OUTPUT_DIR, "02_body_tube.stl"))
    tube.export(os.path.join(OUTPUT_DIR, "02_body_tube.glb"))
    print(f"  ✅ 机身管: x={x_start:.0f} ~ {x_start+length:.0f}mm, 直径 {BODY_R*2:.0f}mm")
    return tube


# ============================================================
# 03. 尾翼 (Fins)
# ============================================================
def build_fins(body_x_start, body_length):
    """
    尾翼: 3 片, 贴在机身尾部
    body_x_start: 机身左端的 x 坐标 (较小值, 因为朝 -X)
    body_length: 机身长度
    尾翼应该在机身的左端区域 (接近 TVC 的一端)
    """
    cfg = CONFIG["fin"]
    RC, TC, SP, TH = cfg["root_chord"], cfg["tip_chord"], cfg["span"], cfg["thickness"]
    n_fins = cfg["count"]

    # 尾翼位置: 根部从机身左端 (x=body_x_start) 开始, 向右 (朝 +X) 延伸 RC
    # 后缘垂直, 前缘有后掠
    fin_root_x0 = body_x_start + 5  # 留出5mm间隙
    leading_sweep = (RC - TC) / 2.0

    # 尾翼 4 个角 (2D 轮廓, y = 径向高度, x = 轴向位置)
    # A: 根前缘, B: 根后缘, C: 尖后缘, D: 尖前缘
    A_2d = [fin_root_x0, BODY_R]
    B_2d = [fin_root_x0 + RC, BODY_R]
    C_2d = [fin_root_x0 + RC, BODY_R + SP]
    D_2d = [fin_root_x0 + leading_sweep, BODY_R + SP]

    fins_list = []
    for fin_idx in range(n_fins):
        theta = math.radians(fin_idx * 360.0 / n_fins)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        # 切线方向 (尾翼厚度方向, 垂直于径向)
        tan_y = -sin_t
        tan_z = cos_t
        half_t = TH / 2.0

        # 8 个顶点 (4 个角 × 2 个面)
        verts8 = []
        for px, pr in [A_2d, B_2d, C_2d, D_2d]:
            base_y, base_z = pr*cos_t, pr*sin_t
            # 底面 (朝 -切线)
            verts8.append([px, base_y - tan_y*half_t, base_z - tan_z*half_t])
            # 顶面 (朝 +切线)
            verts8.append([px, base_y + tan_y*half_t, base_z + tan_z*half_t])

        # 24 个三角面
        # A1=0, A2=1, B1=2, B2=3, C1=4, C2=5, D1=6, D2=7
        faces_f = [
            # 根部面 (连接机身)
            [0, 2, 3], [0, 3, 1],
            # 后缘面
            [2, 4, 5], [2, 5, 3],
            # 尖部面
            [4, 6, 7], [4, 7, 5],
            # 前缘面
            [6, 0, 1], [6, 1, 7],
            # 侧面1
            [0, 6, 4], [0, 4, 2],
            # 侧面2
            [1, 3, 5], [1, 5, 7],
        ]
        fin = trimesh.Trimesh(vertices=np.array(verts8, dtype=float),
                               faces=np.array(faces_f, dtype=int))
        fins_list.append(fin)

    fins = trimesh.util.concatenate(fins_list)
    fins.export(os.path.join(OUTPUT_DIR, "03_fins_x3.stl"))
    fins.export(os.path.join(OUTPUT_DIR, "03_fins_x3.glb"))
    print(f"  ✅ 尾翼 ×3: 翼展 {SP:.0f}mm, 根弦 {RC:.0f}mm, 位置 x={fin_root_x0:.0f} ~ {fin_root_x0+RC:.0f}mm")
    return fins


# ============================================================
# 04. 航电舱 (Avionics Bay)
# ============================================================
def build_avionics(x_start):
    cfg = CONFIG["avionics"]
    R_av = cfg["diameter"] / 2
    L = cfg["length"]
    wall = cfg["wall"]
    shell = build_cylinder_surface(R_av, L, x_start=x_start,
                                    segments=SEG, closed=False,
                                    inner_radius=R_av - wall)
    # 端部封口盘
    cap_left = build_cylinder_surface(R_av - wall, 4,
                                       x_start=x_start,
                                       segments=SEG, closed=True)
    cap_right = build_cylinder_surface(R_av - wall, 4,
                                        x_start=x_start + L - 4,
                                        segments=SEG, closed=True)
    # 中间隔板
    mid = build_cylinder_surface(R_av - wall, 3,
                                  x_start=x_start + L/2 - 1.5,
                                  segments=SEG, closed=True)

    avionics = trimesh.util.concatenate([shell, cap_left, cap_right, mid])
    avionics.export(os.path.join(OUTPUT_DIR, "04_avionics_bay.stl"))
    avionics.export(os.path.join(OUTPUT_DIR, "04_avionics_bay.glb"))
    print(f"  ✅ 航电舱: 直径 {cfg['diameter']:.0f}mm, 长 {L:.0f}mm, x={x_start:.0f} ~ {x_start+L:.0f}mm")
    return avionics


# ============================================================
# 05. TVC 底座 (TVC Base)
# ============================================================
def build_tvc_base(x_start):
    cfg = CONFIG["tvc_base"]
    R_b = cfg["diameter"] / 2
    L = cfg["length"]
    edf_r = cfg["edf_d"] / 2

    # 外壳 (空心圆柱)
    shell = build_cylinder_surface(R_b, L, x_start=x_start,
                                    segments=SEG, closed=False,
                                    inner_radius=edf_r)
    # 左端面盘 (x=x_start, 喷管侧)
    left_cap = build_cylinder_surface(R_b - 0.5, 4, x_start=x_start,
                                       segments=SEG, closed=True)
    # 右端面盘 (x=x_start+L, 机身侧)
    right_cap = build_cylinder_surface(R_b - 0.5, 4, x_start=x_start+L-4,
                                        segments=SEG, closed=True)

    # 固定凸耳 (4 个径向小凸耳, 简化的长方体突起)
    lugs = []
    for i in range(4):
        theta = math.radians(i * 90.0 + 45)
        dir_y = math.cos(theta)
        dir_z = math.sin(theta)
        # 小凸耳: 半径8mm, 沿机身轴向厚15mm, 径向突出20mm
        lug_r = 7.0
        lug_thickness = 15.0
        lug_protrusion = 25.0
        # 凸耳沿X方向厚15mm, 在YZ平面的径向位置: R_b ~ R_b+lug_protrusion
        # 圆柱轴向沿Y或Z(取决于theta), 但为了简化, 用沿X的圆柱
        lug = build_cylinder_surface(lug_r, lug_thickness,
                                      x_start=x_start + L/2 - lug_thickness/2,
                                      segments=14, closed=True)
        # 在 YZ 平面移动到机身外侧
        verts = lug.vertices.copy()
        offset_y = dir_y * (R_b + lug_protrusion / 2)
        offset_z = dir_z * (R_b + lug_protrusion / 2)
        verts[:, 1] += offset_y
        verts[:, 2] += offset_z
        lug.vertices = verts
        lugs.append(lug)

    base = trimesh.util.concatenate([shell, left_cap, right_cap] + lugs)
    base.export(os.path.join(OUTPUT_DIR, "05_tvc_base.stl"))
    base.export(os.path.join(OUTPUT_DIR, "05_tvc_base.glb"))
    print(f"  ✅ TVC底座: 直径 {R_b*2:.0f}mm, 长 {L:.0f}mm, x={x_start:.0f} ~ {x_start+L:.0f}mm")
    return base


# ============================================================
# 06. TVC 万向环 (Gimbal Ring)
# ============================================================
def build_gimbal(x_center):
    cfg = CONFIG["gimbal"]
    R_out = cfg["outer_d"] / 2
    T = cfg["thickness"]
    L_ring = T * 1.5

    # 主环: 空心圆柱(沿X方向)
    ring = build_cylinder_surface(R_out, L_ring,
                                   x_start=x_center - L_ring/2,
                                   segments=SEG, closed=False,
                                   inner_radius=R_out - T)

    # 枢轴 (在 Y 轴方向的小圆柱) - 直接顶点操作
    pivots = []
    pivot_r = cfg["pivot_d"] / 2
    pivot_len = 22.0
    for sign in [-1, 1]:
        # 先在原点附近创建沿X的圆柱
        pv = build_cylinder_surface(pivot_r, pivot_len,
                                     x_start=-pivot_len/2,
                                     segments=16, closed=True)
        # 手动绕 Z 轴旋转 90 度, 然后平移
        # 旋转: (x, y, z) -> (-y, x, z), 使圆柱沿 Y 方向
        verts = pv.vertices.copy()
        new = np.zeros_like(verts)
        new[:, 0] = x_center            # X = 环中心位置
        new[:, 1] = verts[:, 0] + sign * (R_out + pivot_len/2)  # Y = 原X + 偏移
        new[:, 2] = verts[:, 2]         # Z 不变
        pv.vertices = new
        pivots.append(pv)

    # 舵机座 (在 Z 轴方向的小圆柱)
    servo_lugs = []
    for sign in [-1, 1]:
        lug = build_cylinder_surface(pivot_r, pivot_len,
                                      x_start=-pivot_len/2,
                                      segments=16, closed=True)
        # 绕 Y 轴旋转 -90 度: (x, y, z) -> (z, y, -x)
        verts = lug.vertices.copy()
        new = np.zeros_like(verts)
        new[:, 0] = x_center
        new[:, 1] = verts[:, 1]
        new[:, 2] = -verts[:, 0] + sign * (R_out + pivot_len/2)
        lug.vertices = new
        servo_lugs.append(lug)

    gimbal = trimesh.util.concatenate([ring] + pivots + servo_lugs)
    gimbal.export(os.path.join(OUTPUT_DIR, "06_tvc_gimbal.stl"))
    gimbal.export(os.path.join(OUTPUT_DIR, "06_tvc_gimbal.glb"))
    print(f"  ✅ TVC万向环: 中心 x={x_center:.0f}mm, 外径 {R_out*2:.0f}mm")
    return gimbal


# ============================================================
# 07. TVC 喷管 (Nozzle) - 收敛扩散
# ============================================================
def build_nozzle(x_inlet):
    """
    喷管: 入口在 x=x_inlet (靠近 TVC 底座/机身的一端)
    向 -X 方向延伸, 出口在最左边
    入口 → 喉道 → 出口
    """
    cfg = CONFIG["nozzle"]
    R_in = cfg["inlet_d"] / 2
    R_th = cfg["throat_d"] / 2
    R_ex = cfg["exit_d"] / 2
    L_c = cfg["conv_len"]     # 收敛段 (入口 → 喉道)
    L_d = cfg["div_len"]      # 扩散段 (喉道 → 出口)
    W = cfg["wall"]

    # 坐标系:
    #   入口 (inlet):  x = x_inlet                 (x 值较大)
    #   喉道 (throat): x = x_inlet - L_c           (x 值中等)
    #   出口 (exit):   x = x_inlet - L_c - L_d     (x 值最小)

    # 外轮廓
    n_c, n_d = 20, 30
    profile_o = []
    profile_i = []

    # 收敛段: 线性半径 R_in → R_th
    for k in range(n_c):
        t = k / (n_c - 1)  # t=0 入口, t=1 喉道
        x = x_inlet - t * L_c
        r_i = R_in + t * (R_th - R_in)     # 内壁
        r_o = r_i + W                        # 外壁
        profile_o.append((x, r_o))
        profile_i.append((x, max(0.5, r_i)))

    # 扩散段: 非线性 R_th → R_ex
    for k in range(1, n_d + 1):
        t = k / n_d  # t=0 喉道, t=1 出口
        x = x_inlet - L_c - t * L_d
        r_i = R_th + (t ** 1.5) * (R_ex - R_th)
        r_o = r_i + W
        profile_o.append((x, r_o))
        profile_i.append((x, max(0.5, r_i)))

    # 入口法兰盘 (加粗)
    flange_r_in = R_in + W + 2
    flange_profile_o = []
    flange_profile_i = []
    for k in range(5):
        t = k / 4.0
        x = x_inlet + t * 5  # 入口外再延伸5mm
        r_o = R_in + W + (1-t) * 4
        r_i = R_in
        flange_profile_o.append((x, max(0.5, r_o)))
        flange_profile_i.append((x, max(0.5, r_i)))

    # 合并 (喷管主段 + 入口法兰)
    full_o = flange_profile_o + profile_o
    full_i = flange_profile_i + profile_i

    nozzle = build_revolve_shell(full_o, full_i)

    nozzle.export(os.path.join(OUTPUT_DIR, "07_tvc_nozzle.stl"))
    nozzle.export(os.path.join(OUTPUT_DIR, "07_tvc_nozzle.glb"))
    print(f"  ✅ TVC喷管: 入口 {R_in*2:.0f}mm → 喉道 {R_th*2:.0f}mm → 出口 {R_ex*2:.0f}mm")
    print(f"         入口 x={x_inlet:.0f}mm, 出口 x={x_inlet - L_c - L_d:.0f}mm")
    return nozzle


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Ad Astra 火箭 - 3D 零件生成器 v4.0")
    print("=" * 70)
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 组装坐标设计 ---
    # 约定: x 越大 = 越靠右/越靠前 (尖点方向)
    #       x 越小 = 越靠左/越靠后 (喷管方向)
    #
    # [尖点 NOSE_TIP] +X
    #       |
    #       v
    #  整流罩  →  机身管(+尾翼+航电舱)  →  TVC底座  →  万向环  →  喷管
    #       ^         ^                   ^          ^         ^
    #  nose_base=0  body_x= -400       tvc_x=-430  gimbal_x=-440  nozzle_x=-455
    #
    # 喷管在最 -X 方向 (最左边/最下面)
    # -X 方向 ←┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ +X 方向

    nose_cone_len = CONFIG["nose"]["length"]
    body_len = CONFIG["body"]["length"]
    tvc_len = CONFIG["tvc_base"]["length"]
    nozzle_total = CONFIG["nozzle"]["conv_len"] + CONFIG["nozzle"]["div_len"]

    # 关键 x 坐标
    NOSE_TIP_X = nose_cone_len       # 尖点位置 (最右端, +X 方向)
    NOSE_BASE_X = 0                  # 整流罩底部位置
    BODY_END_X = 0                   # 机身右端 = 整流罩底部
    BODY_START_X = -body_len         # 机身左端
    TVC_X = BODY_START_X - tvc_len - 2  # TVC 底座左端 (稍微重叠)
    GIMBAL_X = TVC_X - 15              # 万向环中心
    NOZZLE_INLET_X = TVC_X - 25        # 喷管入口

    print("🔴 01. 整流罩...")
    nose = build_nose(x_base=NOSE_BASE_X)

    print("\n🔵 02. 机身管...")
    body = build_body(x_start=BODY_START_X, length=body_len)

    print("\n🟠 03. 尾翼...")
    fins = build_fins(body_x_start=BODY_START_X, body_length=body_len)

    print("\n🟢 04. 航电舱...")
    # 航电舱放在机身内部中间位置
    av_x = BODY_START_X + body_len * 0.3
    avionics = build_avionics(x_start=av_x)

    print("\n🟣 05. TVC 底座...")
    tvc_base = build_tvc_base(x_start=TVC_X)

    print("\n🟡 06. TVC 万向环...")
    gimbal = build_gimbal(x_center=GIMBAL_X)

    print("\n🔵 07. TVC 喷管...")
    nozzle = build_nozzle(x_inlet=NOZZLE_INLET_X)

    print("\n🚀 08. 组装完整火箭...")
    assembly = trimesh.util.concatenate([nose, body, fins, avionics, tvc_base, gimbal, nozzle])
    assembly.export(os.path.join(OUTPUT_DIR, "08_full_rocket_assembly.stl"))
    assembly.export(os.path.join(OUTPUT_DIR, "08_full_rocket_assembly.glb"))

    # 总长度统计
    all_x = []
    for m in [nose, body, fins, avionics, tvc_base, gimbal, nozzle]:
        b = m.bounds
        all_x.extend([b[0][0], b[1][0]])
    x_min = min(all_x)
    x_max = max(all_x)

    print("\n" + "=" * 70)
    print(f"📊 组装完成!")
    print(f"   总长度: {x_max - x_min:.0f}mm (x={x_min:.0f} ~ x={x_max:.0f})")
    print(f"   整流罩尖点: x={x_max:.0f}mm (最右端)")
    print(f"   喷管出口:  x={x_min:.0f}mm (最左端)")
    print(f"   机身位置:   x={BODY_START_X:.0f} ~ {BODY_END_X:.0f}mm")
    print(f"   尾翼位置:   在机身左端区域")
    print(f"   总面数: {len(assembly.faces):,}")
    print("=" * 70)
    print(f"\n📁 输出目录: {OUTPUT_DIR}")
    print(f"\n🌐 预览: http://localhost:8000/viewer.html")
    print("=" * 70)
