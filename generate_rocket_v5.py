#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v5.0  [改进版]
==============================================================================

设计理念:
  +X = 火箭前进方向 (尖头在右边)
  Y, Z = 径向
  真实业余火箭比例: 长径比 ~12:1

零件清单:
  01. 整流罩 (Nose Cone)        - Von Karman 曲线
  02. 机身管 (Body Tube)        - 空心圆柱 + 加强环
  03. 尾翼×4 (Fins)             - 梯形后掠翼 + 翼型
  04. 航电舱 (Avionics Bay)     - 分层圆筒 + 细节
  05. TVC底座 (TVC Base)        - 法兰盘 + 舵机座 + 安装孔
  06. TVC万向节 (Gimbal)        - 双环结构 + 枢轴
  07. TVC喷管 (Nozzle)          - 收敛-扩散 + 法兰
  08. 完整装配体 (Full Assembly)

尺寸 (mm):
  机身直径: 75  (半径 37.5)
  整流罩长: 180 (含15mm插入法兰)
  机身长:   620
  TVC+喷管: 230
  总长:     ~1030
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
BODY_R = 37.5      # 机身半径
BODY_D = BODY_R * 2
WALL = 2.0          # 壁厚
SEG_C = 64          # 圆形截面分段数
OUTPUT = r"D:\AI_rocket\3d_print_files"

os.makedirs(OUTPUT, exist_ok=True)

# 装配位置 (全局X坐标)
# 火箭尖端在 +X，喷管出口在 -X
#   NOSE_TIP_X  -> 最右端 (尖点)
#   机身从 0 向左延伸到 -BODY_LEN
#   TVC/喷管继续向左延伸
X_NOSE_BASE = 0      # 整流罩底部/机身右端
X_NOSE_LEN = 180     # 整流罩长度
X_BODY_LEN = 620     # 机身长度
X_TVC_LEN = 80       # TVC底座长度
X_GIMBAL_LEN = 50    # 万向节长度
X_NOZZLE_LEN = 160   # 喷管长度 (入口+喉道+扩散段)

# 派生坐标
X_NOSE_TIP = X_NOSE_BASE + X_NOSE_LEN   # 180, 最右端
X_BODY_LEFT = X_NOSE_BASE - X_BODY_LEN  # -620, 机身左端
X_TVC_LEFT = X_BODY_LEFT - X_TVC_LEN    # -700, TVC底座左端
X_GIMBAL_LEFT = X_TVC_LEFT - X_GIMBAL_LEN  # -750, 万向节左端
X_NOZZLE_LEFT = X_GIMBAL_LEFT - X_NOZZLE_LEN  # -910, 喷管出口

# ============================================================================
# 工具函数: 圆柱体
# ============================================================================
def make_cylinder(radius, x_start, x_end, segments=SEG_C):
    """创建实心圆柱。"""
    length = x_end - x_start
    c = trimesh.creation.cylinder(radius=radius, height=length, sections=segments)
    # 旋转 + 平移
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x_start + length/2, 0, 0])
    return c

def make_hollow_tube(outer_r, inner_r, x_start, x_end, segments=SEG_C):
    """创建空心圆柱管(两端开口)。"""
    length = x_end - x_start
    outer = trimesh.creation.cylinder(radius=outer_r, height=length, sections=segments)
    inner = trimesh.creation.cylinder(radius=inner_r, height=length, sections=segments)
    outer.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    inner.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    outer.apply_translation([x_start + length/2, 0, 0])
    inner.apply_translation([x_start + length/2, 0, 0])
    # 用布尔求差 (如果引擎可用)
    try:
        result = outer.difference(inner)
        if result is not None and len(result.vertices) > 0:
            return result
    except:
        pass
    # fallback: 手动构造
    return _manual_hollow_tube(outer_r, inner_r, x_start, x_end, segments)

def _manual_hollow_tube(outer_r, inner_r, x_start, x_end, seg):
    verts = []
    faces = []
    n_v_start = 0
    for i, theta in enumerate(np.linspace(0, 2*np.pi, seg, endpoint=False)):
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        # 4 个顶点: 外圈左右 + 内圈左右
        for x in [x_start, x_end]:
            verts.append([x, outer_r*cos_t, outer_r*sin_t])
        for x in [x_start, x_end]:
            verts.append([x, inner_r*cos_t, inner_r*sin_t])
    # 为每 4 个顶点 (per segment) 构造面
    for i in range(seg):
        i2 = (i+1) % seg
        # 本 segment 的顶点索引
        # 0: 外左, 1: 外右, 2: 内左, 3: 内右
        A_OL, A_OR, A_IL, A_IR = 4*i, 4*i+1, 4*i+2, 4*i+3
        B_OL, B_OR, B_IL, B_IR = 4*i2, 4*i2+1, 4*i2+2, 4*i2+3
        # 外侧面
        faces.append([A_OL, B_OL, B_OR])
        faces.append([A_OL, B_OR, A_OR])
        # 内侧面 (法线反转)
        faces.append([A_IL, A_IR, B_IR])
        faces.append([A_IL, B_IR, B_IL])
        # 左环面
        faces.append([A_OL, A_IL, B_IL])
        faces.append([A_OL, B_IL, B_OL])
        # 右环面
        faces.append([A_OR, B_OR, B_IR])
        faces.append([A_OR, B_IR, A_IR])
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))


# ============================================================================
# 工具函数: 旋转体 (Von Karman曲线)
# ============================================================================
def make_revolve_from_radius(x_coords, r_outer, r_inner):
    """
    绕 X 轴旋转生成有厚度的旋转体。
    x_coords: 沿X轴位置数组 (从尖端到底部)
    r_outer:  对应位置外半径
    r_inner:  对应位置内半径
    """
    n = len(x_coords)
    verts = []
    faces = []
    # 生成外表面和内表面的圆周顶点
    outer_ring = []
    inner_ring = []
    for xi, ro, ri in zip(x_coords, r_outer, r_inner):
        for theta in np.linspace(0, 2*np.pi, SEG_C, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
            outer_ring.append([xi, ro*c, ro*s])
            inner_ring.append([xi, ri*c, ri*s])

    n_outer = len(outer_ring)
    verts = outer_ring + inner_ring

    def idx_outer(ring, seg): return ring*SEG_C + seg
    def idx_inner(ring, seg): return n_outer + ring*SEG_C + seg

    # 外表面 (从左环到右环的面, 尖端在+X, 即X最大的一端)
    # ring=0 是 x_coords[0] (尖端), ring=n-1 是 x_coords[-1] (底部)
    for ring in range(n-1):
        for seg in range(SEG_C):
            seg2 = (seg+1) % SEG_C
            a = ring*SEG_C + seg
            b = ring*SEG_C + seg2
            c = (ring+1)*SEG_C + seg
            d = (ring+1)*SEG_C + seg2
            faces.append([a, c, d])
            faces.append([a, d, b])

    # 内表面 (反转法线)
    for ring in range(n-1):
        for seg in range(SEG_C):
            seg2 = (seg+1) % SEG_C
            a = n_outer + ring*SEG_C + seg
            b = n_outer + ring*SEG_C + seg2
            c = n_outer + (ring+1)*SEG_C + seg
            d = n_outer + (ring+1)*SEG_C + seg2
            faces.append([a, b, d])
            faces.append([a, d, c])

    # 尖端口(最小半径端)封口 (ring=0, 外圈->内圈)
    for seg in range(SEG_C):
        seg2 = (seg+1) % SEG_C
        a = seg
        b = seg2
        c = n_outer + seg
        d = n_outer + seg2
        faces.append([a, b, d])
        faces.append([a, d, c])

    # 底端口(最大半径端)封口
    for seg in range(SEG_C):
        seg2 = (seg+1) % SEG_C
        a = (n-1)*SEG_C + seg
        b = (n-1)*SEG_C + seg2
        c = n_outer + (n-1)*SEG_C + seg
        d = n_outer + (n-1)*SEG_C + seg2
        faces.append([a, c, d])
        faces.append([a, d, b])

    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))


# ============================================================================
# 01. 整流罩 Von Karman
# ============================================================================
def build_nose_cone():
    """Von Karman 曲线整流罩。尖点在 x=X_NOSE_TIP=180, 底部在 x=X_NOSE_BASE=0"""
    L = X_NOSE_LEN - 15  # 180mm总长度, 15mm法兰插入机身
    tip_x = X_NOSE_TIP
    base_x = X_NOSE_BASE + 15  # 15mm是法兰位置

    n_pts = 50
    xs = []
    r_outer = []
    r_inner = []

    for i in range(n_pts):
        t = i / (n_pts - 1)  # 0 尖端, 1 底部
        x = tip_x - t * L    # x 从 tip_x 线性减小到 tip_x-L=base_x
        # Von Karman ogive: r(x) = R * sqrt(2*sigma*t - t^2)
        sigma = 0.8
        ro = BODY_R * math.sqrt(max(0.001, 2*sigma*t - t*t))
        # 内壁: 壁厚 2mm (锥形内缩)
        ri = max(0.5, ro * (1 - 0.04) - 1.5)
        xs.append(x)
        r_outer.append(ro)
        r_inner.append(ri)

    shell = make_revolve_from_radius(xs, r_outer, r_inner)

    # 添加底部法兰 (插入机身的圆柱部分, x从base_x到X_NOSE_BASE=0)
    flange_r = BODY_R - 1.5
    flange = make_hollow_tube(flange_r, flange_r - WALL, X_NOSE_BASE, base_x)

    # 添加底部环形盘 (连接外壳和法兰)
    ring_disk = make_hollow_tube(BODY_R, flange_r, base_x - 3, base_x)

    nose = trimesh.util.concatenate([shell, flange, ring_disk])
    nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
    nose.export(os.path.join(OUTPUT, "01_nose_cone.glb"))
    b = nose.bounds
    print(f"  01 ✅ 整流罩: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  Ø{BODY_D:.0f}mm  L={b[1][0]-b[0][0]:.0f}mm  面数:{len(nose.faces)}")
    return nose


# ============================================================================
# 02. 机身管
# ============================================================================
def build_body_tube():
    """机身管: x从X_BODY_LEFT=-620到X_NOSE_BASE=0"""
    body = make_hollow_tube(BODY_R, BODY_R - WALL, X_BODY_LEFT, X_NOSE_BASE)

    # 内部加强环 (每隔150mm一个)
    rings = []
    ring_positions = np.linspace(X_BODY_LEFT + 80, X_NOSE_BASE - 80, 4)
    for rx in ring_positions:
        ring = make_hollow_tube(BODY_R - WALL + 0.3, BODY_R - 15, rx - 4, rx + 4)
        rings.append(ring)

    body_all = trimesh.util.concatenate([body] + rings)
    body_all.export(os.path.join(OUTPUT, "02_body_tube.stl"))
    body_all.export(os.path.join(OUTPUT, "02_body_tube.glb"))
    b = body_all.bounds
    print(f"  02 ✅ 机身管: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  Ø{BODY_D:.0f}mm  L={X_BODY_LEN:.0f}mm  面数:{len(body_all.faces)}")
    return body_all


# ============================================================================
# 03. 尾翼 ×4 (改进版)
# ============================================================================
def build_fins():
    """4片尾翼, 贴在机身尾部(左端), 朝-X方向后掠"""
    fin_count = 4
    root_chord = 160     # 根部弦长
    tip_chord = 70       # 尖部弦长
    span = 60            # 翼展 (从机身表面向外)
    thickness = 5.0      # 尾翼厚度

    # 尾翼根部起点: 距机身左端10mm
    root_start_x = X_BODY_LEFT + 10  # -610
    root_end_x = root_start_x + root_chord  # -450
    tip_start_x = root_start_x + (root_chord - tip_chord) / 2 + 15  # 后掠
    tip_end_x = tip_start_x + tip_chord

    # 4 个角的 3D 位置需要按角度旋转
    # 翼型截面: 简单薄翼 - 上下表面对称, 前缘和后缘有厚度
    # 为简化, 尾翼作为有厚度的平板

    fins_list = []
    for f_idx in range(fin_count):
        theta = math.radians(f_idx * 360.0 / fin_count)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        # 切线方向 (尾翼厚度方向)
        tan_y = -sin_t
        tan_z = cos_t
        half_t = thickness / 2.0

        # 4 个角 (在径向平面内, 然后向切线方向±half_t加厚)
        # 根前缘, 根后缘, 尖后缘, 尖前缘
        # 根部在机身表面 r=BODY_R, 尖部在 r=BODY_R+span
        corners_local = [
            [root_start_x, BODY_R],          # 根前缘 (LE root)
            [root_end_x, BODY_R],            # 根后缘 (TE root)
            [tip_end_x, BODY_R + span],      # 尖后缘 (TE tip)
            [tip_start_x, BODY_R + span],    # 尖前缘 (LE tip)
        ]

        # 为每个角生成两个3D点 (顶面, 底面)
        verts = []
        for lx, lr in corners_local:
            base_y, base_z = lr*cos_t, lr*sin_t
            # 底面
            verts.append([lx, base_y - tan_y*half_t, base_z - tan_z*half_t])
            # 顶面
            verts.append([lx, base_y + tan_y*half_t, base_z + tan_z*half_t])

        # 索引: 0,1 = 根前缘(底,顶); 2,3 = 根后缘; 4,5 = 尖后缘; 6,7 = 尖前缘
        faces_f = [
            # 根部面 (连接机身)
            [0, 2, 3], [0, 3, 1],
            # 后缘面
            [2, 4, 5], [2, 5, 3],
            # 尖部面
            [4, 6, 7], [4, 7, 5],
            # 前缘面
            [6, 0, 1], [6, 1, 7],
            # 侧面1 (底面)
            [0, 4, 2], [0, 6, 4],  # 修正顺序
            # 侧面2 (顶面)
            [1, 3, 5], [1, 5, 7],
        ]
        # 修正侧面 (让它们朝外)
        faces_f = [
            [0, 2, 3], [0, 3, 1],   # 根部
            [2, 4, 5], [2, 5, 3],   # 后缘
            [4, 6, 7], [4, 7, 5],   # 尖部
            [6, 0, 1], [6, 1, 7],   # 前缘
            [0, 4, 2], [0, 6, 4],   # 底面1
            [1, 3, 5], [1, 5, 7],   # 顶面2
        ]

        fin = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces_f))
        fins_list.append(fin)

    fins = trimesh.util.concatenate(fins_list)
    fins.export(os.path.join(OUTPUT, "03_fins_x4.stl"))
    fins.export(os.path.join(OUTPUT, "03_fins_x4.glb"))
    b = fins.bounds
    print(f"  03 ✅ 尾翼×4: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  根弦{root_chord:.0f}mm  翼展{span:.0f}mm  面数:{len(fins.faces)}")
    return fins


# ============================================================================
# 04. 航电舱
# ============================================================================
def build_avionics():
    """航电舱放在机身内部靠前(右端)位置。"""
    av_d = BODY_D - 14  # 61mm, 略小于机身内径
    av_r = av_d / 2
    av_len = 120
    av_start = X_NOSE_BASE - av_len - 30  # 离整流罩底部有30mm间隙

    # 外壳
    shell = make_hollow_tube(av_r, av_r - WALL, av_start, av_start + av_len)

    # 3 个内部隔板
    partitions = []
    for px in np.linspace(av_start + 30, av_start + av_len - 30, 3):
        p = make_cylinder(av_r - WALL, px - 3, px + 3)
        partitions.append(p)

    # 左端盖板
    cap_l = make_cylinder(av_r - WALL + 0.3, av_start - 5, av_start)
    # 右端盖板
    cap_r = make_cylinder(av_r - WALL + 0.3, av_start + av_len, av_start + av_len + 5)

    avionics = trimesh.util.concatenate([shell, cap_l, cap_r] + partitions)
    avionics.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
    avionics.export(os.path.join(OUTPUT, "04_avionics_bay.glb"))
    b = avionics.bounds
    print(f"  04 ✅ 航电舱: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  Ø{av_d:.0f}mm  L={av_len:.0f}mm  面数:{len(avionics.faces)}")
    return avionics


# ============================================================================
# 05. TVC底座 (大法兰盘)
# ============================================================================
def build_tvc_base():
    """
    TVC底座: x 从 X_BODY_LEFT=-620 到 X_TVC_LEFT=-700 (80mm长)
    - 与机身连接的法兰盘
    - 中心孔 (供燃气通过)
    - 四个舵机座 (上下左右)
    - 外部4个固定凸耳
    """
    x_left = X_TVC_LEFT          # -700
    x_right = X_BODY_LEFT        # -620
    L = x_right - x_left         # 80
    mid_x = (x_left + x_right) / 2

    # 主法兰盘 (外径比机身稍大)
    flange_r = BODY_R + 8        # 45.5
    center_hole_r = 25           # 中心通孔

    # 主体圆环 (空心圆柱法兰)
    main_body = make_hollow_tube(flange_r, center_hole_r, x_left, x_right)

    # 与机身连接的加强环 (右端更大的法兰)
    attach_flange = make_hollow_tube(BODY_R + 3, center_hole_r, x_right - 10, x_right)

    # 4个舵机安装座 (沿 +Y, -Y, +Z, -Z 方向)
    servo_mounts = []
    servo_w = 20
    servo_h = 15
    servo_d = 25
    for sign_y, sign_z in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        # 简化: 用小圆柱作为舵机座的突出部
        dir_y = sign_y if sign_y != 0 else 0
        dir_z = sign_z if sign_z != 0 else 0
        mount_r = 12
        mount_cx = mid_x
        mount_cy = dir_y * (flange_r + servo_d/2)
        mount_cz = dir_z * (flange_r + servo_d/2)

        # 沿X方向的小圆柱/方块
        mount = make_cylinder(mount_r, mount_cx - servo_w/2, mount_cx + servo_w/2, segments=20)
        # 向 YZ 方向外移
        v = mount.vertices.copy()
        v[:, 1] += mount_cy * 0
        v[:, 2] += mount_cz * 0
        # 让 mount 从法兰表面伸出
        if dir_y != 0:
            v[:, 1] += dir_y * (flange_r + 5)
        if dir_z != 0:
            v[:, 2] += dir_z * (flange_r + 5)
        mount.vertices = v
        servo_mounts.append(mount)

    # 4个固定凸耳 (与机身连接用, 在法兰外围)
    lugs = []
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        dir_y, dir_z = math.cos(theta), math.sin(theta)
        lug_r = 8
        lug_cx = x_right - 15
        lug = make_cylinder(lug_r, lug_cx - 10, lug_cx + 10, segments=16)
        v = lug.vertices.copy()
        v[:, 1] += dir_y * (flange_r + 5)
        v[:, 2] += dir_z * (flange_r + 5)
        lug.vertices = v
        lugs.append(lug)

    base = trimesh.util.concatenate([main_body, attach_flange] + servo_mounts + lugs)
    base.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
    base.export(os.path.join(OUTPUT, "05_tvc_base.glb"))
    b = base.bounds
    print(f"  05 ✅ TVC底座: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  Ø{flange_r*2:.0f}mm  L={L:.0f}mm  面数:{len(base.faces)}")
    return base


# ============================================================================
# 06. TVC万向节
# ============================================================================
def build_gimbal():
    """
    万向节: 双环结构 + 4个枢轴, x 从 X_TVC_LEFT=-700 到 X_GIMBAL_LEFT=-750
    """
    x_left = X_GIMBAL_LEFT
    x_right = X_TVC_LEFT
    L = x_right - x_left  # 50mm
    mid_x = (x_left + x_right) / 2

    outer_r = BODY_R + 2  # 39.5, 略大于机身
    ring_thick = 10

    # 外环 (厚圆筒)
    outer_ring = make_hollow_tube(outer_r, outer_r - ring_thick, mid_x - L/2 + 10, mid_x + L/2 - 10)

    # 4 个枢轴 (X轴方向为轴)
    pivots = []
    pivot_r = 4
    pivot_len = 25
    for sign_y, sign_z in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        # 沿切线方向的圆柱 (垂直于径向)
        pv = make_cylinder(pivot_r, mid_x - pivot_len/2, mid_x + pivot_len/2, segments=16)
        v = pv.vertices.copy()
        if sign_y != 0:
            v[:, 1] += sign_y * (outer_r + pivot_len/2)
        if sign_z != 0:
            v[:, 2] += sign_z * (outer_r + pivot_len/2)
        pv.vertices = v
        pivots.append(pv)

    # 4个舵机连接臂
    arms = []
    for sign_y, sign_z in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        arm_r = 7
        arm_len = 35
        arm = make_cylinder(arm_r, mid_x - 10, mid_x + 10, segments=14)
        v = arm.vertices.copy()
        if sign_y != 0:
            v[:, 1] += sign_y * (outer_r + arm_len)
        if sign_z != 0:
            v[:, 2] += sign_z * (outer_r + arm_len)
        arm.vertices = v
        arms.append(arm)

    gimbal = trimesh.util.concatenate([outer_ring] + pivots + arms)
    gimbal.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
    gimbal.export(os.path.join(OUTPUT, "06_tvc_gimbal.glb"))
    b = gimbal.bounds
    print(f"  06 ✅ TVC万向节: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  Ø{outer_r*2:.0f}mm  L={L:.0f}mm  面数:{len(gimbal.faces)}")
    return gimbal


# ============================================================================
# 07. TVC喷管 (收敛-扩散喷管, 改进版)
# ============================================================================
def build_nozzle():
    """
    喷管: 入口在右(连接万向节), 出口在左。收敛-扩散形状。
    x 从 X_GIMBAL_LEFT=-750 到 X_NOZZLE_LEFT=-910
    """
    x_inlet = X_GIMBAL_LEFT     # -750 (入口: 右端, x较大)
    x_exit = X_NOZZLE_LEFT      # -910 (出口: 左端, x较小)
    total_len = x_inlet - x_exit  # 160mm

    # 收敛段: 入口(大) -> 喉道(小)
    # 扩散段: 喉道(小) -> 出口(中)
    R_inlet = 32       # 入口半径 φ64
    R_throat = 17      # 喉道半径 φ34
    R_exit = 28        # 出口半径 φ56
    frac_conv = 0.35   # 收敛段占总长度的比例
    L_conv = total_len * frac_conv  # 56mm
    L_div = total_len - L_conv     # 104mm
    x_throat = x_inlet - L_conv    # 喉道位置

    # 构造曲线
    n_conv = 25
    n_div = 40
    xs = []
    r_outer = []
    r_inner = []
    wall = 4.0

    # 收敛段 (inlet -> throat)
    for i in range(n_conv):
        t = i / (n_conv - 1)  # 0=inlet, 1=throat
        x = x_inlet - t * L_conv
        # 非线性收敛 (更接近真实喷管: 入口处曲率大, 接近喉道处平滑)
        r_in = R_inlet - (R_inlet - R_throat) * (t ** 0.7)
        r_out = r_in + wall
        xs.append(x)
        r_inner.append(r_in)
        r_outer.append(r_out)

    # 扩散段 (throat -> exit)
    for i in range(1, n_div + 1):
        t = i / n_div  # 0=throat, 1=exit
        x = x_throat - t * L_div
        # 非线性扩散 (前段扩张快, 后段扩张逐渐放缓)
        r_in = R_throat + (R_exit - R_throat) * (t ** 1.3)
        r_out = r_in + wall
        xs.append(x)
        r_inner.append(r_in)
        r_outer.append(r_out)

    # 入口法兰 (加厚段)
    flange_thick = 8
    for i in range(8):
        t = i / 7.0
        x = x_inlet + t * flange_thick  # 入口往右延长一点
        r_in = R_inlet
        r_out = R_inlet + 12  # 法兰加厚
        xs.insert(0, x)
        r_inner.insert(0, r_in)
        r_outer.insert(0, r_out)

    # 生成旋转体
    nozzle = make_revolve_from_radius(xs, r_outer, r_inner)

    nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
    nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.glb"))
    b = nozzle.bounds
    print(f"  07 ✅ TVC喷管: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  入φ{R_inlet*2:.0f} 喉φ{R_throat*2:.0f} 出φ{R_exit*2:.0f}  L={total_len+flange_thick:.0f}mm  面数:{len(nozzle.faces)}")
    return nozzle


# ============================================================================
# 主程序
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Ad Astra 火箭 - 3D 零件生成器 v5.0 [改进版]")
    print("=" * 70)
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 输出目录: {OUTPUT}")
    print()
    print(f"  设计规格:")
    print(f"    机身直径 Ø {BODY_D:.0f} mm")
    print(f"    总长度   ~ {X_NOSE_TIP - X_NOZZLE_LEFT:.0f} mm")
    print(f"    长径比   ~ {(X_NOSE_TIP - X_NOZZLE_LEFT)/BODY_D:.1f} : 1")
    print()
    print("-" * 70)

    parts = []

    # 01 整流罩
    nose = build_nose_cone()
    parts.append(nose)

    # 02 机身
    body = build_body_tube()
    parts.append(body)

    # 03 尾翼
    fins = build_fins()
    parts.append(fins)

    # 04 航电舱
    av = build_avionics()
    parts.append(av)

    # 05 TVC底座
    tvc = build_tvc_base()
    parts.append(tvc)

    # 06 万向节
    gimbal = build_gimbal()
    parts.append(gimbal)

    # 07 喷管
    nozzle = build_nozzle()
    parts.append(nozzle)

    # 08 完整装配体
    assembly = trimesh.util.concatenate(parts)
    assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.stl"))
    assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.glb"))

    b = assembly.bounds
    total_len = b[1][0] - b[0][0]
    max_r = max(abs(b[1][1]), abs(b[0][1]), abs(b[1][2]), abs(b[0][2]))
    print("\n" + "-" * 70)
    print(f"  08 ✅ 完整装配体: x=[{b[0][0]:.0f}, {b[1][0]:.0f}]  总长 {total_len:.0f} mm")
    print(f"      最大径向: {max_r:.0f} mm  (含尾翼/舵机座)")
    print(f"      三角面总数: {len(assembly.faces):,}")
    print("-" * 70)
    print("\n✅ 全部零件生成成功!")
    print(f"🌐 在浏览器查看: http://localhost:8000/viewer.html")
    print("=" * 70)
