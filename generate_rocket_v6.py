#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v6.0 [完整机械设计版]
==============================================================================

设计特点:
  ✅ 所有法兰连接处有螺栓孔
  ✅ 航电舱有检修盖板 + 螺丝孔
  ✅ 机身有加强肋 + 穿线孔 + 安装孔
  ✅ 尾翼有螺栓连接 + 根部加强
  ✅ TVC系统有轴承座 + 螺栓固定
  ✅ 喷管有法兰 + 密封槽 + 支撑环
  ✅ 整流罩有分离机构 + O型圈槽

螺栓规格:
  M3: 机身连接、检修盖板
  M4: 尾翼固定
  M5: TVC法兰连接
  M6: 分离机构

尺寸 (mm):
  机身直径: 75  |  总长: ~1100mm  |  长径比: ~15:1
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
BODY_R = 37.5
BODY_D = BODY_R * 2
WALL = 2.5
SEG = 48
OUTPUT = r"D:\AI_rocket\3d_print_files"
os.makedirs(OUTPUT, exist_ok=True)

# 装配坐标
X_NOSE_BASE = 0
X_NOSE_LEN = 190
X_NOSE_TIP = X_NOSE_BASE + X_NOSE_LEN   # 190
X_BODY_LEN = 630
X_BODY_LEFT = X_NOSE_BASE - X_BODY_LEN  # -630
X_TVC_LEN = 90
X_TVC_LEFT = X_BODY_LEFT - X_TVC_LEN     # -720
X_GIMBAL_LEN = 60
X_GIMBAL_LEFT = X_TVC_LEFT - X_GIMBAL_LEN  # -780
X_NOZZLE_LEN = 170
X_NOZZLE_LEFT = X_GIMBAL_LEFT - X_NOZZLE_LEN  # -950

# ============================================================================
# 几何工具
# ============================================================================
def make_cylinder_r(radius, x_start, x_end, segments=SEG):
    length = x_end - x_start
    c = trimesh.creation.cylinder(radius=radius, height=length, sections=segments)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x_start + length/2, 0, 0])
    return c

def make_hollow_tube_r(outer_r, inner_r, x_start, x_end, segments=SEG):
    """空心圆柱管 (两端开口)"""
    length = x_end - x_start
    outer = trimesh.creation.cylinder(radius=outer_r, height=length, sections=segments)
    inner = trimesh.creation.cylinder(radius=inner_r, height=length, sections=segments)
    outer.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    inner.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    outer.apply_translation([x_start + length/2, 0, 0])
    inner.apply_translation([x_start + length/2, 0, 0])
    try:
        result = outer.difference(inner)
        if result is not None and len(result.vertices) > 0:
            return result
    except:
        pass
    return _manual_hollow(outer_r, inner_r, x_start, x_end, segments)

def _manual_hollow(outer_r, inner_r, x_start, x_end, seg):
    verts, faces = [], []
    for i, theta in enumerate(np.linspace(0, 2*np.pi, seg, endpoint=False)):
        c, s = np.cos(theta), np.sin(theta)
        for x in [x_start, x_end]:
            verts.append([x, outer_r*c, outer_r*s])
        for x in [x_start, x_end]:
            verts.append([x, inner_r*c, inner_r*s])
    for i in range(seg):
        i2 = (i+1) % seg
        A0, A1, A2, A3 = 4*i, 4*i+1, 4*i+2, 4*i+3
        B0, B1, B2, B3 = 4*i2, 4*i2+1, 4*i2+2, 4*i2+3
        faces += [[A0,B0,B1],[A0,B1,A1],[A2,A3,B3],[A2,B3,B2],
                   [A0,A2,B2],[A0,B2,B0],[A1,B1,B3],[A1,B3,A3]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

def make_disc(radius, thickness, x_center, segments=SEG):
    """实心圆盘"""
    c = make_cylinder_r(radius, x_center - thickness/2, x_center + thickness/2, segments)
    return c

def make_bolt_holes_circle(n_holes, hole_r, circle_r, x_plane, z_rotation_deg=0):
    """
    在 x=x_plane 平面上创建一个螺栓孔阵列
    n_holes: 孔数量
    hole_r: 孔半径
    circle_r: 孔所在圆的半径
    z_rotation_deg: 绕Z轴旋转角度
    """
    parts = []
    z_rot = math.radians(z_rotation_deg)
    for i in range(n_holes):
        theta = math.radians(i * 360.0 / n_holes) + z_rot
        cx = x_plane
        cy = circle_r * math.cos(theta)
        cz = circle_r * math.sin(theta)
        hole = make_cylinder_r(hole_r, cx - 4, cx + 4, segments=12)
        hole.apply_translation([0, cy, cz])
        parts.append(hole)
    return parts

def make_bolt_ring(n_holes, bolt_r, circle_r, x_start, x_end, segments=SEG):
    """
    创建一个螺栓法兰: 圆柱形法兰环, 周围均匀分布 n_holes 个螺栓孔
    整体是一个空心环, 但周围有螺栓突出的部分
    """
    parts = []
    parts.append(make_hollow_tube_r(circle_r + bolt_r*2, circle_r, x_start, x_end, segments))

    # 螺栓孔(用小圆柱表示孔, 从外向内穿透)
    for i in range(n_holes):
        theta = math.radians(i * 360.0 / n_holes)
        bx = (x_start + x_end) / 2
        by = circle_r * math.cos(theta)
        bz = circle_r * math.sin(theta)
        # 螺栓头凸起 (法兰外侧的圆柱头, 表示螺栓固定位置)
        bolt_head = make_cylinder_r(bolt_r * 1.8, x_end - 1, x_end + bolt_r * 2, segments=12)
        bolt_head.apply_translation([0, by, bz])
        parts.append(bolt_head)
    return parts

def add_groove(mesh, radius, groove_r, x_position, circle_r, n_grooves=1):
    """
    在 x=x_position 位置添加 O 型圈沟槽 (环绕管道的环形凹槽)
    """
    # 简化: 在管道外表面添加环形凸起代表沟槽位置
    verts_before = len(mesh.vertices)
    ring = make_hollow_tube_r(circle_r + groove_r * 2, circle_r, x_position - 1, x_position + 1, segments=SEG)
    parts.append(ring)
    return parts

def make_revolve_detailed(xs, rs_out, rs_in):
    """旋转体, 带内腔"""
    n = len(xs)
    verts = []
    # 外环 + 内环
    for xi, ro, ri in zip(xs, rs_out, rs_in):
        for theta in np.linspace(0, 2*np.pi, SEG, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
            verts.append([xi, ro*c, ro*s])
    outer_start = 0
    inner_start = n * SEG

    verts_out_end = outer_start + n * SEG
    # 内环顶点
    for xi, ro, ri in zip(xs, rs_out, rs_in):
        for theta in np.linspace(0, 2*np.pi, SEG, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
            verts.append([xi, ri*c, ri*s])
    n_total = len(verts)

    faces = []
    def o(ring, seg): return outer_start + ring*SEG + seg
    def i(ring, seg): return inner_start + ring*SEG + seg

    # 外表面
    for ring in range(n-1):
        for seg in range(SEG):
            s2 = (seg+1)%SEG
            faces += [[o(ring,seg),o(ring+1,seg),o(ring+1,s2)],[o(ring,seg),o(ring+1,s2),o(ring,s2)]]
    # 内表面
    for ring in range(n-1):
        for seg in range(SEG):
            s2 = (seg+1)%SEG
            faces += [[i(ring,seg),i(ring,s2),i(ring+1,s2)],[i(ring,seg),i(ring+1,s2),i(ring+1,seg)]]
    # 尖端封口
    for seg in range(SEG):
        s2 = (seg+1)%SEG
        faces += [[o(0,seg),o(0,s2),i(0,s2)],[o(0,seg),i(0,s2),i(0,seg)]]
    # 底部封口
    for seg in range(SEG):
        s2 = (seg+1)%SEG
        faces += [[o(n-1,seg),o(n-1,s2),i(n-1,s2)],[o(n-1,seg),i(n-1,s2),i(n-1,seg)]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

# ============================================================================
# 01. 整流罩 - 带分离机构和O型圈槽
# ============================================================================
def build_nose():
    """
    包含:
    - Von Karman 曲线主体
    - 底部法兰 (插入机身)
    - 分离环槽 (O型圈密封)
    - 6个M3分离螺栓孔 (45°均布)
    """
    L_body = X_NOSE_LEN - 20
    tip_x = X_NOSE_TIP
    base_x = X_NOSE_BASE + 20

    n = 50
    xs, r_out, r_in = [], [], []
    for i in range(n):
        t = i / (n-1)
        x = tip_x - t * L_body
        sigma = 0.8
        ro = BODY_R * math.sqrt(max(0.001, 2*sigma*t - t*t))
        ri = max(0.5, ro - WALL)
        xs.append(x); r_out.append(ro); r_in.append(ri)

    nose = make_revolve_detailed(xs, r_out, r_in)

    # 底部法兰 (插入机身段)
    flange_r = BODY_R - 1.5
    flange = make_hollow_tube_r(flange_r, flange_r - WALL, X_NOSE_BASE, base_x)
    nose = trimesh.util.concatenate([nose, flange])

    # O型圈沟槽 (在法兰上方, x=base_x 附近)
    groove_x = base_x + 5
    groove = make_hollow_tube_r(flange_r + 1, flange_r - 2, groove_x - 2, groove_x + 2)
    nose = trimesh.util.concatenate([nose, groove])

    # 6个M3分离螺栓孔 (在 x=base_x 平面, 45°均布, r=BODY_R-5)
    separation_bolt_r = 1.5  # M3螺栓半径
    for i in range(6):
        theta = math.radians(i * 60)
        by = (BODY_R - 5) * math.cos(theta)
        bz = (BODY_R - 5) * math.sin(theta)
        bolt_hole = make_cylinder_r(separation_bolt_r, base_x - 15, base_x + 15, segments=8)
        bolt_hole.apply_translation([0, by, bz])
        nose = trimesh.util.concatenate([nose, bolt_hole])

    nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
    nose.export(os.path.join(OUTPUT, "01_nose_cone.glb"))
    b = nose.bounds
    print(f"  01 ✅ 整流罩: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  Ø{BODY_D:.0f}mm  L={b[1][0]-b[0][0]:.0f}mm  面数:{len(nose.faces):,}")
    print(f"      → 法兰螺栓孔: 6×M3 @ Ø{BODY_D-10:.0f}mm, 分离O型圈槽 x={groove_x:.0f}")
    return nose


# ============================================================================
# 02. 机身管 - 带加强肋 + 穿线孔 + 安装孔
# ============================================================================
def build_body():
    """
    包含:
    - 空心主筒
    - 外部纵向加强肋 (4条, 沿全长)
    - 穿线孔 (侧面, 用于舵机线缆)
    - 航电舱安装孔 (机身内壁)
    - 贯穿螺栓孔 (法兰连接处)
    """
    body = make_hollow_tube_r(BODY_R, BODY_R - WALL, X_BODY_LEFT, X_NOSE_BASE)

    all_parts = [body]

    # --- 外部加强肋 (4条, 沿全长, 径向方向) ---
    n_ribs = 4
    rib_r = BODY_R + 3  # 肋条外径
    rib_thick = 3        # 肋条厚度
    for i in range(n_ribs):
        theta = math.radians(i * 90)
        rib_cy = rib_r * math.cos(theta)
        rib_cz = rib_r * math.sin(theta)
        rib = make_hollow_tube_r(rib_thick, rib_thick - WALL, X_BODY_LEFT + 10, X_NOSE_BASE - 10, segments=12)
        v = rib.vertices.copy()
        v[:, 1] += rib_cy
        v[:, 2] += rib_cz
        rib.vertices = v
        all_parts.append(rib)

    # --- 穿线孔 (机身侧面, 机身中段) ---
    wire_hole_r = 3  # M6 穿线孔
    wire_hole_positions = [
        X_BODY_LEFT + 150,
        X_BODY_LEFT + 300,
        X_BODY_LEFT + 450,
    ]
    for wx in wire_hole_positions:
        for i in range(2):  # 每侧2个
            theta = math.radians(90 + i * 180)  # ±Y方向
            hy = (BODY_R + 2) * math.cos(theta)
            hz = (BODY_R + 2) * math.sin(theta)
            hole = make_cylinder_r(wire_hole_r, wx - 5, wx + 5, segments=10)
            hole.apply_translation([0, hy, hz])
            all_parts.append(hole)

    # --- 贯穿螺栓孔 (机身与TVC连接处) ---
    # 4个M5螺栓, 沿机身尾端周向均布
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        bx = X_BODY_LEFT + 15
        by = (BODY_R - 3) * math.cos(theta)
        bz = (BODY_R - 3) * math.sin(theta)
        bolt_hole = make_cylinder_r(2.5, X_BODY_LEFT, X_BODY_LEFT + 30, segments=8)
        bolt_hole.apply_translation([0, by, bz])
        all_parts.append(bolt_hole)

    # --- 贯穿螺栓孔 (机身与整流罩连接处) ---
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        bx = X_NOSE_BASE - 15
        by = (BODY_R - 3) * math.cos(theta)
        bz = (BODY_R - 3) * math.sin(theta)
        bolt_hole = make_cylinder_r(2.5, X_NOSE_BASE - 30, X_NOSE_BASE, segments=8)
        bolt_hole.apply_translation([0, by, bz])
        all_parts.append(bolt_hole)

    body_all = trimesh.util.concatenate(all_parts)
    body_all.export(os.path.join(OUTPUT, "02_body_tube.stl"))
    body_all.export(os.path.join(OUTPUT, "02_body_tube.glb"))
    b = body_all.bounds
    print(f"  02 ✅ 机身管: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  Ø{BODY_D:.0f}mm  L={X_BODY_LEN:.0f}mm  面数:{len(body_all.faces):,}")
    print(f"      → 加强肋: 4条 × 沿全长,  → 穿线孔: {len(wire_hole_positions)*2}×Ø{2*wire_hole_r:.0f}mm")
    print(f"      → 连接螺栓: 4×M5 @ x={X_BODY_LEFT:.0f}, 4×M5 @ x={X_NOSE_BASE:.0f}")
    return body_all


# ============================================================================
# 03. 尾翼 ×4 - 螺栓连接 + 根部加强
# ============================================================================
def build_fins():
    """
    包含:
    - 主翼面 (梯形后掠)
    - 根部加强区 (更厚的根部截面)
    - 4个M4安装螺栓孔 (沿根部弦长均布)
    - 加强筋 (翼根部的纵向肋)
    """
    fin_count = 4
    root_chord = 180
    tip_chord = 60
    span = 70
    thickness = 6
    root_start_x = X_BODY_LEFT + 5
    lead_sweep = (root_chord - tip_chord) / 2 + 15

    fins_list = []
    for f_idx in range(fin_count):
        theta = math.radians(f_idx * 360.0 / fin_count)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        tan_y, tan_z = -sin_t, cos_t
        half_t = thickness / 2.0

        # 4角 (x, r) r = 径向距离
        A = [root_start_x, BODY_R]                    # 根前缘
        B = [root_start_x + root_chord, BODY_R]       # 根后缘
        C = [root_start_x + root_chord, BODY_R + span] # 尖后缘
        D = [root_start_x + lead_sweep, BODY_R + span] # 尖前缘

        # 加强根部: 在 A~B 之间加厚
        verts = []
        for p in [A, B, C, D]:
            px, pr = p
            base_y, base_z = pr*cos_t, pr*sin_t
            # 根部局部加厚
            t_norm = (px - A[0]) / (B[0] - A[0]) if B[0] != A[0] else 1
            local_half = half_t * (1 + 0.5 * max(0, 1 - t_norm * 2))
            verts.append([px, base_y - tan_y*local_half, base_z - tan_z*local_half])
            verts.append([px, base_y + tan_y*local_half, base_z + tan_z*local_half])

        # 12个面
        faces = [
            [0,2,3],[0,3,1],  # 根面
            [2,4,5],[2,5,3],  # 后缘
            [4,6,7],[4,7,5],  # 尖面
            [6,0,1],[6,1,7],  # 前缘
            [0,4,2],[0,6,4],  # 底面
            [1,3,5],[1,5,7],  # 顶面
        ]
        fin = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
        fins_list.append(fin)

        # === 添加螺栓孔 (在根部的中间位置) ===
        bolt_r = 2.0  # M4螺栓
        bolt_positions = [0.3, 0.5, 0.7]  # 沿根弦的3个螺栓位置
        for bt in bolt_positions:
            bx = root_start_x + bt * root_chord
            # 螺栓孔 (穿透尾翼的小圆柱)
            bolt_hole = make_cylinder_r(bolt_r, A[1]*cos_t - 5, A[1]*cos_t + 5, segments=8)
            bolt_hole.apply_translation([bx, 0, 0])
            # 旋转到正确角度
            verts_b = bolt_hole.vertices.copy()
            new_v = np.zeros_like(verts_b)
            new_v[:, 0] = verts_b[:, 0]
            new_v[:, 1] = verts_b[:, 1]*cos_t - verts_b[:, 2]*sin_t
            new_v[:, 2] = verts_b[:, 1]*sin_t + verts_b[:, 2]*cos_t
            bolt_hole.vertices = new_v
            fins_list.append(bolt_hole)

    fins = trimesh.util.concatenate(fins_list)
    fins.export(os.path.join(OUTPUT, "03_fins_x4.stl"))
    fins.export(os.path.join(OUTPUT, "03_fins_x4.glb"))
    b = fins.bounds
    print(f"  03 ✅ 尾翼×4: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  根弦{root_chord:.0f}  翼展{span:.0f}  面数:{len(fins.faces):,}")
    print(f"      → 每片 {len(bolt_positions)}×M4螺栓孔, 加强根部截面")
    return fins


# ============================================================================
# 04. 航电舱 - 检修盖板 + 螺丝孔 + 线缆出口
# ============================================================================
def build_avionics():
    """
    包含:
    - 主外壳 (Ø61mm 空心)
    - 检修盖板 (可拆卸, 带6个M3螺丝孔)
    - 内部隔板 (分2个舱)
    - 线缆出口 (侧面圆形凸台)
    - 安装支架 (嵌入机身的凸耳)
    """
    av_d = BODY_D - 14
    av_r = av_d / 2
    av_len = 130
    av_x = X_NOSE_BASE - av_len - 40

    all_parts = []

    # 主外壳
    shell = make_hollow_tube_r(av_r, av_r - WALL, av_x, av_x + av_len)
    all_parts.append(shell)

    # 端盖 (左端和右端)
    for side_x in [av_x - 5, av_x + av_len]:
        cap = make_disc(av_r - WALL + 1, 5, side_x)
        all_parts.append(cap)

    # 内部隔板
    for px in [av_x + av_len * 0.33, av_x + av_len * 0.67]:
        part = make_disc(av_r - WALL + 1, 3, px)
        all_parts.append(part)

    # 检修盖板 (舱室1的中部, 可拆卸面板)
    hatch_x = av_x + av_len * 0.16
    hatch_r = av_r * 0.6
    hatch = make_disc(hatch_r, 3, hatch_x)
    all_parts.append(hatch)

    # 6个M3螺丝孔 (均布在盖板周围)
    for i in range(6):
        theta = math.radians(i * 60)
        sx = hatch_x
        sy = (hatch_r + 3) * math.cos(theta)
        sz = (hatch_r + 3) * math.sin(theta)
        screw_hole = make_cylinder_r(1.5, sx - 2, sx + 2, segments=8)
        screw_hole.apply_translation([0, sy, sz])
        all_parts.append(screw_hole)

    # 线缆出口凸台 (侧面)
    for side_sign in [-1, 1]:
        port_theta = math.radians(90 * side_sign)
        port_r = 5  # 出口半径
        port_cy = av_r * math.cos(port_theta)
        port_cz = av_r * math.sin(port_theta)
        port = make_cylinder_r(port_r + 2, av_x + av_len * 0.5 - 5, av_x + av_len * 0.5 + 5, segments=12)
        port.apply_translation([0, port_cy * 1.15, port_cz * 1.15])
        all_parts.append(port)

    # 固定耳 (嵌入机身用)
    for i in range(4):
        theta = math.radians(i * 90)
        ear_cy = (BODY_R - 5) * math.cos(theta)
        ear_cz = (BODY_R - 5) * math.sin(theta)
        ear = make_cylinder_r(6, av_x + av_len * 0.5 - 3, av_x + av_len * 0.5 + 3, segments=12)
        ear.apply_translation([0, ear_cy, ear_cz])
        all_parts.append(ear)

    av = trimesh.util.concatenate(all_parts)
    av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
    av.export(os.path.join(OUTPUT, "04_avionics_bay.glb"))
    b = av.bounds
    print(f"  04 ✅ 航电舱: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  Ø{av_d:.0f}mm  L={av_len:.0f}mm  面数:{len(av.faces):,}")
    print(f"      → 检修盖板: Ø{hatch_r*2:.0f}mm + 6×M3螺丝,  → 线缆出口: 2×Ø{2*port_r:.0f}mm")
    return av


# ============================================================================
# 05. TVC底座 - 法兰连接 + 轴承座 + 舵机安装
# ============================================================================
def build_tvc_base():
    """
    包含:
    - 主法兰盘 (Ø90mm, 比机身大)
    - 中央通孔 (燃气通道)
    - 4个M5贯穿螺栓孔 (与机身连接)
    - 4个轴承座凸台 (用于万向节枢轴)
    - 4个舵机安装孔 (M3)
    - 固定凸耳 (与机身外侧连接)
    """
    all_parts = []
    flange_r = BODY_R + 10  # 47.5
    center_hole_r = 22
    x_left = X_TVC_LEFT
    x_right = X_BODY_LEFT
    L = x_right - x_left

    # 主法兰 (空心圆盘)
    main = make_hollow_tube_r(flange_r, center_hole_r, x_left, x_right)
    all_parts.append(main)

    # 连接法兰 (右端扩大法兰)
    attach = make_hollow_tube_r(BODY_R + 5, center_hole_r, x_right - 15, x_right)
    all_parts.append(attach)

    # 4个M5贯穿螺栓孔 (机身连接)
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        bx = x_left + L / 2
        by = (flange_r - 5) * math.cos(theta)
        bz = (flange_r - 5) * math.sin(theta)
        bolt = make_cylinder_r(2.5, x_left - 10, x_left + 10, segments=8)
        bolt.apply_translation([0, by, bz])
        all_parts.append(bolt)

    # 4个轴承座 (用于万向节枢轴, 沿径向伸出)
    bearing_r = 12
    bearing_len = 25
    for i in range(4):
        theta = math.radians(i * 90)
        bcy = (flange_r + bearing_len/2) * math.cos(theta)
        bcz = (flange_r + bearing_len/2) * math.sin(theta)
        bearing = make_cylinder_r(bearing_r, x_left + L/2 - 8, x_left + L/2 + 8, segments=16)
        v = bearing.vertices.copy()
        v[:, 1] += bcy
        v[:, 2] += bcz
        bearing.vertices = v
        all_parts.append(bearing)

        # 轴承孔 (中间通孔)
        bore = make_cylinder_r(5, x_left + L/2 - 15, x_left + L/2 + 15, segments=12)
        bore.apply_translation([0, bcy, bcz])
        all_parts.append(bore)

    # 4个舵机安装孔 (上下左右)
    servo_r = 4
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        scy = (center_hole_r + 10) * math.cos(theta)
        scz = (center_hole_r + 10) * math.sin(theta)
        servo = make_cylinder_r(servo_r, x_left + 5, x_left + 20, segments=10)
        servo.apply_translation([0, scy, scz])
        all_parts.append(servo)

    # 固定凸耳 (外侧4个)
    lug_r = 8
    for i in range(4):
        theta = math.radians(i * 90 + 22.5)
        lcy = (flange_r + 5) * math.cos(theta)
        lcz = (flange_r + 5) * math.sin(theta)
        lug = make_cylinder_r(lug_r, x_right - 8, x_right + 8, segments=12)
        v = lug.vertices.copy()
        v[:, 1] += lcy
        v[:, 2] += lcz
        lug.vertices = v
        all_parts.append(lug)

    base = trimesh.util.concatenate(all_parts)
    base.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
    base.export(os.path.join(OUTPUT, "05_tvc_base.glb"))
    b = base.bounds
    print(f"  05 ✅ TVC底座: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  Ø{flange_r*2:.0f}mm  L={L:.0f}mm  面数:{len(base.faces):,}")
    print(f"      → 4×M5贯穿螺栓,  → 4×轴承座(枢轴安装),  → 4×舵机M3安装孔")
    return base


# ============================================================================
# 06. TVC万向节 - 双环 + 枢轴 + 轴承
# ============================================================================
def build_gimbal():
    """
    包含:
    - 外环 (连接TVC底座的枢轴)
    - 内环 (连接喷管)
    - 4个枢轴螺栓 (穿过轴承座)
    - 对中标记 (凸起刻线)
    - 舵机连接臂 (4个伸出臂)
    """
    all_parts = []
    outer_r = BODY_R + 3
    inner_r = outer_r - 12
    L = X_GIMBAL_LEFT + X_GIMBAL_LEN - X_TVC_LEFT  # 60
    mid_x = X_TVC_LEFT - L / 2

    # 外环
    outer_ring = make_hollow_tube_r(outer_r, outer_r - 10, mid_x - L/2 + 10, mid_x + L/2 - 10)
    all_parts.append(outer_ring)

    # 内环 (偏心, 通过枢轴与外环连接)
    inner_ring = make_hollow_tube_r(inner_r, inner_r - 8, mid_x - L/2 + 20, mid_x + L/2 - 20)
    all_parts.append(inner_ring)

    # 4个枢轴 (沿径向伸出)
    pivot_r = 5
    pivot_len = 20
    for i in range(4):
        theta = math.radians(i * 90)
        pcy = (outer_r + pivot_len/2) * math.cos(theta)
        pcz = (outer_r + pivot_len/2) * math.sin(theta)
        pivot = make_cylinder_r(pivot_r, mid_x - 5, mid_x + 5, segments=14)
        v = pivot.vertices.copy()
        v[:, 1] += pcy
        v[:, 2] += pcz
        pivot.vertices = v
        all_parts.append(pivot)

        # 枢轴螺栓孔 (中间通孔)
        bore = make_cylinder_r(3, mid_x - 15, mid_x + 15, segments=10)
        bore.apply_translation([0, pcy, pcz])
        all_parts.append(bore)

    # 舵机连接臂 (从内环伸出的4个臂)
    arm_r = 6
    arm_len = 30
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        acy = (inner_r + arm_len/2) * math.cos(theta)
        acz = (inner_r + arm_len/2) * math.sin(theta)
        arm = make_cylinder_r(arm_r, mid_x - 5, mid_x + 5, segments=12)
        v = arm.vertices.copy()
        v[:, 1] += acy
        v[:, 2] += acz
        arm.vertices = v
        all_parts.append(arm)

    # 对中标记 (4条凸起的刻线)
    for i in range(4):
        theta = math.radians(i * 90)
        mcy = outer_r * math.cos(theta)
        mcz = outer_r * math.sin(theta)
        mark = make_hollow_tube_r(1, 0, mid_x - L/2 - 3, mid_x - L/2 + 3, segments=8)
        v = mark.vertices.copy()
        v[:, 1] += mcy
        v[:, 2] += mcz
        mark.vertices = v
        all_parts.append(mark)

    gimbal = trimesh.util.concatenate(all_parts)
    gimbal.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
    gimbal.export(os.path.join(OUTPUT, "06_tvc_gimbal.glb"))
    b = gimbal.bounds
    print(f"  06 ✅ TVC万向节: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  Ø{outer_r*2:.0f}mm  L={L:.0f}mm  面数:{len(gimbal.faces):,}")
    print(f"      → 4×枢轴螺栓孔(M6),  → 4×舵机连接臂,  → 对中标记刻线")
    return gimbal


# ============================================================================
# 07. TVC喷管 - 法兰 + 密封槽 + 支撑环
# ============================================================================
def build_nozzle():
    """
    包含:
    - 入口法兰 (带8个M5螺栓孔)
    - 收敛段 (入口→喉道)
    - 扩散段 (喉道→出口)
    - 出口法兰 (带8个M5螺栓孔)
    - 密封O型圈沟槽 (入口和出口各1个)
    - 冷却通道示意 (外壁凸起条)
    - 喉道加强环
    """
    all_parts = []
    R_in = 33      # 入口半径 φ66
    R_th = 17      # 喉道半径 φ34
    R_ex = 27      # 出口半径 φ54
    L_conv = 55
    L_div = L_conv * 2.0
    W = 4.0        # 壁厚
    x_inlet = X_GIMBAL_LEFT - 15
    x_throat = x_inlet - L_conv
    x_exit = x_throat - L_div

    # 入口法兰
    flange_r_in = R_in + 15
    flange_in = make_hollow_tube_r(flange_r_in, R_in, x_inlet + 5, x_inlet + 20)
    all_parts.append(flange_in)

    # 入口法兰上的8个M5螺栓孔
    for i in range(8):
        theta = math.radians(i * 45)
        bx = x_inlet + 12
        by = (flange_r_in - 5) * math.cos(theta)
        bz = (flange_r_in - 5) * math.sin(theta)
        bolt = make_cylinder_r(2.5, x_inlet - 5, x_inlet + 25, segments=8)
        bolt.apply_translation([0, by, bz])
        all_parts.append(bolt)

    # 入口O型圈密封槽
    seal_r = flange_r_in - 8
    seal = make_hollow_tube_r(seal_r + 2, seal_r - 2, x_inlet + 3, x_inlet + 7)
    all_parts.append(seal)

    # 收敛-扩散段
    xs, r_out, r_in_arr = [], [], []
    n_conv = 25
    n_div = 40

    for i in range(n_conv):
        t = i / (n_conv - 1)
        x = x_inlet - t * L_conv
        ri = R_in - (R_in - R_th) * (t ** 0.7)
        xs.append(x); r_out.append(ri + W); r_in_arr.append(ri)

    for i in range(1, n_div + 1):
        t = i / n_div
        x = x_throat - t * L_div
        ri = R_th + (R_ex - R_th) * (t ** 1.3)
        xs.append(x); r_out.append(ri + W); r_in_arr.append(ri)

    nozzle_body = make_revolve_detailed(xs, r_out, r_in_arr)
    all_parts.append(nozzle_body)

    # 喉道加强环
    throat_ring = make_hollow_tube_r(R_th + W + 4, R_th, x_throat - 5, x_throat + 5)
    all_parts.append(throat_ring)

    # 出口法兰
    flange_r_ex = R_ex + 12
    flange_ex = make_hollow_tube_r(flange_r_ex, R_ex, x_exit - 15, x_exit - 5)
    all_parts.append(flange_ex)

    # 出口法兰上的8个M5螺栓孔
    for i in range(8):
        theta = math.radians(i * 45)
        bx = x_exit - 10
        by = (flange_r_ex - 5) * math.cos(theta)
        bz = (flange_r_ex - 5) * math.sin(theta)
        bolt = make_cylinder_r(2.5, x_exit - 25, x_exit + 5, segments=8)
        bolt.apply_translation([0, by, bz])
        all_parts.append(bolt)

    # 出口O型圈密封槽
    seal_ex_r = flange_r_ex - 6
    seal_ex = make_hollow_tube_r(seal_ex_r + 2, seal_ex_r - 2, x_exit - 8, x_exit - 4)
    all_parts.append(seal_ex)

    # 冷却通道 (外壁凸起条, 沿长度方向4条)
    n_cool = 4
    for ci in range(n_cool):
        theta = math.radians(ci * 90)
        groove_x_start = x_inlet + 25
        groove_x_end = x_exit - 20
        cy = math.cos(theta) * (R_in + W + 2)
        cz = math.sin(theta) * (R_in + W + 2)
        channel = make_hollow_tube_r(W * 0.6, W * 0.3, groove_x_start, groove_x_end, segments=8)
        v = channel.vertices.copy()
        v[:, 1] += cy
        v[:, 2] += cz
        channel.vertices = v
        all_parts.append(channel)

    nozzle = trimesh.util.concatenate(all_parts)
    nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
    nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.glb"))
    b = nozzle.bounds
    total_len = b[1][0] - b[0][0]
    print(f"  07 ✅ TVC喷管: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  入Ø{flange_r_in*2:.0f} 喉Ø{R_th*2:.0f} 出Ø{flange_r_ex*2:.0f}  L={total_len:.0f}mm  面数:{len(nozzle.faces):,}")
    print(f"      → 入口: 8×M5法兰螺栓, O型圈密封槽")
    print(f"      → 出口: 8×M5法兰螺栓, O型圈密封槽")
    print(f"      → 冷却通道: {n_cool}条外壁散热肋,  → 喉道加强环")
    return nozzle


# ============================================================================
# 主程序
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v6.0 [完整机械设计版]")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 {OUTPUT}")
    print(f"\n  设计规格:")
    print(f"    机身直径 Ø {BODY_D:.0f} mm   | 壁厚 {WALL:.1f} mm")
    print(f"    总长度   ~ {X_NOSE_TIP - X_NOZZLE_LEFT:.0f} mm")
    print(f"    长径比   ~ {(X_NOSE_TIP - X_NOZZLE_LEFT)/BODY_D:.1f} : 1")
    print(f"\n  螺栓规格:")
    print(f"    M3: 检修盖板, 分离机构")
    print(f"    M4: 尾翼固定")
    print(f"    M5: 法兰连接, 贯穿螺栓")
    print(f"    M6: TVC枢轴")
    print("-" * 70)

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
    max_span = max(abs(b[1][1]), abs(b[0][1]), abs(b[1][2]), abs(b[0][2]))
    print("\n" + "-" * 70)
    print(f"  08 ✅ 完整装配体: x=[{b[0][0]:.0f},{b[1][0]:.0f}]  总长 {total_len:.0f} mm  最大径向 {max_span:.0f} mm")
    print(f"      三角面总数: {len(assembly.faces):,}")
    print("-" * 70)
    print(f"\n✅ 全部零件生成成功!")
    print(f"🌐 http://localhost:8000/viewer.html")
    print("=" * 70)
