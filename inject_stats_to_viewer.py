#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 自动从 STL 读取真实数据并同步到 viewer.html (v11)
所有参数严格对齐历史 aero_sim/rocket_config.py；该配置不是当前制造真相源。
"""
import os
import re
import numpy as np
import trimesh

OUTPUT = r"D:\AI_rocket\3d_print_files"
VIEWER = os.path.join(OUTPUT, "viewer.html")

# v11 零件清单 (与 rocket_config.py 对齐)
PARTS = [
    {
        "file": "00_full_rocket_assembly.stl",
        "title": "🚀 完整火箭 (v11)",
        "desc_template": "Ad Astra 探空火箭历史 v11 固体飞行构型（非当前制造真相源）。装配体: 整流罩(Von Karman 150mm) → 机身管(Ø75mm×600mm) → 航电舱 → 回收舱 → 尾翼×3(翼展80mm, 根弦100mm, 120°均布) → 发动机舱(C6-5) → 收敛-扩散喷管(出口Ø18mm)。总长{length:.0f}mm(不含喷管750+喷管20=770)，最大外径{max_dia:.0f}mm，{n_faces:,}面。",
        "stats_keys": ["总长", "最大直径", "面数"],
        "is_assembly": True,
    },
    {
        "file": "01_nose_cone.stl",
        "title": "🔴 整流罩 (Von Karman)",
        "desc_template": "Von Karman 曲线外形(最优跨声速阻力, σ=0.8)，底部外径 75mm(=机身外径)，长 150mm。底部内径 71mm(=机身内径)，壁厚 2mm。参数源自 rocket_config.py NOSE_LENGTH=150mm。",
        "stats_keys": ["类型", "长度", "底部外径", "面数"],
    },
    {
        "file": "02_body_tube.stl",
        "title": "🔵 机身管",
        "desc_template": "Ø75mm 外径空心管，壁厚 2mm，长 600mm。PLA 3D 打印。源自 rocket_config.py: BODY_OUTER_RADIUS=37.5mm, BODY_INNER_RADIUS=35.5mm, BODY_LENGTH=600mm。用于容纳航电舱(220-300mm)、回收舱(350-410mm)、发动机舱(650-750mm)。",
        "stats_keys": ["外径", "壁厚", "长度", "面数"],
    },
    {
        "file": "03_fins.stl",
        "title": "🟠 尾翼 ×3 (梯形)",
        "desc_template": "3 片梯形尾翼，120° 均布。根弦 100mm，梢弦 50mm，翼展 80mm(从管壁算起)，前缘后掠 30mm，翼厚 3mm。翼根前缘位于距头锥顶端 600mm 处(= 机身管末端)。源自 rocket_config.py FIN_COUNT=3, FIN_SPAN=80mm, FIN_ROOT_CHORD=100mm, FIN_TIP_CHORD=50mm, FIN_SWEEP_LENGTH=30mm。静稳定裕度 1.36 caliber。",
        "stats_keys": ["数量", "翼展", "根弦", "梢弦", "前缘后掠", "面数"],
    },
    {
        "file": "04_avionics_bay.stl",
        "title": "🟢 航电舱",
        "desc_template": "Ø71mm 内径圆筒，长 80mm，位于机身管 220-300mm 处(距头锥 370-450mm)，用于安装 STM32+GY-91+ESP8266+电池。源自 rocket_config.py AVIONICS_CG_FROM_NOSE=400mm。",
        "stats_keys": ["直径", "长度", "位置", "面数"],
    },
    {
        "file": "05_motor_nozzle.stl",
        "title": "🔥 发动机舱 + 喷管 (Estes C6-5)",
        "desc_template": "Estes C6-5 固体发动机舱(管尾 650-750mm，100mm 长，容纳 Ø18×70mm 发动机) + 收敛-扩散喷管(喉道 4mm, 出口 18mm, 长 20mm)。源自 rocket_config.py: MOTOR_TOTAL_IMPULSE=20.0N·s, MOTOR_AVG_THRUST=12.12N, MOTOR_BURN_TIME=1.65s。⚠️ 推重比警告: 当前总重 340g 需 F/G 级固体才能 15m/s 脱架(详见 aero-sim-report.md)。",
        "stats_keys": ["类型", "总冲", "均推", "燃烧时间", "喉道", "出口", "面数"],
    },
    {
        "file": "06_recovery_bay.stl",
        "title": "🪂 回收系统舱",
        "desc_template": "Ø71mm 内径圆筒，长 60mm，位于机身管 350-410mm 处(距头锥 500-560mm)。容纳主伞+弹射机构(质量 30g)。源自 rocket_config.py MASS_RECOVERY=0.030kg。",
        "stats_keys": ["直径", "长度", "位置", "面数"],
    },
    {
        "file": "07_bolts.stl",
        "title": "🔩 螺栓总成 (M3×16)",
        "desc_template": "M3×16 螺栓 16 颗(整流罩-机身连接 8 颗 + 机身-发动机舱连接 8 颗)。六角头，螺杆长 10mm。源自设计: WALL_T=4mm 法兰厚度 × 2 + 安全余量。",
        "stats_keys": ["规格", "数量", "面数"],
    },
]


def get_stl_stats(filename):
    """从 STL 读取真实统计数据"""
    path = os.path.join(OUTPUT, filename)
    if not os.path.exists(path):
        return None
    mesh = trimesh.load(path)
    if len(mesh.vertices) == 0:
        return None

    bounds = mesh.bounds
    length = float(bounds[1][0] - bounds[0][0])

    yz_r = np.linalg.norm(mesh.vertices[:, 1:], axis=1)
    max_dia = float(yz_r.max() * 2)

    n_faces = len(mesh.faces)
    is_watertight = bool(mesh.is_watertight)
    volume = float(mesh.volume) if is_watertight else 0

    return {
        "length": round(length, 1),
        "max_dia": round(max_dia, 1),
        "n_faces": n_faces,
        "is_watertight": is_watertight,
        "volume": round(volume, 0),
    }


def build_stats_dict(part, stats):
    """根据零件类型构建 stats 字典"""
    if stats is None:
        return {"面数": "N/A"}
    file = part["file"]

    if file == "00_full_rocket_assembly.stl":
        return {
            "总长": f"{stats['length']:.0f}mm",
            "最大直径": f"{stats['max_dia']:.0f}mm",
            "面数": f"{stats['n_faces']:,}",
            "水密": "✅" if stats['is_watertight'] else "❌",
        }
    elif file == "01_nose_cone.stl":
        return {
            "类型": "Von Karman",
            "长度": f"{stats['length']:.0f}mm",
            "底部外径": f"{stats['max_dia']:.0f}mm",
            "面数": f"{stats['n_faces']:,}",
            "水密": "✅" if stats['is_watertight'] else "❌",
        }
    elif file == "02_body_tube.stl":
        return {
            "外径": "Ø75mm",
            "壁厚": "2mm",
            "长度": f"{stats['length']:.0f}mm",
            "面数": f"{stats['n_faces']:,}",
            "水密": "✅" if stats['is_watertight'] else "❌",
        }
    elif file == "03_fins.stl":
        return {
            "数量": "3片(120°)",
            "翼展": "80mm",
            "根弦": "100mm",
            "梢弦": "50mm",
            "前缘后掠": "30mm",
            "面数": f"{stats['n_faces']:,}",
        }
    elif file == "04_avionics_bay.stl":
        return {
            "直径": "Ø71mm",
            "长度": f"{stats['length']:.0f}mm",
            "位置": "220-300mm",
            "面数": f"{stats['n_faces']:,}",
        }
    elif file == "05_motor_nozzle.stl":
        return {
            "类型": "Estes C6-5",
            "总冲": "20.0N·s",
            "均推": "12.12N",
            "燃烧时间": "1.65s",
            "喉道": "Ø4mm",
            "出口": f"Ø{stats['max_dia']:.0f}mm",
            "面数": f"{stats['n_faces']:,}",
            "水密": "✅" if stats['is_watertight'] else "❌",
        }
    elif file == "06_recovery_bay.stl":
        return {
            "直径": "Ø71mm",
            "长度": f"{stats['length']:.0f}mm",
            "位置": "350-410mm",
            "面数": f"{stats['n_faces']:,}",
        }
    elif file == "07_bolts.stl":
        return {
            "规格": "M3×16",
            "数量": "16颗",
            "面数": f"{stats['n_faces']:,}",
        }
    return {}


def main():
    print("="*70)
    print("📊 同步 viewer.html 数据 (v11, 严格对齐 rocket_config.py)")
    print("="*70)

    with open(VIEWER, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []
    for part in PARTS:
        filename = part["file"]
        stats = get_stl_stats(filename)
        if stats is None:
            print(f"  ❌ {filename}: 文件不存在")
            continue

        # 构建 desc 和 stats
        desc = part["desc_template"].format(**stats)
        stats_dict = build_stats_dict(part, stats)
        stats_json = "{" + ", ".join(f'"{k}":"{v}"' for k, v in stats_dict.items()) + "}"

        # 按 data-file 找按钮
        old_pattern = re.compile(
            r'<button\s+class="model-btn[^"]*"\s+data-file="' + re.escape(filename) + r'"[^>]*>.*?</button>',
            re.DOTALL
        )

        new_btn_html = (
            f'<button class="model-btn" data-file="{filename}" '
            f'data-title="{part["title"]}" data-desc="{desc}" '
            f"data-stats='{stats_json}'>"
            f'<span class="num">{part["title"].split(" ")[0]}</span>'
            f'{part["title"]}'
            f'</button>'
        )

        new_content, n = old_pattern.subn(new_btn_html, content)
        if n == 0:
            print(f"  ⚠️ {filename}: 未找到按钮")
            continue

        content = new_content
        changes.append((filename, stats['n_faces'], stats['length'], stats['max_dia']))
        print(f"  ✅ {filename}: {stats['n_faces']:,}面, "
              f"长{stats['length']:.0f}mm, 外径{stats['max_dia']:.0f}mm")

    # 修复标题
    content = content.replace(
        "🚀 Ad Astra 火箭项目 v10",
        "🚀 Ad Astra 火箭项目 v11"
    )
    content = content.replace(
        "v10 终极质量版 · 8 零件水密 · 4 螺栓法兰连接 · 3D 零件预览",
        "v11 同步版 · 严格对齐 rocket_config.py · 3 片尾翼 120° 分布 · Estes C6-5 发动机"
    )
    content = content.replace(
        "<title>🚀 Ad Astra - 火箭 3D 零件预览 v10</title>",
        "<title>🚀 Ad Astra - 火箭 3D 零件预览 v11</title>"
    )
    content = content.replace(
        "let currentFile = '00_full_rocket_assembly.stl';",
        "let currentFile = '00_full_rocket_assembly.stl';"
    )
    content = content.replace(
        "let currentTitle = '🚀 完整火箭 (v10)';",
        "let currentTitle = '🚀 完整火箭 (v11)';"
    )

    # statsRow 初始值 (默认显示完整火箭的)
    assembly_stats = get_stl_stats("00_full_rocket_assembly.stl")
    if assembly_stats:
        new_stats_row = f'''<div class="stats-row" id="statsRow">
                <div class="stat-item"><div class="label">总长</div><div class="value">{assembly_stats['length']:.0f}mm</div></div>
                <div class="stat-item"><div class="label">最大直径</div><div class="value">{assembly_stats['max_dia']:.0f}mm</div></div>
                <div class="stat-item"><div class="label">面数</div><div class="value">{assembly_stats['n_faces']:,}</div></div>
                <div class="stat-item"><div class="label">水密</div><div class="value">{"✅" if assembly_stats['is_watertight'] else "❌"}</div></div>
            </div>'''
        content = re.sub(
            r'<div class="stats-row"[^>]*>.*?</div>\s*<a href',
            new_stats_row + '\n            <a href',
            content,
            count=1,
            flags=re.DOTALL
        )

    # 写回
    with open(VIEWER, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n{'='*70}")
    print(f"✅ viewer.html 已更新: {len(changes)} 个零件")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
