#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 火箭模型详细验证脚本
检查每个零件的几何质量、连接处的重合度、螺栓对齐
"""
import numpy as np
import trimesh
import os

OUTPUT = r"D:\AI_rocket\3d_print_files"

print("="*70)
print("🔍 火箭模型详细验证")
print("="*70)

# 加载所有零件
parts = {}
files = [
    "01_nose_cone.stl",
    "02_body_tube.stl",
    "03_fins.stl",
    "04_avionics_bay.stl",
    "05_tvc_base.stl",
    "06_tvc_gimbal.stl",
    "07_tvc_nozzle.stl",
    "08_bolts_nuts.stl",
    "00_full_rocket_assembly.stl",
]

for f in files:
    path = os.path.join(OUTPUT, f)
    if os.path.exists(path):
        mesh = trimesh.load(path)
        parts[f] = mesh
        print(f"\n📄 {f}:")
        print(f"  顶点数: {len(mesh.vertices):,}")
        print(f"  面数:   {len(mesh.faces):,}")
        print(f"  边界:   X=[{mesh.bounds[0][0]:.2f}, {mesh.bounds[1][0]:.2f}]")
        print(f"          Y=[{mesh.bounds[0][1]:.2f}, {mesh.bounds[1][1]:.2f}]")
        print(f"          Z=[{mesh.bounds[0][2]:.2f}, {mesh.bounds[1][2]:.2f}]")
        # 检查是否为水密
        print(f"  水密:   {'✅' if mesh.is_watertight else '❌'}")
        # 检查法线一致性
        print(f"  体积:   {mesh.volume:.0f} mm³" if mesh.is_watertight else "  体积:   N/A (非水密)")

# 详细检查连接处
print("\n" + "="*70)
print("🔗 连接处重合度详细检查")
print("="*70)

joints = [
    ("整流罩-机身", "01_nose_cone.stl", "02_body_tube.stl", 0),
    ("机身-TVC", "02_body_tube.stl", "05_tvc_base.stl", -600),
    ("TVC-万向节", "05_tvc_base.stl", "06_tvc_gimbal.stl", -680),
    ("万向节-喷管", "06_tvc_gimbal.stl", "07_tvc_nozzle.stl", -725),
]

for name, p1, p2, x_joint in joints:
    if p1 in parts and p2 in parts:
        m1 = parts[p1]
        m2 = parts[p2]
        # 检查 x=x_joint 截面
        slice1 = m1.section(plane_origin=[x_joint, 0, 0], plane_normal=[1, 0, 0])
        slice2 = m2.section(plane_origin=[x_joint, 0, 0], plane_normal=[1, 0, 0])
        print(f"\n🔗 {name} (x={x_joint}):")
        if slice1 is not None and slice2 is not None:
            p1_poly = slice1.to_planar()[0]
            p2_poly = slice2.to_planar()[0]
            # 检查两个截面是否重合
            print(f"  零件1截面: {len(p1_poly.vertices)}顶点")
            print(f"  零件2截面: {len(p2_poly.vertices)}顶点")
            # 找半径
            r1_max = np.max(np.linalg.norm(p1_poly.vertices, axis=1)) if len(p1_poly.vertices) > 0 else 0
            r2_max = np.max(np.linalg.norm(p2_poly.vertices, axis=1)) if len(p2_poly.vertices) > 0 else 0
            print(f"  零件1最大半径: {r1_max:.2f}mm")
            print(f"  零件2最大半径: {r2_max:.2f}mm")
            print(f"  半径差: {abs(r1_max - r2_max):.2f}mm")
        else:
            print(f"  ❌ 截面获取失败")

# 检查装配体
print("\n" + "="*70)
print("🚀 完整装配体检查")
print("="*70)

if "00_full_rocket_assembly.stl" in parts:
    asm = parts["00_full_rocket_assembly.stl"]
    print(f"\n总面数: {len(asm.faces):,}")
    print(f"水密: {'✅' if asm.is_watertight else '❌'}")
    print(f"体积: {asm.volume:.0f} mm³")
    print(f"长度: {asm.bounds[1][0] - asm.bounds[0][0]:.0f}mm")
    print(f"最大半径: {np.max(np.linalg.norm(asm.vertices[:,1:], axis=1)):.1f}mm")

    # 检查自相交
    print(f"\n检查几何问题...")
    # 退化三角形
    degenerate = 0
    for face in asm.faces:
        v = asm.vertices[face]
        area = 0.5 * np.linalg.norm(np.cross(v[1]-v[0], v[2]-v[0]))
        if area < 0.001:
            degenerate += 1
    print(f"退化三角形: {degenerate}")

    # 检查重复顶点
    unique_v = np.unique(asm.vertices, axis=0)
    print(f"唯一顶点数: {len(unique_v)}/{len(asm.vertices)}")

# 检查螺栓
if "08_bolts_nuts.stl" in parts:
    bolts = parts["08_bolts_nuts.stl"]
    print(f"\n🔩 螺栓组件:")
    print(f"  面数: {len(bolts.faces):,}")
    print(f"  X范围: [{bolts.bounds[0][0]:.0f}, {bolts.bounds[1][0]:.0f}]")

    # 螺栓应该集中在4个连接处
    bolt_xs = [0, -600, -680, -725]
    for bx in bolt_xs:
        count = np.sum((bolts.vertices[:, 0] >= bx - 5) & (bolts.vertices[:, 0] <= bx + 5))
        print(f"  x={bx}处螺栓顶点数: {count}")

print("\n" + "="*70)
print("✅ 验证完成")
print("="*70)
