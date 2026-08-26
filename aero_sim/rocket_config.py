"""
Ad Astra 探空火箭 — 历史固体飞行基线 (LEGACY_FLIGHT_BASELINE)
=================================
这些参数供历史稳定性分析和弹道仿真脚本引用，不是当前 EDF 台架或制造构型的工程真相源。
单位制：SI（米 / 千克 / 秒）
"""

# ── 整流罩 (Nose Cone) ────────────────────────────
NOSE_TYPE = "Von Karman"       # 冯·卡门曲线（最优跨声速阻力）
NOSE_LENGTH = 0.150            # 整流罩长度 [m]
NOSE_BASE_RADIUS = 0.0375     # 底部半径 = 管外径/2 [m]

# ── 机身管 (Body Tube) ────────────────────────────
BODY_OUTER_RADIUS = 0.0375    # 外半径 [m]  → 外径 75 mm
BODY_INNER_RADIUS = 0.0355    # 内半径 [m]  → 壁厚 2 mm (PLA 3D打印)
BODY_LENGTH = 0.600           # 管长 [m]

# ── 尾翼 (Fins) ───────────────────────────────────
FIN_COUNT = 3                  # 3 片 120° 均布
FIN_ROOT_CHORD = 0.100        # 根弦长 [m]
FIN_TIP_CHORD = 0.050         # 梢弦长 [m]
FIN_SPAN = 0.080              # 翼展（从管壁算起）[m]
FIN_SWEEP_LENGTH = 0.030      # 前缘后掠距离 [m]
FIN_THICKNESS = 0.003         # 翼厚 [m]（3mm PLA）
# 尾翼前缘距火箭头锥顶端的距离
FIN_POSITION_FROM_NOSE = 0.600  # [m] 贴近管底

# ── 质量 (Mass Properties) ────────────────────────
# 干重分解（不含发动机）
MASS_NOSECONE = 0.040         # 整流罩 [kg]
MASS_BODY_TUBE = 0.120        # 机身管 [kg]
MASS_FINS = 0.030             # 3片尾翼合计 [kg]
MASS_AVIONICS = 0.100         # 航电（STM32+GY91+ESP8266+电池）[kg]
MASS_RECOVERY = 0.030         # 回收系统（伞+弹射机构）[kg]
MASS_MISC = 0.020             # 胶水、线缆、螺丝等 [kg]

MASS_DRY = (MASS_NOSECONE + MASS_BODY_TUBE + MASS_FINS
            + MASS_AVIONICS + MASS_RECOVERY + MASS_MISC)

# 航电舱重心位置（距头锥顶端）
AVIONICS_CG_FROM_NOSE = 0.400  # [m] 大致在管中段偏后

# ── 发动机 (Motor) ────────────────────────────────
# 基线选型：Estes C6-5（商业成品小型固体发动机）
# 总冲 ~8.8 N·s | 平均推力 ~4.7 N | 燃烧时间 ~1.9 s | 质量 ~24 g
MOTOR_DRY_MASS = 0.0214       # 燃尽后壳体质量 [kg]
MOTOR_PROPELLANT_MASS = 0.0242 # 推进剂质量 [kg]
MOTOR_TOTAL_MASS = MOTOR_DRY_MASS + MOTOR_PROPELLANT_MASS
MOTOR_TOTAL_IMPULSE = 20.0     # 总冲 [N·s]
MOTOR_BURN_TIME = 1.65         # 燃烧时间 [s]
MOTOR_AVG_THRUST = 12.12

# ── 全箭总质量 ────────────────────────────────────
MASS_TOTAL = MASS_DRY + MOTOR_TOTAL_MASS  # ~0.364 kg（远轻于1kg上限）

# ── 发射架 (Launch Rail) ─────────────────────────
RAIL_LENGTH = 1.0             # 发射导轨长度 [m]
RAIL_INCLINATION = 85         # 倾角 [°]（近乎垂直）
RAIL_HEADING = 0              # 方位角 [°]（正北）

# ── 环境 (Environment) ────────────────────────────
LAUNCH_LATITUDE = 39.9        # 纬度（北京附近）
LAUNCH_LONGITUDE = 116.4      # 经度
LAUNCH_ELEVATION = 50         # 海拔 [m]

# ── 全箭长度 ──────────────────────────────────────
TOTAL_LENGTH = NOSE_LENGTH + BODY_LENGTH  # 0.75 m
CALIBER = BODY_OUTER_RADIUS * 2            # 管径 0.075 m


if __name__ == "__main__":
    print("=" * 50)
    print("  Ad Astra 探空火箭 — 基线参数总览")
    print("=" * 50)
    print(f"  全箭长度:       {TOTAL_LENGTH * 1000:.0f} mm")
    print(f"  机身管外径:     {BODY_OUTER_RADIUS * 2 * 1000:.0f} mm")
    print(f"  整流罩:         {NOSE_TYPE}, L={NOSE_LENGTH*1000:.0f} mm")
    print(f"  尾翼:           {FIN_COUNT} 片梯形翼, 翼展 {FIN_SPAN*1000:.0f} mm")
    print(f"  干重:           {MASS_DRY*1000:.0f} g")
    print(f"  发动机:         Estes C6-5, 总冲 {MOTOR_TOTAL_IMPULSE} N·s")
    print(f"  起飞质量:       {MASS_TOTAL*1000:.0f} g")
    print("=" * 50)
