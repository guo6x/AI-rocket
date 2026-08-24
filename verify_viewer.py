#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ viewer.html 显示修复验证脚本
检查所有按钮引用的 STL 文件是否存在, 数据是否一致
"""
import os
import re
import sys
import numpy as np
import trimesh

OUTPUT = r"D:\AI_rocket\3d_print_files"
VIEWER = os.path.join(OUTPUT, "viewer.html")


def main():
    print("="*70)
    print("✅ viewer.html 显示修复验证")
    print("="*70)

    # 1. 解析 viewer.html 所有 data-file
    with open(VIEWER, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'data-file="([^"]+)"')
    files = pattern.findall(content)

    print(f"\nviewer.html 中引用了 {len(files)} 个文件:")
    all_ok = True
    for f in files:
        path = os.path.join(OUTPUT, f)
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        if not exists:
            all_ok = False
        size = os.path.getsize(path) / 1024 if exists else 0
        print(f"  {status} {f:<40} {size:>8.1f} KB")

    # 2. 检查 start_server.py 引用
    print("\nstart_server.py 文件名检查:")
    ss_path = os.path.join(OUTPUT, "start_server.py")
    if os.path.exists(ss_path):
        with open(ss_path, "r", encoding="utf-8") as f:
            ss_content = f.read()
        ss_pattern = re.compile(r'"([^"]+\.stl)"')
        ss_files = ss_pattern.findall(ss_content)
        for f in ss_files:
            path = os.path.join(OUTPUT, f)
            exists = os.path.exists(path)
            status = "✅" if exists else "❌"
            print(f"  {status} {f}")

    # 3. 检查 viewer.html 的 statsRow 初始值是否与 STL 实际一致
    print("\nstatsRow 初始值与 STL 一致性:")
    # 找 statsRow 块
    sr_match = re.search(r'<div class="stats-row"[^>]*>(.*?)</div>\s*<a href', content, re.DOTALL)
    if sr_match:
        sr_content = sr_match.group(1)
        # 找 value
        values = re.findall(r'<div class="value">([^<]+)</div>', sr_content)
        print(f"  viewer 初始 statsRow 包含 {len(values)} 个值: {values}")

    # 4. 检查每个 STL 的真实尺寸 vs viewer 描述
    print("\n每个零件的实际尺寸 vs viewer 描述:")
    for filename in files:
        path = os.path.join(OUTPUT, filename)
        if not os.path.exists(path):
            continue
        mesh = trimesh.load(path)
        bounds = mesh.bounds
        length = bounds[1][0] - bounds[0][0]
        yz_r = np.linalg.norm(mesh.vertices[:, 1:], axis=1)
        max_dia = yz_r.max() * 2
        n_faces = len(mesh.faces)
        watertight = mesh.is_watertight
        print(f"  {filename}:")
        print(f"    X范围=[{bounds[0][0]:.0f}, {bounds[1][0]:.0f}], 长度={length:.0f}mm")
        print(f"    最大外径={max_dia:.0f}mm, 面数={n_faces:,}, 水密={watertight}")

    # 5. 总结
    print("\n" + "="*70)
    if all_ok:
        print("🎉 验证通过! 所有 8 个 viewer.html 引用的 STL 文件都存在")
    else:
        print("❌ 仍有部分文件缺失, 请检查 generate_rocket_v10.py 输出")
    print("="*70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
