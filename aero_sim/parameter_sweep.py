"""
Ad Astra 探空火箭 — 参数扫描与优化
====================================
自动化扫描尾翼面积、整流罩长度等关键变量，
输出参数 vs 稳定裕度 / 阻力系数的对比表。
"""

import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import font_config  # noqa: F401

sys.path.insert(0, os.path.dirname(__file__))

from rocket_config import (
    NOSE_LENGTH, NOSE_BASE_RADIUS,
    BODY_OUTER_RADIUS, BODY_LENGTH, BODY_INNER_RADIUS,
    FIN_COUNT, FIN_ROOT_CHORD, FIN_TIP_CHORD, FIN_SPAN,
    FIN_SWEEP_LENGTH, FIN_THICKNESS, FIN_POSITION_FROM_NOSE,
    MASS_DRY, TOTAL_LENGTH,
)

# 管径
CALIBER = BODY_OUTER_RADIUS * 2


def barrowman_cp(nose_len, fin_root, fin_tip, fin_span, fin_sweep, fin_pos):
    """简化 Barrowman 计算，返回 (CP 位置, CNa_total)"""
    r = BODY_OUTER_RADIUS
    d = CALIBER

    # 整流罩
    cn_nose = 2.0
    cp_nose = 0.466 * nose_len

    # 尾翼
    n = FIN_COUNT
    mid_chord = math.sqrt(fin_sweep**2 + fin_span**2)
    num = 4 * n * (fin_span / d) ** 2
    den = 1 + math.sqrt(1 + (2 * mid_chord / (fin_root + fin_tip)) ** 2)
    interf = 1 + r / (r + fin_span)
    cn_fins = (num / den) * interf

    x_local = (fin_sweep / 3) * ((fin_root + 2 * fin_tip) / (fin_root + fin_tip)) + \
              (1.0 / 6) * (fin_root + fin_tip - (fin_root * fin_tip) / (fin_root + fin_tip))
    cp_fins = fin_pos + x_local

    cn_total = cn_nose + cn_fins
    cp_total = (cn_nose * cp_nose + cn_fins * cp_fins) / cn_total
    return cp_total, cn_total


def estimate_cg(nose_len, body_len):
    """简化 CG 估算（基于比例缩放）"""
    total_len = nose_len + body_len
    # CG 大致在全长 55% 处（靠近尾部，因为发动机和航电偏后）
    return total_len * 0.55


def sweep_fin_span():
    """扫描：尾翼翼展 vs 稳定裕度"""
    spans = np.linspace(0.03, 0.15, 20)  # 30mm ~ 150mm
    margins = []

    cg = estimate_cg(NOSE_LENGTH, BODY_LENGTH)

    for s in spans:
        cp, _ = barrowman_cp(
            NOSE_LENGTH, FIN_ROOT_CHORD, FIN_TIP_CHORD,
            s, FIN_SWEEP_LENGTH, FIN_POSITION_FROM_NOSE
        )
        margin = (cp - cg) / CALIBER
        margins.append(margin)

    return spans * 1000, margins  # 转 mm


def sweep_fin_root_chord():
    """扫描：尾翼根弦长 vs 稳定裕度"""
    chords = np.linspace(0.05, 0.20, 20)  # 50mm ~ 200mm
    margins = []

    cg = estimate_cg(NOSE_LENGTH, BODY_LENGTH)

    for cr in chords:
        cp, _ = barrowman_cp(
            NOSE_LENGTH, cr, FIN_TIP_CHORD,
            FIN_SPAN, FIN_SWEEP_LENGTH, FIN_POSITION_FROM_NOSE
        )
        margin = (cp - cg) / CALIBER
        margins.append(margin)

    return chords * 1000, margins


def sweep_nose_length():
    """扫描：整流罩长度 vs 稳定裕度"""
    nose_lens = np.linspace(0.05, 0.30, 20)  # 50mm ~ 300mm
    margins = []

    for nl in nose_lens:
        cg = estimate_cg(nl, BODY_LENGTH)
        cp, _ = barrowman_cp(
            nl, FIN_ROOT_CHORD, FIN_TIP_CHORD,
            FIN_SPAN, FIN_SWEEP_LENGTH, FIN_POSITION_FROM_NOSE
        )
        margin = (cp - cg) / CALIBER
        margins.append(margin)

    return nose_lens * 1000, margins


def sweep_body_length():
    """扫描：机身管长度 vs 稳定裕度"""
    body_lens = np.linspace(0.30, 1.00, 20)  # 300mm ~ 1000mm
    margins = []

    for bl in body_lens:
        cg = estimate_cg(NOSE_LENGTH, bl)
        fin_pos = NOSE_LENGTH + bl - FIN_ROOT_CHORD
        cp, _ = barrowman_cp(
            NOSE_LENGTH, FIN_ROOT_CHORD, FIN_TIP_CHORD,
            FIN_SPAN, FIN_SWEEP_LENGTH, fin_pos
        )
        margin = (cp - cg) / CALIBER
        margins.append(margin)

    return body_lens * 1000, margins


def run_parameter_sweep():
    """执行全部参数扫描并生成图表"""
    print("=" * 60)
    print("  Ad Astra 探空火箭 — 参数灵敏度扫描")
    print("=" * 60)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('参数灵敏度分析 — 各参数对静稳定裕度的影响',
                 fontsize=14, fontweight='bold')

    sweeps = [
        (axes[0, 0], sweep_fin_span, '尾翼翼展 [mm]', '翼展', FIN_SPAN * 1000),
        (axes[0, 1], sweep_fin_root_chord, '尾翼根弦长 [mm]', '根弦长', FIN_ROOT_CHORD * 1000),
        (axes[1, 0], sweep_nose_length, '整流罩长度 [mm]', '整流罩长', NOSE_LENGTH * 1000),
        (axes[1, 1], sweep_body_length, '机身管长度 [mm]', '管长', BODY_LENGTH * 1000),
    ]

    for ax, sweep_fn, xlabel, label, baseline_val in sweeps:
        x_vals, margins = sweep_fn()

        ax.plot(x_vals, margins, 'b-', linewidth=2)
        ax.axhline(y=1.0, color='green', linestyle='--', alpha=0.7, label='最低稳定线 (1 cal)')
        ax.axhline(y=2.0, color='orange', linestyle='--', alpha=0.5, label='过稳定线 (2 cal)')
        ax.axvline(x=baseline_val, color='red', linestyle=':', alpha=0.7, label=f'基线值 {baseline_val:.0f}mm')

        ax.fill_between(x_vals, 1.0, 2.0, alpha=0.1, color='green', label='理想区间')
        ax.set_xlabel(xlabel)
        ax.set_ylabel('稳定裕度 [caliber]')
        ax.set_title(f'{label} 灵敏度')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # 打印推荐范围
        ideal = [(x, m) for x, m in zip(x_vals, margins) if 1.0 <= m <= 2.0]
        if ideal:
            x_min = min(p[0] for p in ideal)
            x_max = max(p[0] for p in ideal)
            print(f"  {label}: 理想范围 {x_min:.0f} ~ {x_max:.0f} mm "
                  f"(基线 {baseline_val:.0f} mm)")
        else:
            print(f"  {label}: ⚠️ 在扫描范围内未找到理想稳定区间!")

    plt.tight_layout()

    os.makedirs('results', exist_ok=True)
    out_path = os.path.join('results', 'parameter_sweep.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n[SAVED] {os.path.abspath(out_path)}")
    plt.close(fig)

    # ── 综合推荐 ──
    print("\n" + "=" * 60)
    print("  [REC] 推荐外形配置")
    print("=" * 60)
    print(f"  管径:       {CALIBER*1000:.0f} mm")
    print(f"  整流罩:     冯·卡门, {NOSE_LENGTH*1000:.0f} mm")
    print(f"  机身管长:   {BODY_LENGTH*1000:.0f} mm")
    print(f"  尾翼翼展:   {FIN_SPAN*1000:.0f} mm (可调至 60~120mm)")
    print(f"  尾翼根弦:   {FIN_ROOT_CHORD*1000:.0f} mm")
    print(f"  尾翼数量:   {FIN_COUNT} 片")
    print("=" * 60)


if __name__ == "__main__":
    run_parameter_sweep()
