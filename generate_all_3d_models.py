#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🚀 AD ASTRA 完整箭体 + TVC 3D 模型生成器 (修复版)
=============================================================================

📦 生成内容：
   1. 整流罩 (Nose Cone)
   2. 机身管 (Body Tube)
   3. 尾翼 ×3 (Fins)
   4. TVC 万向节组件
   5. 航电舱保护套

📁 输出：*.stl (3D打印) + *.glb (3D预览)

=============================================================================
"""

import numpy as np
import trimesh
import os
import math
from datetime import datetime

# ============================================================
# 配置参数 (毫米 mm)
# ============================================================
CONFIG = {
    "nose_cone": {
        "base_radius": 37.5,  # 底部半径
        "length": 150,        # 长度
        "segments": 48,       # 圆周分段
    },
    "body_tube": {
        "outer_radius": 37.5,
        "inner_radius": 35.5,
        "length": 600,
    },
    "fins": {
        "count": 3,
        "root_chord": 100,
        "tip_chord": 50,
        "span": 80,
        "thickness": 3,
        "position": 600,
        "sweep": 30,
    },
    "avionics_sleeve": {
        "inner_radius": 26.0,
        "outer_radius": 32.5,
        "height": 100,
    },
    "tvc": {
        "edf_diameter": 74,
        "wall": 2.5,
        "gimbal_height": 12,
        "nozzle_length": 40,
        "nozzle_exit": 62,
    }
}

def von_karman_profile(radius, length, num_points=50):
    """冯·卡门曲线"""
    points = []
    for i in range(num_points + 1):
        x = length * (i / num_points)
        theta = math.acos(1 - 2 * x / length) if 0 < x <= length else 0
        y = radius / math.sqrt(math.pi) * math.sqrt(theta - 0.5 * math.sin(2 * theta))
        points.append((x, y))
    return points

def create_hollow_cylinder(inner_r, outer_r, height, segments=48):
    """创建空心圆柱"""
    vertices = []
    faces = []

    # 上下边缘
    for r in [outer_r, inner_r]:
        for j in range(segments):
            angle = 2 * np.pi * j / segments
            vertices.append([height, r * np.cos(angle), r * np.sin(angle)])
        for j in range(segments):
            angle = 2 * np.pi * j / segments
            vertices.append([0, r * np.cos(angle), r * np.sin(angle)])

    # 外表面
    for j in range(segments):
        v1 = j
        v2 = (j + 1) % segments
        v3 = segments + j
        v4 = segments + (j + 1) % segments
        faces.append([v1, v3, v2])
        faces.append([v2, v3, v4])

    # 内表面
    for j in range(segments):
        v1 = segments * 2 + j
        v2 = segments * 2 + (j + 1) % segments
        v3 = segments * 3 + j
        v4 = segments * 3 + (j + 1) % segments
        faces.append([v1, v2, v3])
        faces.append([v2, v4, v3])

    # 底边
    for j in range(segments):
        v1 = segments + j
        v2 = segments + (j + 1) % segments
        v3 = segments * 3 + j
        v4 = segments * 3 + (j + 1) % segments
        faces.append([v1, v4, v2])
        faces.append([v1, v3, v4])

    # 顶边
    for j in range(segments):
        v1 = j
        v2 = (j + 1) % segments
        v3 = segments * 2 + j
        v4 = segments * 2 + (j + 1) % segments
        faces.append([v1, v2, v3])
        faces.append([v2, v4, v3])

    mesh = trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))
    return mesh

def create_cone_hollow(base_r, length, thickness, segments=48):
    """创建空心圆锥（整流罩）"""
    outer_points = von_karman_profile(base_r, length, 40)
    inner_points = []
    for x, y in outer_points:
        inner_r = max(y - thickness, 0.5)
        inner_points.append((x, inner_r))

    vertices = []
    faces = []
    n = len(outer_points)

    # 外表面
    for i, (x, y) in enumerate(outer_points):
        for j in range(segments):
            angle = 2 * np.pi * j / segments
            vertices.append([x, y * np.cos(angle), y * np.sin(angle)])

    # 内表面
    for i, (x, y) in enumerate(inner_points):
        for j in range(segments):
            angle = 2 * np.pi * j / segments
            vertices.append([x, y * np.cos(angle), y * np.sin(angle)])

    # 外表面三角形
    for i in range(n - 1):
        for j in range(segments):
            v1 = i * segments + j
            v2 = i * segments + (j + 1) % segments
            v3 = (i + 1) * segments + j
            v4 = (i + 1) * segments + (j + 1) % segments
            faces.append([v1, v2, v3])
            faces.append([v2, v4, v3])

    # 内表面三角形
    offset = n * segments
    for i in range(n - 1):
        for j in range(segments):
            v1 = offset + i * segments + j
            v2 = offset + i * segments + (j + 1) % segments
            v3 = offset + (i + 1) * segments + j
            v4 = offset + (i + 1) * segments + (j + 1) % segments
            faces.append([v1, v3, v2])
            faces.append([v2, v3, v4])

    # 底部外环
    for j in range(segments):
        v1 = j
        v2 = (j + 1) % segments
        v3 = offset + j
        v4 = offset + (j + 1) % segments
        faces.append([v1, v4, v2])
        faces.append([v1, v3, v4])

    mesh = trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))
    return mesh

def create_trapezoid_fin(root, tip, span, thickness, sweep):
    """创建梯形尾翼"""
    # 顶点
    p1 = np.array([0, 0, 0])
    p2 = np.array([root, 0, 0])
    p3 = np.array([sweep, 0, span])
    p4 = np.array([sweep + tip, 0, span])

    # 前面
    v = [p1, p2, p3, p4, p1 + [0, thickness, 0], p2 + [0, thickness, 0],
         p3 + [0, thickness, 0], p4 + [0, thickness, 0]]

    faces = [
        [0, 1, 2], [1, 3, 2],        # 正面
        [4, 6, 5], [5, 6, 7],        # 背面
        [0, 4, 5], [0, 5, 1],        # 底边
        [2, 6, 4], [2, 4, 0],        # 前缘
        [3, 7, 6], [3, 6, 2],        # 顶边
        [1, 5, 7], [1, 7, 3],        # 后缘
    ]

    return trimesh.Trimesh(vertices=np.array(v), faces=np.array(faces))

def create_annulus(inner_r, outer_r, height, segments=48):
    """创建圆环（空心圆柱）"""
    vertices = []
    faces = []

    # 4个边缘
    for z in [height, 0]:
        for r in [outer_r, inner_r]:
            for j in range(segments):
                angle = 2 * np.pi * j / segments
                vertices.append([z, r * np.cos(angle), r * np.sin(angle)])

    # 外表面
    for j in range(segments):
        v1, v2 = j, (j + 1) % segments
        v3, v4 = segments + j, segments + (j + 1) % segments
        faces.append([v1, v2, v3])
        faces.append([v2, v4, v3])

    # 内表面
    for j in range(segments):
        v1, v2 = segments * 2 + j, segments * 2 + (j + 1) % segments
        v3, v4 = segments * 3 + j, segments * 3 + (j + 1) % segments
        faces.append([v1, v3, v2])
        faces.append([v2, v3, v4])

    # 底边
    for j in range(segments):
        v1, v2 = segments + j, segments + (j + 1) % segments
        v3, v4 = segments * 3 + j, segments * 3 + (j + 1) % segments
        faces.append([v1, v4, v2])
        faces.append([v1, v3, v4])

    # 顶边
    for j in range(segments):
        v1, v2 = j, (j + 1) % segments
        v3, v4 = segments * 2 + j, segments * 2 + (j + 1) % segments
        faces.append([v1, v2, v3])
        faces.append([v2, v4, v3])

    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))

def create_cone_frustum(r_top, r_bottom, height, segments=48):
    """创建圆锥台"""
    vertices = []
    faces = []

    # 4个边缘
    for z in [height, 0]:
        r = r_top if z == height else r_bottom
        for j in range(segments):
            angle = 2 * np.pi * j / segments
            vertices.append([z, r * np.cos(angle), r * np.sin(angle)])

    # 侧面
    for j in range(segments):
        v1, v2 = j, (j + 1) % segments
        v3, v4 = segments + j, segments + (j + 1) % segments
        faces.append([v1, v2, v3])
        faces.append([v2, v4, v3])

    # 底边
    for j in range(segments):
        v1, v2 = segments + j, segments + (j + 1) % segments
        v3 = len(vertices)
        vertices.append([0, 0, 0])
        faces.append([v1, v3, v2])

    # 顶边
    for j in range(segments):
        v1, v2 = j, (j + 1) % segments
        v3 = len(vertices)
        vertices.append([height, 0, 0])
        faces.append([v1, v2, v3])

    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces))

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def save_mesh(mesh, name, output_dir):
    """保存网格到文件"""
    if mesh is None:
        print(f"   ⚠️ 跳过 {name} (网格为空)")
        return None

    try:
        mesh.merge_vertices()
    except:
        pass

    stl_file = os.path.join(output_dir, f"{name}.stl")
    glb_file = os.path.join(output_dir, f"{name}.glb")

    try:
        mesh.export(stl_file)
        print(f"   ✅ 已保存: {stl_file}")
    except Exception as e:
        print(f"   ❌ STL 保存失败: {e}")

    try:
        mesh.export(glb_file)
        print(f"   ✅ 已保存: {glb_file}")
    except Exception as e:
        print(f"   ❌ GLB 保存失败: {e}")

    return mesh

def generate_nose_cone(config, output_dir):
    """生成整流罩"""
    print("\n" + "="*60)
    print("🔴 生成整流罩 (Nose Cone)")
    print("="*60)
    cfg = config["nose_cone"]
    print(f"   底部半径: {cfg['base_radius']} mm")
    print(f"   长度: {cfg['length']} mm")

    mesh = create_cone_hollow(cfg["base_radius"], cfg["length"], 2.0, cfg["segments"])
    return save_mesh(mesh, "nose_cone", output_dir)

def generate_body_tube(config, output_dir):
    """生成机身管"""
    print("\n" + "="*60)
    print("🔵 生成机身管 (Body Tube)")
    print("="*60)
    cfg = config["body_tube"]
    print(f"   外径: {cfg['outer_radius'] * 2} mm")
    print(f"   内径: {cfg['inner_radius'] * 2} mm")
    print(f"   长度: {cfg['length']} mm")

    mesh = create_hollow_cylinder(cfg["inner_radius"], cfg["outer_radius"], cfg["length"])
    return save_mesh(mesh, "body_tube", output_dir)

def generate_fins(config, output_dir):
    """生成尾翼"""
    print("\n" + "="*60)
    print("🟠 生成尾翼 (Fins)")
    print("="*60)
    cfg = config["fins"]
    print(f"   数量: {cfg['count']} 片")
    print(f"   翼展: {cfg['span']} mm")

    fins = []
    for i in range(cfg["count"]):
        angle = 2 * np.pi * i / cfg["count"]
        fin = create_trapezoid_fin(cfg["root_chord"], cfg["tip_chord"],
                                   cfg["span"], cfg["thickness"], cfg["sweep"])

        # 旋转
        rot = trimesh.transformations.rotation_matrix(angle, [1, 0, 0])
        fin.apply_transform(rot)

        # 平移
        body_r = config["body_tube"]["outer_radius"]
        fin.apply_translation([cfg["position"], body_r, 0])
        fins.append(fin)

    combined = trimesh.util.concatenate(fins)
    return save_mesh(combined, "fins_x3", output_dir)

def generate_avionics_sleeve(config, output_dir):
    """生成航电舱"""
    print("\n" + "="*60)
    print("🟢 生成航电舱 (Avionics Sleeve)")
    print("="*60)
    cfg = config["avionics_sleeve"]
    print(f"   内径: {cfg['inner_radius'] * 2} mm")
    print(f"   外径: {cfg['outer_radius'] * 2} mm")
    print(f"   高度: {cfg['height']} mm")

    mesh = create_annulus(cfg["inner_radius"], cfg["outer_radius"], cfg["height"])
    return save_mesh(mesh, "avionics_sleeve", output_dir)

def generate_tvc_components(config, output_dir):
    """生成 TVC 组件"""
    print("\n" + "="*60)
    print("🟣 生成 TVC 组件")
    print("="*60)
    cfg = config["tvc"]

    results = {}

    # TVC 底座
    print("\n  📦 TVC 底座")
    edf_r = cfg["edf_diameter"] / 2
    base_mesh = create_hollow_cylinder(edf_r, edf_r + cfg["wall"] + 2, 30)
    results["base"] = save_mesh(base_mesh, "tvc_base", output_dir)

    # TVC 万向环
    print("\n  📦 TVC 万向环")
    ring_ir = edf_r - 2
    ring_or = edf_r - 0.5
    ring_mesh = create_annulus(ring_ir, ring_or, cfg["gimbal_height"])
    results["gimbal"] = save_mesh(ring_mesh, "tvc_gimbal_ring", output_dir)

    # TVC 喷管
    print("\n  📦 TVC 喷管")
    inlet_r = ring_ir - cfg["wall"]
    nozzle_mesh = create_cone_frustum(inlet_r, cfg["nozzle_exit"]/2, cfg["nozzle_length"])
    results["nozzle"] = save_mesh(nozzle_mesh, "tvc_nozzle", output_dir)

    return results

def generate_preview_html(output_dir):
    """生成 3D 预览 HTML"""
    print("\n" + "="*60)
    print("🌐 生成 3D 预览 HTML")
    print("="*60)

    files = [
        ("nose_cone", "🔴 整流罩", "冯·卡门曲线 | 150mm"),
        ("body_tube", "🔵 机身管", "600mm 长 | 75mm 直径"),
        ("fins_x3", "🟠 尾翼 ×3", "梯形翼 | 80mm 翼展"),
        ("avionics_sleeve", "🟢 航电舱", "100mm 高 | STM32 兼容"),
        ("tvc_base", "🟣 TVC 底座", "EDF 安装 | 30mm 高"),
        ("tvc_gimbal_ring", "🟡 TVC 万向环", "±15° 范围"),
        ("tvc_nozzle", "🔵 TVC 喷管", "锥形 | 40mm 长"),
    ]

    cards_html = ""
    for fname, title, desc in files:
        cards_html += f'''
            <div class="model-card">
                <h3>{title}</h3>
                <canvas id="canvas-{fname}"></canvas>
                <div class="info">
                    {desc}<br>
                    <a href="{fname}.stl" class="download" download>📥 下载 STL</a>
                </div>
            </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Ad Astra - 3D 模型预览</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0e17, #1a1a2e);
            color: #fff;
            min-height: 100vh;
        }}
        header {{
            text-align: center;
            padding: 2rem;
            background: rgba(0,0,0,0.3);
        }}
        header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        header p {{ color: #888; }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .model-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }}
        .model-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .model-card h3 {{
            padding: 1rem;
            background: rgba(0,212,255,0.1);
            font-size: 1rem;
        }}
        .model-card canvas {{
            width: 100%;
            height: 220px;
            background: #0a0a15;
        }}
        .model-card .info {{
            padding: 1rem;
            font-size: 0.9rem;
            color: #aaa;
            line-height: 1.6;
        }}
        .model-card .download {{
            display: inline-block;
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, #00d4ff, #a855f7);
            color: #fff;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            margin-top: 0.5rem;
        }}
        .model-card .download:hover {{
            transform: scale(1.05);
        }}
        .instructions {{
            background: rgba(0,212,255,0.1);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 2rem 0;
        }}
        .instructions h3 {{ color: #00d4ff; margin-bottom: 1rem; }}
        .instructions ul {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}
        .instructions li {{
            padding: 0.75rem;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
        }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: #666;
            font-size: 0.9rem;
        }}
    </style>
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
        }}
    }}
    </script>
</head>
<body>
    <header>
        <h1>🚀 Ad Astra 3D 模型预览</h1>
        <p>拖拽旋转 · 滚轮缩放 · 右键平移</p>
    </header>

    <div class="container">
        <div class="instructions">
            <h3>💡 3D 打印指南</h3>
            <ul>
                <li>📐 <strong>切片软件:</strong> Cura / PrusaSlicer</li>
                <li>📏 <strong>层高:</strong> 0.2mm (标准)</li>
                <li>🧊 <strong>填充:</strong> 20%</li>
                <li>🌡️ <strong>材料:</strong> PLA 或 PETG</li>
                <li>🖨️ <strong>喷嘴:</strong> 0.4mm 标准</li>
                <li>⚡ <strong>速度:</strong> 50mm/s</li>
            </ul>
        </div>

        <div class="model-grid">
            {cards_html}
        </div>
    </div>

    <footer>
        <p>🚀 Ad Astra 火箭项目 | 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </footer>

    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        import {{ STLLoader }} from 'three/addons/loaders/STLLoader.js';

        const models = {{
            'canvas-nose': {{ file: 'nose_cone.stl' }},
            'canvas-body_tube': {{ file: 'body_tube.stl' }},
            'canvas-fins_x3': {{ file: 'fins_x3.stl' }},
            'canvas-avionics_sleeve': {{ file: 'avionics_sleeve.stl' }},
            'canvas-tvc_base': {{ file: 'tvc_base.stl' }},
            'canvas-tvc_gimbal_ring': {{ file: 'tvc_gimbal_ring.stl' }},
            'canvas-tvc_nozzle': {{ file: 'tvc_nozzle.stl' }},
        }};

        const material = new THREE.MeshPhongMaterial({{
            color: 0x00d4ff,
            specular: 0x333333,
            shininess: 100,
            flatShading: false
        }});

        for (const [canvasId, config] of Object.entries(models)) {{
            const canvas = document.getElementById(canvasId);
            if (!canvas) continue;

            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0a0a15);

            const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
            camera.position.set(2, 1.5, 2);

            const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
            renderer.setSize(canvas.clientWidth, canvas.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);

            const controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            scene.add(new THREE.AmbientLight(0xffffff, 0.6));
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(5, 5, 5);
            scene.add(dirLight);

            scene.add(new THREE.GridHelper(8, 20, 0x222222, 0x111111));

            const loader = new STLLoader();
            loader.load(config.file, (geometry) => {{
                geometry.computeVertexNormals();
                const mesh = new THREE.Mesh(geometry, material);

                // 自动缩放适应视角
                const box = new THREE.Box3().setFromObject(mesh);
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                mesh.scale.setScalar(1.5 / maxDim);

                // 居中
                box.setFromObject(mesh);
                const center = box.getCenter(new THREE.Vector3());
                mesh.position.sub(center);

                scene.add(mesh);
            }});

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
        }}
    </script>
</body>
</html>'''

    html_file = os.path.join(output_dir, "3d_preview.html")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"   ✅ 已保存: {html_file}")

def main():
    print("\n" + "="*70)
    print("🚀 AD ASTRA 完整箭体 + TVC 3D 模型生成器")
    print("="*70)
    print(f"\n📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    output_dir = ensure_dir(os.path.join(os.path.dirname(__file__), "3d_print_files"))
    print(f"\n📁 输出目录: {output_dir}")

    # 生成所有组件
    generate_nose_cone(CONFIG, output_dir)
    generate_body_tube(CONFIG, output_dir)
    generate_fins(CONFIG, output_dir)
    generate_avionics_sleeve(CONFIG, output_dir)
    generate_tvc_components(CONFIG, output_dir)
    generate_preview_html(output_dir)

    print("\n" + "="*70)
    print("🎉 所有 3D 模型生成完成！")
    print("="*70)
    print(f"\n📁 文件位置: {output_dir}")
    print("\n📋 生成的 STL 文件:")
    print("   ├── nose_cone.stl       ← 整流罩")
    print("   ├── body_tube.stl       ← 机身管")
    print("   ├── fins_x3.stl        ← 尾翼")
    print("   ├── avionics_sleeve.stl ← 航电舱")
    print("   ├── tvc_base.stl       ← TVC 底座")
    print("   ├── tvc_gimbal_ring.stl← 万向环")
    print("   ├── tvc_nozzle.stl     ← 喷管")
    print("   └── 3d_preview.html    ← 3D 预览页面")
    print("\n💡 使用方法:")
    print("   1. 用浏览器打开 3d_preview.html 查看模型")
    print("   2. 用 Cura/PrusaSlicer 导入 STL 切片打印")
    print("   3. 层高 0.2mm，填充 20%，PLA 材料")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
