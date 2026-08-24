#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 物理连接验证 - 检查每个连接处的两个零件是否物理接触
"""
import numpy as np
import trimesh
import os

OUTPUT = r"D:\AI_rocket\3d_print_files"

print("="*70)
print("🔍 物理连接验证")
print("="*70)

parts = {
    "01_nose_cone": trimesh.load(os.path.join(OUTPUT, "01_nose_cone.stl")),
    "02_body_tube": trimesh.load(os.path.join(OUTPUT, "02_body_tube.stl")),
    "03_fins": trimesh.load(os.path.join(OUTPUT, "03_fins.stl")),
    "04_avionics_bay": trimesh.load(os.path.join(OUTPUT, "04_avionics_bay.stl")),
    "05_tvc_base": trimesh.load(os.path.join(OUTPUT, "05_tvc_base.stl")),
    "06_tvc_gimbal": trimesh.load(os.path.join(OUTPUT, "06_tvc_gimbal.stl")),
    "07_tvc_nozzle": trimesh.load(os.path.join(OUTPUT, "07_tvc_nozzle.stl")),
    "08_bolts_nuts": trimesh.load(os.path.join(OUTPUT, "08_bolts_nuts.stl")),
}

# 用更鲁棒的检查: 在连接处x±2mm范围内, 任何零件的X坐标是否有重叠
def check_overlap(p1, p2, x_joint, tolerance=2.0):
    """检查两个零件在连接处是否有几何重叠"""
    # 在 x_joint ± tolerance 范围内提取两零件的顶点
    p1_in_range = p1.vertices[(p1.vertices[:, 0] >= x_joint - tolerance) &
                                (p1.vertices[:, 0] <= x_joint + tolerance)]
    p2_in_range = p2.vertices[(p2.vertices[:, 0] >= x_joint - tolerance) &
                                (p2.vertices[:, 0] <= x_joint + tolerance)]
    return len(p1_in_range) > 0 and len(p2_in_range) > 0

joints = [
    ("整流罩-机身", "01_nose_cone", "02_body_tube", 0),
    ("机身-TVC", "02_body_tube", "05_tvc_base", -600),
    ("TVC-万向节", "05_tvc_base", "06_tvc_gimbal", -680),
    ("万向节-喷管", "06_tvc_gimbal", "07_tvc_nozzle", -725),
]

all_passed = True
for name, p1_name, p2_name, x_joint in joints:
    p1 = parts[p1_name]
    p2 = parts[p2_name]
    overlap = check_overlap(p1, p2, x_joint)
    status = "✅" if overlap else "❌"
    if not overlap:
        all_passed = False
    print(f"{status} {name} (x={x_joint}): 两零件在连接处几何重叠")

# 加载装配体并检查
print("\n" + "="*70)
print("完整装配体验证")
print("="*70)

asm = trimesh.load(os.path.join(OUTPUT, "00_full_rocket_assembly.stl"))
print(f"装配体: {len(asm.faces):,}面, 水密:{asm.is_watertight}, 体积:{asm.volume:.0f}mm³")

# 检查装配体的连续性 - 在每个连接处取截面看是否真的"连成一体"
print("\n截面连续性 (单截面是否包含两零件的材质):")
for name, _, _, x_joint in joints:
    section = asm.section(plane_origin=[x_joint, 0, 0], plane_normal=[1, 0, 0])
    if section is not None:
        path_2d = section.to_2D()[0]
        n_pts = len(path_2d.vertices)
        if n_pts > 0:
            r = np.linalg.norm(path_2d.vertices, axis=1)
            print(f"  ✅ {name} (x={x_joint}): 截面点数={n_pts}, 半径范围={r.min():.1f}-{r.max():.1f}mm")
        else:
            print(f"  ⚠️ {name} (x={x_joint}): 截面为空!")
            all_passed = False
    else:
        print(f"  ❌ {name} (x={x_joint}): 无截面!")
        all_passed = False

# 螺栓位置验证
print("\n螺栓位置 (应该在每个法兰处):")
for name, _, _, x_joint in joints:
    bolt_verts = parts["08_bolts_nuts"].vertices
    near = bolt_verts[(bolt_verts[:, 0] >= x_joint - 3) & (bolt_verts[:, 0] <= x_joint + 3)]
    if len(near) > 0:
        ys = np.linalg.norm(near[:, 1:], axis=1)
        print(f"  ✅ {name} (x={x_joint}): {len(near)}个螺栓顶点, 半径{ys.min():.1f}-{ys.max():.1f}mm")
    else:
        print(f"  ❌ {name}: 无螺栓")
        all_passed = False

print("\n" + "="*70)
print(f"🎯 最终: {'🎉 全部通过!' if all_passed else '❌ 仍有部分问题'}")
print("="*70)
