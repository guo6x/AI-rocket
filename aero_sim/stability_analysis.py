"""
Ad Astra 探空火箭 — CG/CP 静稳定性分析
=======================================
使用 Barrowman 方程计算气动压力中心 (CP)，
结合质量分布计算重心 (CG)，验证静稳定裕度。

静稳定性铁律：CP 必须在 CG 后方 ≥ 1 个管径 (1 caliber)
"""

import math
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import font_config  # noqa: F401 — 中文字体配置

from rocket_config import (
    NOSE_TYPE, NOSE_LENGTH, NOSE_BASE_RADIUS,
    BODY_OUTER_RADIUS, BODY_LENGTH, BODY_INNER_RADIUS,
    FIN_COUNT, FIN_ROOT_CHORD, FIN_TIP_CHORD, FIN_SPAN,
    FIN_SWEEP_LENGTH, FIN_THICKNESS, FIN_POSITION_FROM_NOSE,
    MASS_NOSECONE, MASS_BODY_TUBE, MASS_FINS,
    MASS_AVIONICS, MASS_RECOVERY, MASS_MISC,
    MASS_DRY, MOTOR_DRY_MASS, MOTOR_PROPELLANT_MASS,
    TOTAL_LENGTH, AVIONICS_CG_FROM_NOSE,
)

# 管径 (caliber) — 稳定性度量的基本单位
CALIBER = BODY_OUTER_RADIUS * 2  # [m]


# ═══════════════════════════════════════════════════
#  第一部分：Barrowman 方程计算 CP
# ═══════════════════════════════════════════════════

def calc_nose_cp():
    """冯·卡门整流罩的法向力系数导数 & CP 位置"""
    # 冯·卡门 / 抛物线型鼻锥: CNa = 2, CP 在 0.466 * L_nose (经验值)
    cn_alpha_nose = 2.0
    cp_nose = 0.466 * NOSE_LENGTH  # 距头锥顶端
    return cn_alpha_nose, cp_nose


def calc_fin_cp():
    """
    Barrowman 方程：梯形翼的法向力系数导数 & CP 位置
    参考：James S. Barrowman, "The Practical Calculation of the
    Aerodynamic Characteristics of Slender Finned Vehicles", 1967
    """
    n = FIN_COUNT
    cr = FIN_ROOT_CHORD       # 根弦
    ct = FIN_TIP_CHORD        # 梢弦
    s = FIN_SPAN              # 半翼展（从管壁起算）
    lw = FIN_SWEEP_LENGTH     # 前缘后掠距离
    r = BODY_OUTER_RADIUS     # 管外半径
    d = CALIBER               # 管直径

    # ── 干扰因子 (interference factor) ──
    # Barrowman 公式中考虑管体-尾翼之间的气动干扰
    mid_chord_line = math.sqrt(lw**2 + s**2)

    # 法向力系数导数 CNa（每弧度，全部翼片）
    numerator = 4 * n * (s / d) ** 2
    denominator = 1 + math.sqrt(
        1 + (2 * mid_chord_line / (cr + ct)) ** 2
    )
    # 干扰因子: 1 + r/(r+s)
    interference = 1 + r / (r + s)
    cn_alpha_fins = (numerator / denominator) * interference

    # ── 单翼 CP 位置（距尾翼前缘根部）──
    mac_le = lw * (cr + 2 * ct) / (3 * (cr + ct)) + \
             (cr**2 + ct**2 + cr * ct) / (3 * (cr + ct))
    # 但这是距尾翼前缘的距离，需加上尾翼在箭体上的位置
    # 距尾翼前缘根部
    x_fin_local = (lw / 3) * ((cr + 2 * ct) / (cr + ct)) + \
                  (1.0 / 6) * (cr + ct - (cr * ct) / (cr + ct))

    cp_fins = FIN_POSITION_FROM_NOSE + x_fin_local

    return cn_alpha_fins, cp_fins


def calc_body_tube_cp():
    """
    圆柱机身管在小攻角下几乎不产生法向力。
    Barrowman 方程中圆柱段 CNa ≈ 0，所以忽略。
    """
    return 0.0, NOSE_LENGTH + BODY_LENGTH / 2  # 不影响加权


def calc_cp_total():
    """合成全箭 CP 位置（CNa 加权平均）"""
    cn_nose, cp_nose = calc_nose_cp()
    cn_fins, cp_fins = calc_fin_cp()
    cn_body, cp_body = calc_body_tube_cp()

    cn_total = cn_nose + cn_fins + cn_body
    cp_total = (cn_nose * cp_nose + cn_fins * cp_fins + cn_body * cp_body) / cn_total

    return cn_total, cp_total


# ═══════════════════════════════════════════════════
#  第二部分：质量分布计算 CG
# ═══════════════════════════════════════════════════

def calc_cg():
    """
    计算全箭重心位置（距头锥顶端）
    每个组件用"集中质量+位置"建模
    """
    components = [
        # (名称,            质量[kg],               CG距头锥顶端[m])
        ("整流罩",          MASS_NOSECONE,           NOSE_LENGTH * 0.466),
        ("机身管",          MASS_BODY_TUBE,          NOSE_LENGTH + BODY_LENGTH / 2),
        ("尾翼×3",         MASS_FINS,               FIN_POSITION_FROM_NOSE + FIN_ROOT_CHORD / 2),
        ("航电系统",        MASS_AVIONICS,           AVIONICS_CG_FROM_NOSE),
        ("回收系统",        MASS_RECOVERY,           NOSE_LENGTH + 0.050),  # 靠近整流罩底
        ("杂项",            MASS_MISC,               NOSE_LENGTH + BODY_LENGTH / 2),
        ("发动机(含药)",    MOTOR_DRY_MASS + MOTOR_PROPELLANT_MASS,
                            NOSE_LENGTH + BODY_LENGTH - 0.040),  # 管底
    ]

    total_mass = sum(m for _, m, _ in components)
    cg_position = sum(m * x for _, m, x in components) / total_mass

    return cg_position, total_mass, components


# ═══════════════════════════════════════════════════
#  第三部分：稳定性判定与可视化
# ═══════════════════════════════════════════════════

def analyze_stability():
    """完整的静稳定性分析"""
    cg_pos, total_mass, components = calc_cg()
    cn_total, cp_pos = calc_cp_total()

    stability_margin = (cp_pos - cg_pos) / CALIBER

    print("=" * 60)
    print("  Ad Astra 探空火箭 — 静稳定性分析报告")
    print("=" * 60)

    # 质量分解表
    print("\n[DATA] 质量分解:")
    print(f"  {'组件':<12} {'质量(g)':>8} {'CG位置(mm)':>10}")
    print(f"  {'-'*12} {'-'*8} {'-'*10}")
    for name, mass, pos in components:
        print(f"  {name:<12} {mass*1000:>8.1f} {pos*1000:>10.1f}")
    print(f"  {'─'*12} {'─'*8} {'─'*10}")
    print(f"  {'合计':<12} {total_mass*1000:>8.1f}")

    # CG/CP 结果
    print(f"\n[CG] 重心 (CG): {cg_pos*1000:.1f} mm (距头锥顶端)")
    print(f"[CP] 压心 (CP): {cp_pos*1000:.1f} mm (距头锥顶端)")
    print(f"[d]  管径 (d):  {CALIBER*1000:.1f} mm")
    print(f"\n{'='*60}")

    # 稳定性判决
    if stability_margin >= 1.0:
        verdict = "[OK] 静稳定! "
    elif stability_margin >= 0.5:
        verdict = "[WARN] 临界稳定（建议增大尾翼）"
    else:
        verdict = "[FAIL] 不稳定!! CP在CG前方，火箭将翻滚！"

    print(f"  稳定裕度: {stability_margin:.2f} caliber  → {verdict}")
    print(f"{'='*60}")

    return cg_pos, cp_pos, stability_margin, total_mass, components


def plot_rocket_profile(cg_pos, cp_pos, stability_margin):
    """绘制箭体侧视图 + CG/CP 标注"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 4))
    ax.set_aspect('equal')
    ax.set_title(
        f'Ad Astra 探空火箭 — 侧视图 & 稳定性分析\n'
        f'稳定裕度: {stability_margin:.2f} caliber',
        fontsize=13, fontweight='bold'
    )

    r = BODY_OUTER_RADIUS * 1000  # mm
    y_center = 0

    # ── 整流罩（简化为三角形）──
    nose_pts = np.array([
        [0, y_center],
        [NOSE_LENGTH * 1000, y_center + r],
        [NOSE_LENGTH * 1000, y_center - r],
    ])
    nose = plt.Polygon(nose_pts, closed=True, fc='#4FC3F7', ec='#0277BD', lw=1.5)
    ax.add_patch(nose)

    # ── 机身管 ──
    body_x = NOSE_LENGTH * 1000
    body_w = BODY_LENGTH * 1000
    body_rect = patches.Rectangle(
        (body_x, y_center - r), body_w, 2 * r,
        fc='#E0E0E0', ec='#424242', lw=1.5
    )
    ax.add_patch(body_rect)

    # ── 尾翼 (上下各画一片) ──
    fin_x = FIN_POSITION_FROM_NOSE * 1000
    fin_cr = FIN_ROOT_CHORD * 1000
    fin_ct = FIN_TIP_CHORD * 1000
    fin_s = FIN_SPAN * 1000
    fin_sw = FIN_SWEEP_LENGTH * 1000

    for sign in [1, -1]:
        fin_pts = np.array([
            [fin_x, y_center + sign * r],
            [fin_x + fin_sw, y_center + sign * (r + fin_s)],
            [fin_x + fin_sw + fin_ct, y_center + sign * (r + fin_s)],
            [fin_x + fin_cr, y_center + sign * r],
        ])
        fin = plt.Polygon(fin_pts, closed=True, fc='#FF7043', ec='#BF360C', lw=1.5)
        ax.add_patch(fin)

    # ── CG 标记（向下三角 ▽）──
    cg_mm = cg_pos * 1000
    ax.annotate('', xy=(cg_mm, y_center + r + 15),
                xytext=(cg_mm, y_center + r + 35),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(cg_mm, y_center + r + 38, f'CG\n{cg_mm:.0f}mm',
            ha='center', va='bottom', fontsize=10, color='blue', fontweight='bold')

    # ── CP 标记（向上三角 △）──
    cp_mm = cp_pos * 1000
    ax.annotate('', xy=(cp_mm, y_center - r - 15),
                xytext=(cp_mm, y_center - r - 35),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.text(cp_mm, y_center - r - 38, f'CP\n{cp_mm:.0f}mm',
            ha='center', va='top', fontsize=10, color='red', fontweight='bold')

    # ── 稳定裕度标注 ──
    ax.annotate('', xy=(cg_mm, y_center - r - 5),
                xytext=(cp_mm, y_center - r - 5),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    mid_x = (cg_mm + cp_mm) / 2
    ax.text(mid_x, y_center - r - 8,
            f'{stability_margin:.2f} cal',
            ha='center', va='top', fontsize=9, color='green', fontweight='bold')

    # 坐标轴
    ax.set_xlim(-20, TOTAL_LENGTH * 1000 + 50)
    ax.set_ylim(-80, 80)
    ax.set_xlabel('距头锥顶端 [mm]')
    ax.axhline(y=0, color='gray', linestyle=':', alpha=0.3)
    ax.set_yticks([])

    # 保存
    os.makedirs('results', exist_ok=True)
    out_path = os.path.join('results', 'stability_analysis.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n[SAVED] 侧视图已保存: {os.path.abspath(out_path)}")
    plt.close(fig)
    return out_path


# ═══════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    cg, cp, margin, mass, comps = analyze_stability()
    plot_rocket_profile(cg, cp, margin)
