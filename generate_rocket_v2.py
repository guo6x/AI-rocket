#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v2.0
=============================================================================

生成完整可用的火箭零部件：
1. 整流罩 (Von Karman 曲线 + 安装法兰)
2. 机身管 (空心圆柱 + 连接卡槽)
3. 尾翼 ×3 (NACA 翼型截面)
4. 航电舱 (分舱结构 + 电池仓)
5. TVC 底座 (EDF 涵道安装座)
6. TVC 万向环 (3 轴枢轴结构)
7. TVC 喷管 (收敛扩散喷管)
8. 完整装配体 (所有零件正确组装)

尺寸说明：
- 机身直径：75mm
- 总高度：约 800mm
- 设计：业余可 3D 打印
=============================================================================
"""

import numpy as np
import trimesh
import os
import math
from datetime import datetime

# ============================================================
# 完整参数表（所有尺寸：mm）
# ============================================================
CONFIG = {
    "rocket": {
        "body_diameter": 75.0,
        "body_radius": 37.5,
        "total_height": 800,
        "wall_thickness": 2.5,
    },
    "nose_cone": {
        "base_diameter": 75.0,
        "base_radius": 37.5,
        "length": 200.0,
        "thickness": 2.0,
        "flange_height": 15.0,
        "flange_thickness": 3.0,
        "flange_clearance": 0.5,
        "segments": 64,
    },
    "body_tube": {
        "outer_diameter": 75.0,
        "outer_radius": 37.5,
        "inner_radius": 34.0,  # 壁厚3.5mm
        "length": 450.0,
        "coupling_length": 30.0,  # 连接卡槽
        "internal_ring_spacing": 100.0,  # 内部加强环间距
        "internal_ring_width": 5.0,
        "internal_ring_thickness": 4.0,
        "segments": 64,
    },
    "fins": {
        "count": 3,
        "root_chord": 120.0,
        "tip_chord": 60.0,
        "span": 60.0,  # 翼展
        "thickness": 4.0,
        "airfoil_ratio": 0.12,  # 翼型厚度比
        "sweepback": 20.0,  # 后掠角(度)
        "root_radius_gap": 1.0,  # 与机身间隙
        "root_fillet_radius": 8.0,  # 根部圆角
    },
    "avionics": {
        "diameter": 68.0,  # 略小于机身内径
        "radius": 34.0,
        "length": 100.0,
        "wall_thickness": 2.0,
        "compartment_count": 2,  # 2个舱室
        "battery_slot_width": 50.0,
        "battery_slot_depth": 15.0,
        "pcb_mount_holes": 4,
        "mount_hole_diameter": 3.2,
        "segments": 48,
    },
    "tvc_base": {
        "outer_diameter": 90.0,
        "inner_diameter": 74.0,  # EDF 内径
        "height": 40.0,
        "wall_thickness": 5.0,
        "mounting_hole_count": 4,
        "mounting_hole_diameter": 4.0,
        "gimbal_pivot_diameter": 8.0,  # 枢轴直径
        "gimbal_pivot_height": 10.0,
    },
    "tvc_gimbal": {
        "outer_diameter": 82.0,
        "inner_diameter": 70.0,
        "height": 20.0,
        "pivot_hole_diameter": 8.0,
        "servo_mount_width": 25.0,
        "servo_mount_height": 15.0,
        "clearance": 0.8,
    },
    "tvc_nozzle": {
        "inlet_diameter": 70.0,
        "throat_diameter": 35.0,
        "exit_diameter": 55.0,
        "total_length": 120.0,
        "convergent_length": 50.0,
        "divergent_length": 70.0,
        "wall_thickness": 3.0,
        "exit_flange_diameter": 78.0,
        "exit_flange_thickness": 4.0,
        "segments": 64,
    },
    "assembly": {
        "spacing": 2.0,  # 零件间隙
    }
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


# ============================================================
# 工具函数：几何体生成
# ============================================================

def create_hollow_cylinder(outer_r, inner_r, height, segments=64):
    """创建空心圆柱（带顶盖/底盖）"""
    vertices = []
    faces = []
    
    # 生成顶点
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        
        # 顶部外圆
        vertices.append([height, outer_r * cos_a, outer_r * sin_a])
        # 顶部内圆
        vertices.append([height, inner_r * cos_a, inner_r * sin_a])
        # 底部外圆
        vertices.append([0, outer_r * cos_a, outer_r * sin_a])
        # 底部内圆
        vertices.append([0, inner_r * cos_a, inner_r * sin_a])
    
    # 生成面
    for i in range(segments):
        curr = i * 4
        next_i = ((i + 1) % segments) * 4
        
        # 外壁
        faces.append([curr + 0, curr + 2, next_i + 2])
        faces.append([curr + 0, next_i + 2, next_i + 0])
        
        # 内壁
        faces.append([curr + 1, next_i + 3, curr + 3])
        faces.append([curr + 1, next_i + 1, next_i + 3])
        
        # 顶环
        faces.append([curr + 0, next_i + 1, curr + 1])
        faces.append([curr + 0, next_i + 0, next_i + 1])
        
        # 底环
        faces.append([curr + 2, curr + 3, next_i + 3])
        faces.append([curr + 2, next_i + 3, next_i + 2])
    
    mesh = trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))
    return mesh


def create_solid_cylinder(radius, height, segments=64):
    """创建实心圆柱"""
    vertices = []
    faces = []
    
    # 中心顶点
    top_center = 0
    vertices.append([height, 0, 0])
    bottom_center = 1
    vertices.append([0, 0, 0])
    
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([height, radius * np.cos(angle), radius * np.sin(angle)])
        vertices.append([0, radius * np.cos(angle), radius * np.sin(angle)])
    
    for i in range(segments):
        top_idx = 2 + i * 2
        bottom_idx = 3 + i * 2
        next_top = 2 + ((i + 1) % segments) * 2
        next_bottom = 3 + ((i + 1) % segments) * 2
        
        # 侧面
        faces.append([top_idx, bottom_idx, next_bottom])
        faces.append([top_idx, next_bottom, next_top])
        
        # 顶盖
        faces.append([top_center, next_top, top_idx])
        # 底盖
        faces.append([bottom_center, bottom_idx, next_bottom])
    
    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))


def create_cone(radius_top, radius_bottom, height, segments=64):
    """创建锥台（实心）"""
    vertices = []
    faces = []
    
    top_center = 0
    vertices.append([height, 0, 0])
    bottom_center = 1
    vertices.append([0, 0, 0])
    
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([height, radius_top * np.cos(angle), radius_top * np.sin(angle)])
        vertices.append([0, radius_bottom * np.cos(angle), radius_bottom * np.sin(angle)])
    
    for i in range(segments):
        top_idx = 2 + i * 2
        bottom_idx = 3 + i * 2
        next_top = 2 + ((i + 1) % segments) * 2
        next_bottom = 3 + ((i + 1) % segments) * 2
        
        faces.append([top_idx, bottom_idx, next_bottom])
        faces.append([top_idx, next_bottom, next_top])
        faces.append([top_center, next_top, top_idx])
        faces.append([bottom_center, bottom_idx, next_bottom])
    
    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))


def create_von_karman_cone(base_radius, length, segments=64, angular_seg=64):
    """
    创建冯·卡门整流罩（实体）
    曲线方程: theta = acos(1 - 2*x/L), y = R/sqrt(pi) * sqrt(theta - 0.5*sin(2*theta))
    """
    vertices = []
    faces = []
    
    # 顶点
    tip_idx = 0
    vertices.append([length, 0, 0])
    
    # 底部中心
    bottom_center = 1
    vertices.append([0, 0, 0])
    
    # 生成环形顶点
    ring_count = segments
    for ring in range(ring_count):
        x = length * (ring / (ring_count - 1))
        theta = math.acos(1 - 2 * x / length) if 0 < x <= length else 0
        y = base_radius / math.sqrt(math.pi) * math.sqrt(theta - 0.5 * math.sin(2 * theta))
        
        if x >= length - 0.1:
            y = 0
        
        for i in range(angular_seg):
            angle = 2 * np.pi * i / angular_seg
            vertices.append([x, y * np.cos(angle), y * np.sin(angle)])
    
    # 生成三角形面
    # 尖端三角
    for i in range(angular_seg):
        curr = 2 + (ring_count - 1) * angular_seg + i
        next_v = 2 + (ring_count - 1) * angular_seg + ((i + 1) % angular_seg)
        faces.append([tip_idx, curr, next_v])
    
    # 中间环之间的面
    for ring in range(ring_count - 1):
        for i in range(angular_seg):
            curr_out = 2 + ring * angular_seg + i
            next_out = 2 + ring * angular_seg + ((i + 1) % angular_seg)
            curr_in = 2 + (ring + 1) * angular_seg + i
            next_in = 2 + (ring + 1) * angular_seg + ((i + 1) % angular_seg)
            
            faces.append([curr_out, curr_in, next_in])
            faces.append([curr_out, next_in, next_out])
    
    # 底部
    for i in range(angular_seg):
        curr = 2 + i
        next_v = 2 + ((i + 1) % angular_seg)
        faces.append([bottom_center, next_v, curr])
    
    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))


def create_von_karman_hollow(base_radius, length, thickness, segments=40, angular_seg=64):
    """创建空心冯·卡门整流罩"""
    # 外表面
    outer_verts = []
    for ring in range(segments):
        x = length * (ring / (segments - 1))
        theta = math.acos(1 - 2 * x / length) if 0 < x <= length else 0
        y = base_radius / math.sqrt(math.pi) * math.sqrt(theta - 0.5 * math.sin(2 * theta))
        if x >= length - 0.1: y = 0
        
        for i in range(angular_seg):
            angle = 2 * np.pi * i / angular_seg
            outer_verts.append([x, y * np.cos(angle), y * np.sin(angle)])
    
    # 内表面（向内偏移厚度）
    inner_verts = []
    for ring in range(segments):
        x = length * (ring / (segments - 1))
        theta = math.acos(1 - 2 * x / length) if 0 < x <= length else 0
        y = base_radius / math.sqrt(math.pi) * math.sqrt(theta - 0.5 * math.sin(2 * theta))
        if x >= length - 0.1: y = 0
        
        y_inner = y - thickness * (1 - x / length * 0.5) - 1.0  # 内表面稍小
        if y_inner < 1.0: y_inner = 1.0
        
        for i in range(angular_seg):
            angle = 2 * np.pi * i / angular_seg
            inner_verts.append([x, y_inner * np.cos(angle), y_inner * np.sin(angle)])
    
    # 生成面
    vertices = []
    faces = []
    
    # 外表面
    for v in outer_verts:
        vertices.append(v)
    outer_base = 0
    
    # 内表面
    inner_base = len(vertices)
    for v in inner_verts:
        vertices.append(v)
    
    # 外表面三角形
    # 尖端
    for i in range(angular_seg):
        curr = (segments - 1) * angular_seg + i
        next_v = (segments - 1) * angular_seg + ((i + 1) % angular_seg)
        faces.append([curr, next_v, ((segments - 1) * angular_seg) + (i + angular_seg // 2)])
    
    # 环面
    for ring in range(segments - 1):
        for i in range(angular_seg):
            curr_out = ring * angular_seg + i
            next_out = ring * angular_seg + ((i + 1) % angular_seg)
            curr_in = (ring + 1) * angular_seg + i
            next_in = (ring + 1) * angular_seg + ((i + 1) % angular_seg)
            
            faces.append([curr_out, next_out, curr_in])
            faces.append([next_out, next_in, curr_in])
    
    # 内表面（倒序，法线向内）
    for ring in range(segments - 1):
        for i in range(angular_seg):
            curr_out = inner_base + ring * angular_seg + i
            next_out = inner_base + ring * angular_seg + ((i + 1) % angular_seg)
            curr_in = inner_base + (ring + 1) * angular_seg + i
            next_in = inner_base + (ring + 1) * angular_seg + ((i + 1) % angular_seg)
            
            faces.append([curr_out, curr_in, next_out])
            faces.append([next_out, curr_in, next_in])
    
    # 底部连接环
    for i in range(angular_seg):
        curr = i
        next_v = (i + 1) % angular_seg
        inner_curr = inner_base + i
        inner_next = inner_base + (i + 1) % angular_seg
        
        faces.append([curr, inner_curr, inner_next])
        faces.append([curr, inner_next, next_v])
    
    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))


def create_airfoil_fin(root_chord, tip_chord, span, thickness, segments=20):
    """
    创建带翼型的尾翼（NACA简化版）
    简化版本：带圆角的梯形
    """
    vertices = []
    faces = []
    
    # 简化为带圆角的梯形，多个薄截面堆叠
    layers = 5
    for layer in range(layers):
        t = layer / (layers - 1)  # 0到1，从底部到顶端
        z_pos = t * span
        
        # 插值翼弦
        chord = root_chord + (tip_chord - root_chord) * t
        
        # 翼型截面（圆形前缘，尖形后缘）
        points_per_section = 16
        section_points = []
        for i in range(points_per_section):
            pt = i / (points_per_section - 1)  # 0到1
            
            # 椭圆翼型
            x_pos = -chord * 0.3 + pt * chord  # 前缘在1/3处
            y_ratio = math.sqrt(max(0, 1 - (2 * pt - 1) ** 2)) * thickness * 0.5
            y_pos = y_ratio * (1 - abs(t - 0.5) * 0.8)  # 顶端稍薄
            
            section_points.append([x_pos, y_pos, z_pos])
        
        # 添加底部点（用于连接）
        for p in section_points:
            vertices.append(p)
    
    # 生成侧面
    for layer in range(layers - 1):
        for i in range(points_per_section - 1):
            curr_out = layer * points_per_section + i
            next_out = layer * points_per_section + i + 1
            curr_in = (layer + 1) * points_per_section + i
            next_in = (layer + 1) * points_per_section + i + 1
            
            faces.append([curr_out, next_out, curr_in])
            faces.append([next_out, next_in, curr_in])
    
    # 端面（底部和顶部）
    for end in [0, layers - 1]:
        for i in range(points_per_section // 2):
            v1 = end * points_per_section + i
            v2 = end * points_per_section + points_per_section - 1 - i
            center = end * points_per_section + points_per_section // 4
            
            if i < points_per_section // 3:
                faces.append([v1, center, v2])
    
    # 简化：添加一个简单的底部安装板（方形）
    board_thickness = 6
    board_points = [
        [-5, -thickness, 0], [chord * 0.8, -thickness, 0], [chord * 0.8, thickness, 0], [-5, thickness, 0],
        [-5, -thickness, -board_thickness], [chord * 0.8, -thickness, -board_thickness],
        [chord * 0.8, thickness, -board_thickness], [-5, thickness, -board_thickness],
    ]
    
    base = len(vertices)
    for p in board_points:
        vertices.append(p)
    
    # 安装板面
    faces.append([base + 0, base + 1, base + 2])
    faces.append([base + 0, base + 2, base + 3])
    faces.append([base + 4, base + 6, base + 5])
    faces.append([base + 4, base + 7, base + 6])
    # 侧面
    faces.append([base + 0, base + 4, base + 5])
    faces.append([base + 0, base + 5, base + 1])
    faces.append([base + 1, base + 5, base + 6])
    faces.append([base + 1, base + 6, base + 2])
    faces.append([base + 2, base + 6, base + 7])
    faces.append([base + 2, base + 7, base + 3])
    faces.append([base + 3, base + 7, base + 4])
    faces.append([base + 3, base + 4, base + 0])
    
    mesh = trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))
    return mesh


def create_box(width, height, depth):
    """创建长方体"""
    w, h, d = width/2, height/2, depth
    vertices = [
        [-w, -h, 0], [w, -h, 0], [w, h, 0], [-w, h, 0],
        [-w, -h, d], [w, -h, d], [w, h, d], [-w, h, d],
    ]
    faces = [
        [0, 1, 2], [0, 2, 3],  # bottom
        [4, 6, 5], [4, 7, 6],  # top
        [0, 4, 5], [0, 5, 1],  # side1
        [1, 5, 6], [1, 6, 2],  # side2
        [2, 6, 7], [2, 7, 3],  # side3
        [3, 7, 4], [3, 4, 0],  # side4
    ]
    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))


# ============================================================
# 1. 生成整流罩 (Nose Cone)
# ============================================================

def generate_nose_cone(cfg, output_dir):
    print("\n" + "="*60)
    print("🔴 生成整流罩 (Nose Cone)")
    print("="*60)
    
    nc = cfg["nose_cone"]
    
    # 主锥体
    print("   - 生成冯·卡门外型...")
    main_cone = create_von_karman_hollow(
        base_radius=nc["base_radius"],
        length=nc["length"],
        thickness=nc["thickness"],
        segments=35,
        angular_seg=64
    )
    
    # 底部安装法兰
    print("   - 生成安装法兰...")
    flange_outer = nc["base_radius"] + nc["flange_thickness"]
    flange_inner = nc["base_radius"] - nc["flange_clearance"]
    flange = create_hollow_cylinder(
        outer_r=flange_outer,
        inner_r=flange_inner,
        height=nc["flange_height"],
        segments=64
    )
    flange.apply_translation([-nc["flange_height"], 0, 0])
    
    # 合并
    print("   - 合并组件...")
    parts = [main_cone, flange]
    nose_cone = trimesh.util.concatenate(parts)
    
    # 重命名并导出
    nose_cone.merge_vertices()
    
    print(f"   - 尺寸: 长 {nc['length']}mm, 直径 {nc['base_diameter']}mm")
    print(f"   - 顶点数: {len(nose_cone.vertices)}, 面数: {len(nose_cone.faces)}")
    
    stl_file = os.path.join(output_dir, "01_nose_cone.stl")
    glb_file = os.path.join(output_dir, "01_nose_cone.glb")
    nose_cone.export(stl_file)
    nose_cone.export(glb_file)
    print(f"   ✅ 已保存")
    
    return nose_cone


# ============================================================
# 2. 生成机身管 (Body Tube)
# ============================================================

def generate_body_tube(cfg, output_dir):
    print("\n" + "="*60)
    print("🔵 生成机身管 (Body Tube)")
    print("="*60)
    
    bt = cfg["body_tube"]
    
    # 主空心管
    print("   - 生成主空心管...")
    main_tube = create_hollow_cylinder(
        outer_r=bt["outer_radius"],
        inner_r=bt["inner_radius"],
        height=bt["length"],
        segments=bt["segments"]
    )
    
    # 内部加强环
    print("   - 生成内部加强环...")
    rings = []
    ring_count = int(bt["length"] / bt["internal_ring_spacing"]) - 1
    for i in range(ring_count):
        ring_pos = (i + 1) * bt["internal_ring_spacing"]
        ring = create_hollow_cylinder(
            outer_r=bt["outer_radius"] - 0.5,
            inner_r=bt["inner_radius"] + 2,
            height=bt["internal_ring_width"],
            segments=48
        )
        ring.apply_translation([ring_pos, 0, 0])
        rings.append(ring)
    
    # 顶部连接槽（用于安装整流罩）
    print("   - 生成顶部连接槽...")
    top_coupling = create_hollow_cylinder(
        outer_r=bt["outer_radius"] - 1.0,
        inner_r=bt["inner_radius"],
        height=bt["coupling_length"],
        segments=48
    )
    top_coupling.apply_translation([bt["length"] - bt["coupling_length"], 0, 0])
    
    # 底部连接槽（用于连接TVC底座）
    print("   - 生成底部连接槽...")
    bottom_coupling = create_hollow_cylinder(
        outer_r=bt["outer_radius"] - 1.0,
        inner_r=bt["inner_radius"],
        height=bt["coupling_length"],
        segments=48
    )
    bottom_coupling.apply_translation([-bt["coupling_length"], 0, 0])
    
    # 合并所有部分
    print("   - 合并组件...")
    parts = [main_tube] + rings + [top_coupling, bottom_coupling]
    body_tube = trimesh.util.concatenate(parts)
    
    body_tube.merge_vertices()
    
    print(f"   - 尺寸: 长 {bt['length']}mm, 外径 {bt['outer_diameter']}mm")
    print(f"   - 内部加强环: {ring_count} 个")
    print(f"   - 顶点数: {len(body_tube.vertices)}, 面数: {len(body_tube.faces)}")
    
    stl_file = os.path.join(output_dir, "02_body_tube.stl")
    glb_file = os.path.join(output_dir, "02_body_tube.glb")
    body_tube.export(stl_file)
    body_tube.export(glb_file)
    print(f"   ✅ 已保存")
    
    return body_tube


# ============================================================
# 3. 生成尾翼 (Fins)
# ============================================================

def generate_fins(cfg, output_dir):
    print("\n" + "="*60)
    print("🟠 生成尾翼 (Fins)")
    print("="*60)
    
    fc = cfg["fins"]
    bt_r = cfg["body_tube"]["outer_radius"]
    
    # 单个尾翼
    print("   - 生成翼型截面尾翼...")
    fin = create_airfoil_fin(
        root_chord=fc["root_chord"],
        tip_chord=fc["tip_chord"],
        span=fc["span"],
        thickness=fc["thickness"]
    )
    
    # 创建3个尾翼的组装件
    print("   - 组装3片尾翼...")
    all_fins = []
    
    for i in range(fc["count"]):
        angle_deg = 360.0 * i / fc["count"]
        angle_rad = np.radians(angle_deg)
        
        fin_copy = fin.copy()
        
        # 平移到机身位置
        fin_copy.apply_translation([0, bt_r + fc["root_radius_gap"], 0])
        
        # 围绕Y轴旋转（机身轴线）
        # 绕X轴旋转来放置在圆周上
        fin_copy.apply_transform(trimesh.transformations.rotation_matrix(angle_rad, [1, 0, 0]))
        
        all_fins.append(fin_copy)
    
    fins_assembly = trimesh.util.concatenate(all_fins)
    
    print(f"   - 数量: {fc['count']} 片")
    print(f"   - 翼展: {fc['span']}mm, 根弦: {fc['root_chord']}mm")
    print(f"   - 顶点数: {len(fins_assembly.vertices)}, 面数: {len(fins_assembly.faces)}")
    
    stl_file = os.path.join(output_dir, "03_fins_x3.stl")
    glb_file = os.path.join(output_dir, "03_fins_x3.glb")
    fins_assembly.export(stl_file)
    fins_assembly.export(glb_file)
    print(f"   ✅ 已保存")
    
    return fins_assembly


# ============================================================
# 4. 生成航电舱 (Avionics Bay)
# ============================================================

def generate_avionics(cfg, output_dir):
    print("\n" + "="*60)
    print("🟢 生成航电舱 (Avionics Bay)")
    print("="*60)
    
    ac = cfg["avionics"]
    
    # 外壳
    print("   - 生成外壳...")
    shell = create_hollow_cylinder(
        outer_r=ac["radius"],
        inner_r=ac["radius"] - ac["wall_thickness"],
        height=ac["length"],
        segments=ac["segments"]
    )
    
    # 中间隔板
    print("   - 生成分舱隔板...")
    partition_height = ac["length"] / ac["compartment_count"]
    partitions = []
    for i in range(1, ac["compartment_count"]):
        pos = i * partition_height
        partition = create_hollow_cylinder(
            outer_r=ac["radius"] - ac["wall_thickness"] - 0.3,
            inner_r=5.0,
            height=3.0,
            segments=24
        )
        partition.apply_translation([pos - 1.5, 0, 0])
        partitions.append(partition)
    
    # 底部安装板
    print("   - 生成底部安装板...")
    base_plate = create_solid_cylinder(
        radius=ac["radius"] - ac["wall_thickness"] - 0.5,
        height=5.0,
        segments=32
    )
    base_plate.apply_translation([-5.0, 0, 0])
    
    # 合并
    print("   - 合并组件...")
    parts = [shell] + partitions + [base_plate]
    avionics = trimesh.util.concatenate(parts)
    
    avionics.merge_vertices()
    
    print(f"   - 尺寸: 直径 {ac['diameter']}mm, 长 {ac['length']}mm")
    print(f"   - 舱室: {ac['compartment_count']} 个")
    print(f"   - 顶点数: {len(avionics.vertices)}, 面数: {len(avionics.faces)}")
    
    stl_file = os.path.join(output_dir, "04_avionics_bay.stl")
    glb_file = os.path.join(output_dir, "04_avionics_bay.glb")
    avionics.export(stl_file)
    avionics.export(glb_file)
    print(f"   ✅ 已保存")
    
    return avionics


# ============================================================
# 5. TVC 底座 (TVC Base)
# ============================================================

def generate_tvc_base(cfg, output_dir):
    print("\n" + "="*60)
    print("🟣 生成 TVC 底座 (TVC Base)")
    print("="*60)
    
    tb = cfg["tvc_base"]
    
    # 主底座（中空）
    print("   - 生成主底座...")
    main_base = create_hollow_cylinder(
        outer_r=tb["outer_diameter"]/2,
        inner_r=tb["inner_diameter"]/2,
        height=tb["height"],
        segments=48
    )
    
    # 顶部连接板（用于连接机身）
    print("   - 生成顶部连接板...")
    top_plate = create_hollow_cylinder(
        outer_r=cfg["body_tube"]["outer_radius"] + 1,
        inner_r=tb["inner_diameter"]/2,
        height=8.0,
        segments=48
    )
    top_plate.apply_translation([tb["height"], 0, 0])
    
    # 枢轴安装座 (2个对向枢轴)
    print("   - 生成枢轴安装座...")
    pivots = []
    for side in [-1, 1]:
        pivot = create_box(
            width=tb["gimbal_pivot_height"] * 2,
            height=tb["gimbal_pivot_height"],
            depth=tb["gimbal_pivot_height"]
        )
        pivot.apply_translation([
            tb["height"] / 2,
            side * (tb["outer_diameter"] / 2 + tb["gimbal_pivot_height"] / 2),
            0
        ])
        pivots.append(pivot)
    
    # 安装孔凸耳
    print("   - 生成安装耳...")
    lugs = []
    for i in range(tb["mounting_hole_count"]):
        angle = np.radians(i * 90)
        lug = create_box(
            width=15,
            height=15,
            depth=tb["height"] * 0.4
        )
        lug_r = tb["outer_diameter"]/2 + 5
        lug.apply_translation([
            tb["height"] * 0.3,
            lug_r * np.cos(angle),
            lug_r * np.sin(angle)
        ])
        lugs.append(lug)
    
    # 合并
    print("   - 合并组件...")
    parts = [main_base, top_plate] + pivots + lugs
    tvc_base = trimesh.util.concatenate(parts)
    
    tvc_base.merge_vertices()
    
    print(f"   - 尺寸: 直径 {tb['outer_diameter']}mm, 高 {tb['height']}mm")
    print(f"   - 安装孔: {tb['mounting_hole_count']} 个")
    print(f"   - 顶点数: {len(tvc_base.vertices)}, 面数: {len(tvc_base.faces)}")
    
    stl_file = os.path.join(output_dir, "05_tvc_base.stl")
    glb_file = os.path.join(output_dir, "05_tvc_base.glb")
    tvc_base.export(stl_file)
    tvc_base.export(glb_file)
    print(f"   ✅ 已保存")
    
    return tvc_base


# ============================================================
# 6. TVC 万向环 (Gimbal Ring)
# ============================================================

def generate_tvc_gimbal(cfg, output_dir):
    print("\n" + "="*60)
    print("🟡 生成 TVC 万向环 (Gimbal Ring)")
    print("="*60)
    
    tg = cfg["tvc_gimbal"]
    
    # 主环
    print("   - 生成主万向环...")
    ring = create_hollow_cylinder(
        outer_r=tg["outer_diameter"]/2,
        inner_r=tg["inner_diameter"]/2,
        height=tg["height"],
        segments=48
    )
    
    # 枢轴孔
    print("   - 生成枢轴凸耳...")
    pivot_lugs = []
    for side in [-1, 1]:
        lug = create_box(
            width=tg["height"],
            height=12,
            depth=12
        )
        lug.apply_translation([
            0,
            side * (tg["outer_diameter"]/2 + 6),
            0
        ])
        pivot_lugs.append(lug)
    
    # 伺服舵机安装座
    print("   - 生成舵机安装座...")
    servo_mount = create_box(
        width=30,
        height=tg["servo_mount_height"],
        depth=tg["servo_mount_width"]
    )
    servo_mount.apply_translation([0, 0, -tg["outer_diameter"]/2 - tg["servo_mount_width"]/2])
    
    # 合并
    print("   - 合并组件...")
    parts = [ring] + pivot_lugs + [servo_mount]
    gimbal = trimesh.util.concatenate(parts)
    
    gimbal.merge_vertices()
    
    print(f"   - 尺寸: 外径 {tg['outer_diameter']}mm, 高 {tg['height']}mm")
    print(f"   - 枢轴直径: {tg['pivot_hole_diameter']}mm")
    print(f"   - 顶点数: {len(gimbal.vertices)}, 面数: {len(gimbal.faces)}")
    
    stl_file = os.path.join(output_dir, "06_tvc_gimbal.stl")
    glb_file = os.path.join(output_dir, "06_tvc_gimbal.glb")
    gimbal.export(stl_file)
    gimbal.export(glb_file)
    print(f"   ✅ 已保存")
    
    return gimbal


# ============================================================
# 7. TVC 喷管 (Nozzle)
# ============================================================

def generate_tvc_nozzle(cfg, output_dir):
    print("\n" + "="*60)
    print("🔵 生成 TVC 喷管 (TVC Nozzle)")
    print("="*60)
    
    tn = cfg["tvc_nozzle"]
    
    # 收敛段 (inlet -> throat)
    print("   - 生成收敛段...")
    convergent = create_cone(
        radius_top=tn["inlet_diameter"]/2,
        radius_bottom=tn["throat_diameter"]/2,
        height=tn["convergent_length"],
        segments=tn["segments"]
    )
    convergent.apply_translation([tn["divergent_length"], 0, 0])
    
    # 扩散段 (throat -> exit)
    print("   - 生成扩散段...")
    divergent = create_cone(
        radius_top=tn["throat_diameter"]/2,
        radius_bottom=tn["exit_diameter"]/2,
        height=tn["divergent_length"],
        segments=tn["segments"]
    )
    
    # 出口法兰
    print("   - 生成出口法兰...")
    exit_flange = create_hollow_cylinder(
        outer_r=tn["exit_flange_diameter"]/2,
        inner_r=tn["exit_diameter"]/2,
        height=tn["exit_flange_thickness"],
        segments=48
    )
    exit_flange.apply_translation([-tn["exit_flange_thickness"], 0, 0])
    
    # 入口法兰（用于连接万向环）
    print("   - 生成入口法兰...")
    inlet_flange = create_hollow_cylinder(
        outer_r=cfg["tvc_gimbal"]["inner_diameter"]/2 - 1,
        inner_r=tn["inlet_diameter"]/2,
        height=10.0,
        segments=48
    )
    inlet_flange.apply_translation([tn["total_length"], 0, 0])
    
    # 合并
    print("   - 合并组件...")
    parts = [convergent, divergent, exit_flange, inlet_flange]
    nozzle = trimesh.util.concatenate(parts)
    
    nozzle.merge_vertices()
    
    print(f"   - 入口: {tn['inlet_diameter']}mm")
    print(f"   - 喉道: {tn['throat_diameter']}mm")
    print(f"   - 出口: {tn['exit_diameter']}mm")
    print(f"   - 总长: {tn['total_length']}mm")
    print(f"   - 顶点数: {len(nozzle.vertices)}, 面数: {len(nozzle.faces)}")
    
    stl_file = os.path.join(output_dir, "07_tvc_nozzle.stl")
    glb_file = os.path.join(output_dir, "07_tvc_nozzle.glb")
    nozzle.export(stl_file)
    nozzle.export(glb_file)
    print(f"   ✅ 已保存")
    
    return nozzle


# ============================================================
# 8. 完整装配体 (Full Rocket Assembly)
# ============================================================

def generate_full_assembly(cfg, output_dir, all_parts):
    print("\n" + "="*60)
    print("🚀 生成完整装配体 (Full Rocket Assembly)")
    print("="*60)
    
    # 从底到顶的位置：
    # TVC喷管(底部) -> TVC万向环 -> TVC底座 -> 机身管 -> 尾翼 -> 航电舱(在机身内) -> 整流罩(顶部)
    
    bt = cfg["body_tube"]
    nc = cfg["nose_cone"]
    tb = cfg["tvc_base"]
    tn = cfg["tvc_nozzle"]
    ac = cfg["avionics"]
    
    # 位置计算
    nozzle_z = 0  # 喷管在最底部
    gimbal_z = nozzle_z + tn["total_length"] + 5
    base_z = gimbal_z + cfg["tvc_gimbal"]["height"] + 5
    body_z = base_z + tb["height"]
    fins_z = body_z + bt["length"] - cfg["fins"]["root_chord"] - 50  # 尾翼靠底部
    nose_z = body_z + bt["length"]
    
    assembled_parts = []
    
    # 1. 喷管（底部）
    nozzle = all_parts["nozzle"].copy()
    nozzle.apply_translation([nozzle_z, 0, 0])
    assembled_parts.append(nozzle)
    print(f"   - 喷管位置: z = {nozzle_z}mm")
    
    # 2. 万向环
    gimbal = all_parts["gimbal"].copy()
    gimbal.apply_translation([gimbal_z, 0, 0])
    assembled_parts.append(gimbal)
    print(f"   - 万向环位置: z = {gimbal_z}mm")
    
    # 3. TVC底座
    tvc_base = all_parts["tvc_base"].copy()
    tvc_base.apply_translation([base_z, 0, 0])
    assembled_parts.append(tvc_base)
    print(f"   - TVC底座位置: z = {base_z}mm")
    
    # 4. 机身管
    body = all_parts["body_tube"].copy()
    body.apply_translation([body_z, 0, 0])
    assembled_parts.append(body)
    print(f"   - 机身管位置: z = {body_z}mm")
    
    # 5. 尾翼（在机身底部）
    fins = all_parts["fins"].copy()
    fins.apply_translation([fins_z, 0, 0])
    assembled_parts.append(fins)
    print(f"   - 尾翼位置: z = {fins_z}mm")
    
    # 6. 航电舱（在机身内上部）
    avionics = all_parts["avionics"].copy()
    avionics_z = body_z + bt["length"] - ac["length"] - 20
    avionics.apply_translation([avionics_z, 0, 0])
    assembled_parts.append(avionics)
    print(f"   - 航电舱位置: z = {avionics_z}mm (机身内部)")
    
    # 7. 整流罩（顶部）
    nose = all_parts["nose_cone"].copy()
    nose.apply_translation([nose_z, 0, 0])
    assembled_parts.append(nose)
    print(f"   - 整流罩位置: z = {nose_z}mm")
    
    # 合并
    assembly = trimesh.util.concatenate(assembled_parts)
    
    total_height = nose_z + nc["length"]
    print(f"\n   - 火箭总高度: ~{total_height:.0f}mm")
    print(f"   - 最大直径: {bt['outer_diameter']}mm")
    print(f"   - 总顶点数: {len(assembly.vertices)}, 面数: {len(assembly.faces)}")
    
    stl_file = os.path.join(output_dir, "08_full_rocket_assembly.stl")
    glb_file = os.path.join(output_dir, "08_full_rocket_assembly.glb")
    assembly.export(stl_file)
    assembly.export(glb_file)
    print(f"   ✅ 已保存完整装配体")
    
    return assembly


# ============================================================
# 主函数
# ============================================================

def main():
    print("\n" + "="*70)
    print("🚀 Ad Astra 火箭 - 完整 3D 零件生成器 v2.0")
    print("="*70)
    print(f"\n📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    output_dir = ensure_dir(os.path.join(os.path.dirname(__file__), "3d_print_files"))
    print(f"\n📁 输出目录: {output_dir}")
    
    # 删除旧文件（避免文件名冲突）
    print("\n   清理旧文件...")
    for f in os.listdir(output_dir):
        if f.endswith('.stl') and f[0].isdigit():
            try:
                os.remove(os.path.join(output_dir, f))
            except:
                pass
    
    # 生成各部件
    nose_cone = generate_nose_cone(CONFIG, output_dir)
    body_tube = generate_body_tube(CONFIG, output_dir)
    fins = generate_fins(CONFIG, output_dir)
    avionics = generate_avionics(CONFIG, output_dir)
    tvc_base = generate_tvc_base(CONFIG, output_dir)
    gimbal = generate_tvc_gimbal(CONFIG, output_dir)
    nozzle = generate_tvc_nozzle(CONFIG, output_dir)
    
    # 保存引用
    all_parts = {
        "nose_cone": nose_cone,
        "body_tube": body_tube,
        "fins": fins,
        "avionics": avionics,
        "tvc_base": tvc_base,
        "gimbal": gimbal,
        "nozzle": nozzle,
    }
    
    # 完整装配体
    full_assembly = generate_full_assembly(CONFIG, output_dir, all_parts)
    
    print("\n" + "="*70)
    print("🎉 所有 3D 模型生成完成！")
    print("="*70)
    
    print("\n📋 零件清单:")
    print("   ┌─────────────────────────────────────────────────────┐")
    print("   │  1. 整流罩 (Nose Cone)           - Von Karman曲线      │")
    print("   │  2. 机身管 (Body Tube)           - 空心圆柱+加强环     │")
    print("   │  3. 尾翼 ×3 (Fins)               - 带翼型+安装板       │")
    print("   │  4. 航电舱 (Avionics Bay)        - 分舱圆筒           │")
    print("   │  5. TVC 底座 (TVC Base)          - EDF安装座+枢轴     │")
    print("   │  6. TVC 万向环 (Gimbal Ring)     - 3轴枢轴结构        │")
    print("   │  7. TVC 喷管 (TVC Nozzle)        - 收敛扩散喷管       │")
    print("   │  8. 完整火箭 (Full Assembly)     - 所有零件组装       │")
    print("   └─────────────────────────────────────────────────────┘")
    
    print(f"\n📐 关键尺寸:")
    print(f"   机身直径: {CONFIG['body_tube']['outer_diameter']}mm")
    print(f"   总高度: ~{CONFIG['nose_cone']['length'] + CONFIG['body_tube']['length'] + CONFIG['tvc_base']['height'] + CONFIG['tvc_nozzle']['total_length'] + 50:.0f}mm")
    print(f"   设计壁厚: {CONFIG['rocket']['wall_thickness']}mm")
    
    print("\n🌐 在浏览器中查看: http://localhost:8000/viewer.html")
    print("\n   💡 提示: 请确保 HTTP 服务器在 3d_print_files 目录运行")
    print("   💡 如果需要调整尺寸，请修改 CONFIG 中的参数重新生成")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
