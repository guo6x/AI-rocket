#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 简化版火箭生成器 - 每步验证
"""
import numpy as np
import trimesh
import os
import math

WALL = 2.5  # 壁厚
SEG = 48
OUTPUT = r"D:\AI_rocket\3d_print_files"
os.makedirs(OUTPUT, exist_ok=True)

def get_section_radius(mesh, x_coord, axis='Y'):
    """获取指定X坐标截面处的半径"""
    axis_idx = 1 if axis == 'Y' else 2
    verts_at_x = [v[axis_idx] for v in mesh.vertices if abs(v[0] - x_coord) < 0.5]
    if verts_at_x:
        return (max(verts_at_x) - min(verts_at_x)) / 2
    return 0

# ============================================================================
# 步骤1: 定义所有零件的精确坐标和半径 (基于连接关系)
# ============================================================================
print("=" * 60)
print("步骤1: 定义零件坐标和半径")
print("=" * 60)

# ========== 坐标定义 ==========
# 整流罩: x = 0 到 190 (右端=尖头)
NOSE_X1, NOSE_X2 = 0, 190

# 机身: x = -630 到 0 (右端接整流罩)
BODY_X1, BODY_X2 = -630, 0

# TVC底座: 右端接机身左端(-630)，左端 = -630 - 85 = -715
TVC_X1, TVC_X2 = -715, -630

# 万向节: 右端接TVC左端(-715)，左端 = -715 - 50 = -765
GIM_X1, GIM_X2 = -765, -715

# 喷管: 右端接万向节左端(-765)，左端 = -765 - 180 = -945
NOZ_X1, NOZ_X2 = -945, -765

# ========== 半径定义 ==========
BODY_R = 37.5          # 机身外半径
BODY_RI = BODY_R - 2.5 # 机身内半径 = 35mm

# 整流罩：插入机身，外径略小于机身内径
NOSE_RO = BODY_RI - 0.5  # 34.5mm（插入机身，间隙0.5mm）
NOSE_RI = NOSE_RO - WALL  # 32mm（壁厚2.5mm）

# TVC底座：右端接机身左端(37.5mm)
TVC_R_RIGHT = BODY_R           # 37.5mm（匹配机身）
TVC_RI_RIGHT = TVC_R_RIGHT - 5  # 内径32.5mm
TVC_R_LEFT = 40.0              # 40mm（过渡到万向节）
TVC_RI_LEFT = TVC_R_LEFT - 5   # 内径35mm

# 万向节：外径40mm (配合TVC左端)
GIM_OR = 40.0
GIM_IR = GIM_OR - 8.0  # 32mm

# 喷管：入口外径32mm（配合万向节内径32mm）
NOZ_RI = 28.0  # 喷管入口内半径
NOZ_RO_IN = NOZ_RI + 4  # 入口外半径 32mm
RT = 16  # 喉道半径
RE = 26  # 出口半径
W = 4    # 壁厚

print(f"整流罩: {NOSE_X1} ~ {NOSE_X2}")
print(f"机身:   {BODY_X1} ~ {BODY_X2}")
print(f"TVC底:  {TVC_X1} ~ {TVC_X2}")
print(f"万向节: {GIM_X1} ~ {GIM_X2}")
print(f"喷管:   {NOZ_X1} ~ {NOZ_X2}")

# ============================================================================
# 步骤2: 基础几何函数
# ============================================================================
def simple_cyl(r, x1, x2, seg=SEG):
    """简单圆柱体"""
    L = x2 - x1
    c = trimesh.creation.cylinder(radius=r, height=L, sections=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x1 + L/2, 0, 0])
    return c

def simple_tube(ro, ri, x1, x2, seg=SEG):
    """空心管"""
    outer = simple_cyl(ro, x1, x2, seg)
    inner = simple_cyl(ri, x1, x2, seg)
    try:
        result = outer.difference(inner)
        if result and len(result.vertices) > 0:
            return result
    except:
        pass
    # Fallback: 手动构建
    verts, faces = [], []
    for i, th in enumerate(np.linspace(0, 2*np.pi, seg, endpoint=False)):
        c, s = np.cos(th), np.sin(th)
        for x in [x1, x2]:
            verts.append([x, ro*c, ro*s])
        for x in [x1, x2]:
            verts.append([x, ri*c, ri*s])
    for i in range(seg):
        i2 = (i+1)%seg
        a0,a1,a2,a3 = 4*i,4*i+1,4*i+2,4*i+3
        b0,b1,b2,b3 = 4*i2,4*i2+1,4*i2+2,4*i2+3
        faces += [[a0,b0,b1],[a0,b1,a1],[a2,a3,b3],[a2,b3,b2],
                   [a0,a2,b2],[a0,b2,b0],[a1,b1,b3],[a1,b3,a3]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

def simple_revolve(xs, rs_out, rs_in, seg=SEG):
    """旋转体"""
    n = len(xs)
    verts = []
    for xi, ro, ri in zip(xs, rs_out, rs_in):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts.append([xi, ro*c, ro*s])
    outer_n = len(verts)
    for xi, ro, ri in zip(xs, rs_out, rs_in):
        for th in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(th), np.sin(th)
            verts.append([xi, ri*c, ri*s])
    faces = []
    def o(r, s): return r*seg + s
    def i(r, s): return outer_n + r*seg + s
    for r in range(n-1):
        for s in range(seg):
            s2 = (s+1)%seg
            faces += [[o(r,s),o(r+1,s),o(r+1,s2)],[o(r,s),o(r+1,s2),o(r,s2)]]
    for r in range(n-1):
        for s in range(seg):
            s2 = (s+1)%seg
            faces += [[i(r,s),i(r,s2),i(r+1,s2)],[i(r,s),i(r+1,s2),i(r+1,s)]]
    for s in range(seg):
        s2 = (s+1)%seg
        faces += [[o(0,s),o(0,s2),i(0,s2)],[o(0,s),i(0,s2),i(0,s)]]
    for s in range(seg):
        s2 = (s+1)%seg
        faces += [[o(n-1,s),o(n-1,s2),i(n-1,s2)],[o(n-1,s),i(n-1,s2),i(n-1,s)]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

# ============================================================================
# 步骤2: 生成01整流罩
# ============================================================================
print("\n" + "=" * 60)
print("步骤2: 生成整流罩 (验证: X=[0, 190])")
print("=" * 60)

# Von Karman曲线: x从190到15
# Von Karman曲线公式在t=1时只能达到约0.6*BODY_R
# 所以我们在曲线末端加一个圆柱过渡段，直接达到NOSE_RO
L_nose_curve = NOSE_X2 - 15  # 175mm (从X=190到X=15)

# 曲线段
xs, ro, ri = [], [], []
sigma = 0.8
for i in range(25):
    t = i / 24  # 0到1
    x = NOSE_X2 - t * L_nose_curve  # 190 -> 15
    r_out = NOSE_RO * math.sqrt(max(0.001, 2*sigma*t - t*t))
    r_in = max(NOSE_RI, r_out - WALL)
    xs.append(x); ro.append(r_out); ri.append(r_in)

# 检查曲线末端(X=15)半径，如果不够就加一段圆柱
t_end = 1.0
r_end = NOSE_RO * math.sqrt(max(0.001, 2*sigma*t_end - t_end*t_end))
print(f"曲线末端(X=15)半径: {r_end:.1f}mm, 目标: {NOSE_RO}mm")
if abs(r_end - NOSE_RO) > 2:
    xs.append(15); ro.append(NOSE_RO); ri.append(NOSE_RI)

nose_body = simple_revolve(xs, ro, ri)

# 法兰: x从0到15，与机身内径配合
flange = simple_tube(NOSE_RO + 1.0, NOSE_RI, NOSE_X1, 15)  # 外径稍大用于对接

nose = trimesh.util.concatenate([nose_body, flange])
nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))

# 整流罩底部在X=190处（尖端），插入端在X=0到X=15
nose_tip_radius = get_section_radius(nose, 190, 'Y')
nose_base_radius = get_section_radius(nose, 15, 'Y')  # 曲线末端
print(f"整流罩结果: X=[{nose.bounds[0][0]:.0f}, {nose.bounds[1][0]:.0f}]")
print(f"  尖端(X=190)半径: {nose_tip_radius:.1f}mm (应为 ~0mm)")
print(f"  底部(X=15)半径: {nose_base_radius:.1f}mm (应为 {NOSE_RO}mm)")
print(f"期望: X=[0, 190], 底部半径={NOSE_RO}mm")
ok = abs(nose.bounds[1][0] - 190) < 1 and abs(nose_base_radius - NOSE_RO) < 2
print("✅ 整流罩正确!" if ok else "❌ 整流罩错误!")

# ============================================================================
# 步骤3: 生成02机身管
# ============================================================================
print("\n" + "=" * 60)
print("步骤3: 生成机身管 (验证: X=[-630, 0], R=37.5mm)")
print("=" * 60)

body_tube = simple_tube(BODY_R, BODY_RI, BODY_X1, BODY_X2)
body_tube.export(os.path.join(OUTPUT, "02_body_tube.stl"))
body_radius = max(abs(body_tube.bounds[0][1]), abs(body_tube.bounds[1][1]))
print(f"机身管结果: X=[{body_tube.bounds[0][0]:.0f}, {body_tube.bounds[1][0]:.0f}]")
print(f"  外半径: {body_radius:.1f}mm (应为 {BODY_R}mm)")
print(f"期望: X=[-630, 0], R={BODY_R}mm")
ok = abs(body_tube.bounds[0][0] + 630) < 1 and abs(body_tube.bounds[1][0]) < 1 and abs(body_radius - BODY_R) < 1
print("✅ 机身管正确!" if ok else "❌ 机身管错误!")

# ============================================================================
# 步骤5: 生成03尾翼 (简单)
# ============================================================================
print("\n" + "=" * 60)
print("步骤4: 生成尾翼")
print("=" * 60)

fins = []
ROOT = 150
TIP = 50
SPAN = 60
THICK = 5
FIN_X = BODY_X1 + 5  # -625

for f in range(4):
    th = math.radians(f * 90)
    cy0, cz0 = math.cos(th), math.sin(th)
    ty, tz = -cz0, cy0
    
    corners = [
        [FIN_X, BODY_R],
        [FIN_X + ROOT, BODY_R],
        [FIN_X + ROOT, BODY_R + SPAN],
        [FIN_X + ROOT - TIP + 10, BODY_R + SPAN],
    ]
    
    verts = []
    for px, pr in corners:
        by, bz = pr*cy0, pr*cz0
        h = THICK / 2 * (1.5 if px < FIN_X + 30 else 1.0)
        verts.append([px, by - ty*h, bz - tz*h])
        verts.append([px, by + ty*h, bz + tz*h])
    
    faces = [[0,2,3],[0,3,1],[2,4,5],[2,5,3],[4,6,7],[4,7,5],[6,0,1],[6,1,7],[0,4,2],[0,6,4],[1,3,5],[1,5,7]]
    fin = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    fins.append(fin)

all_fins = trimesh.util.concatenate(fins)
all_fins.export(os.path.join(OUTPUT, "03_fins_x4.stl"))
print(f"尾翼结果: X=[{all_fins.bounds[0][0]:.0f}, {all_fins.bounds[1][0]:.0f}]")
print(f"期望: X=[-625, -475] (尾翼贴在机身尾部)")

# ============================================================================
# 步骤6: 生成04航电舱
# ============================================================================
print("\n" + "=" * 60)
print("步骤5: 生成航电舱")
print("=" * 60)

AV_R = BODY_R - WALL - 3
AV_LEN = 100
AV_X1 = BODY_X1 + 200
AV_X2 = AV_X1 + AV_LEN

av = simple_tube(AV_R, AV_R - 2, AV_X1, AV_X2)
av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
print(f"航电舱结果: X=[{av.bounds[0][0]:.0f}, {av.bounds[1][0]:.0f}]")
print(f"期望: X=[{AV_X1:.0f}, {AV_X2:.0f}]")

# ============================================================================
# 步骤5: 生成05 TVC底座 (锥形过渡)
# ============================================================================
print("\n" + "=" * 60)
print("步骤5: 生成TVC底座 (验证: X=[-715, -630])")
print("=" * 60)

# TVC底座设计：使用圆柱管（简化，匹配端面）
# 右端(X=-630): 外径37.5mm (配合机身左端37.5mm)
# 左端(X=-715): 外径40mm (配合万向节)
# 使用简单圆柱，避免旋转体边界问题
tvc_right_outer = simple_cyl(TVC_R_RIGHT, -640, -630)  # 右端短圆柱
tvc_left_outer = simple_cyl(TVC_R_LEFT, -715, -640)    # 左端过渡圆柱
tvc_right_inner = simple_cyl(TVC_RI_RIGHT, -640, -630)  # 右端内孔
tvc_left_inner = simple_cyl(TVC_RI_LEFT, -715, -640)    # 左端内孔

# 合并外表面
tvc_outer = trimesh.util.concatenate([tvc_right_outer, tvc_left_outer])
tvc_inner = trimesh.util.concatenate([tvc_right_inner, tvc_left_inner])

# 布尔运算得到空心管
try:
    tvc = tvc_outer.difference(tvc_inner)
except:
    tvc = tvc_outer

tvc.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
tvc_right_radius = max(abs(tvc.bounds[1][1]), abs(tvc.bounds[1][2]))  # X=-630处
tvc_left_radius = max(abs(tvc.bounds[0][1]), abs(tvc.bounds[0][2]))    # X=-715处
print(f"TVC底座结果: X=[{tvc.bounds[0][0]:.0f}, {tvc.bounds[1][0]:.0f}]")
print(f"  右端(X=-630)外半径: {tvc_right_radius:.1f}mm (应为 {TVC_R_RIGHT}mm)")
print(f"  左端(X=-715)外半径: {tvc_left_radius:.1f}mm (应为 {TVC_R_LEFT}mm)")
print(f"期望: X=[-715, -630]")
ok = abs(tvc.bounds[0][0] + 715) < 1 and abs(tvc.bounds[1][0] + 630) < 1
print("✅ TVC底座正确!" if ok else "❌ TVC底座错误!")

# ============================================================================
# 步骤6: 生成06 TVC万向节
# ============================================================================
print("\n" + "=" * 60)
print("步骤6: 生成TVC万向节 (验证: X=[-765, -715])")
print("=" * 60)

# 万向节：外径40mm (配合TVC左端外径)，内径32mm (容纳喷管)
gim = simple_tube(GIM_OR, GIM_IR, GIM_X1, GIM_X2)
gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
gim_right_radius = max(abs(gim.bounds[1][1]), abs(gim.bounds[1][2]))  # X=-715处
gim_left_radius = max(abs(gim.bounds[0][1]), abs(gim.bounds[0][2]))  # X=-765处
print(f"万向节结果: X=[{gim.bounds[0][0]:.0f}, {gim.bounds[1][0]:.0f}]")
print(f"  右端(X=-715)外半径: {gim_right_radius:.1f}mm (应为 {GIM_OR}mm)")
print(f"  左端(X=-765)外半径: {gim_left_radius:.1f}mm (应为 {GIM_OR}mm)")
print(f"  内半径: {GIM_IR}mm (喷管入口外径={NOZ_RO_IN}mm)")
print(f"期望: X=[-765, -715]")
ok = abs(gim.bounds[0][0] + 765) < 1 and abs(gim.bounds[1][0] + 715) < 1
print("✅ 万向节正确!" if ok else "❌ 万向节错误!")

# ============================================================================
# 步骤7: 生成07 TVC喷管
# ============================================================================
print("\n" + "=" * 60)
print("步骤7: 生成TVC喷管 (验证: X=[-945, -765])")
print("=" * 60)

# 喷管设计：收敛-扩散型
# 入口(X=-765): 外径34mm, 内径30mm (配合万向节内径32mm)
# 喉道(X=-830): 外径20mm, 内径16mm
# 出口(X=-945): 外径30mm, 内径26mm
RI = NOZ_RI  # 30mm 入口内半径
RT = 16      # 喉道半径
RE = 26      # 出口半径
W = 4        # 壁厚
LC = 65      # 收敛段
LD = 115     # 扩散段

x_in = NOZ_X2  # -765
x_th = x_in - LC  # -830
x_ex = NOZ_X1  # -945

# 收敛段 (20点)
xs_conv, ro_conv, ri_conv = [], [], []
for i in range(20):
    t = i / 19
    x = x_in - t * LC
    r = RI - (RI - RT) * (t ** 0.7)
    xs_conv.append(x); ro_conv.append(r + W); ri_conv.append(r)

# 扩散段 (40点)
xs_div, ro_div, ri_div = [], [], []
for i in range(1, 40):
    t = i / 40
    x = x_th - t * LD
    r = RT + (RE - RT) * (t ** 1.3)
    xs_div.append(x); ro_div.append(r + W); ri_div.append(r)

nozzle = simple_revolve(xs_conv + xs_div, ro_conv + ro_div, ri_conv + ri_div)
nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
nozzle_in_radius = max(abs(nozzle.bounds[1][1]), abs(nozzle.bounds[1][2]))  # X=-765处
print(f"喷管结果: X=[{nozzle.bounds[0][0]:.0f}, {nozzle.bounds[1][0]:.0f}]")
print(f"  入口外半径(X=-765): {nozzle_in_radius:.1f}mm (应为 {NOZ_RO_IN}mm)")
print(f"期望: X=[-945, -765]")

# ============================================================================
# 步骤10: 组装完整火箭
# ============================================================================
print("\n" + "=" * 60)
print("步骤9: 组装完整火箭")
print("=" * 60)

parts = [nose, body_tube, all_fins, av, tvc, gim, nozzle]
assembly = trimesh.util.concatenate(parts)
assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.stl"))

print(f"\n完整火箭: X=[{assembly.bounds[0][0]:.0f}, {assembly.bounds[1][0]:.0f}]")
print(f"总长度: {assembly.bounds[1][0] - assembly.bounds[0][0]:.0f}mm")
print(f"面数: {len(assembly.faces):,}")

# ============================================================================
# 步骤8: 连接和半径验证
# ============================================================================
print("\n" + "=" * 60)
print("步骤8: 连接验证 (端面 + 截面半径)")
print("=" * 60)

# 获取各零件的关键半径（使用截面检查）
nose_radius = get_section_radius(nose, nose.bounds[1][0], 'Y')  # 整流罩底部(X=190处)
body_left_radius = get_section_radius(body_tube, body_tube.bounds[0][0], 'Y')  # 机身左端
body_right_radius = get_section_radius(body_tube, body_tube.bounds[1][0], 'Y')  # 机身右端
tvc_right_radius = get_section_radius(tvc, -630, 'Y')  # TVC右端(X=-630)
tvc_left_radius = get_section_radius(tvc, tvc.bounds[0][0], 'Y')  # TVC左端
gim_radius = get_section_radius(gim, gim.bounds[0][0], 'Y')  # 万向节
nozzle_in_radius = get_section_radius(nozzle, nozzle.bounds[1][0], 'Y')  # 喷管入口

print("端面匹配 (X方向):")
checks = [
    ("整流罩-机身", nose.bounds[0][0], body_tube.bounds[1][0], 0),
    ("机身-TVc", body_tube.bounds[0][0], tvc.bounds[1][0], 0),
    ("TVC-万向节", tvc.bounds[0][0], gim.bounds[1][0], 0),
    ("万向节-喷管", gim.bounds[0][0], nozzle.bounds[1][0], 0),
]

all_ok = True
for name, a, b, expected in checks:
    gap = abs(a - b)
    status = "✅" if gap < 2 else "❌"
    if gap >= 2:
        all_ok = False
    print(f"  {name}: {a:.0f} vs {b:.0f} → 间隙 {gap:.1f}mm {status}")

print("\n截面半径匹配 (连接处):")
radius_checks = [
    ("整流罩底部", nose_radius, body_right_radius, "整流罩(X=190) vs 机身右端(X=0)"),
    ("机身左端", body_left_radius, tvc_right_radius, "机身左端(X=-630) vs TVC右端(X=-630)"),
    ("TVC左端", tvc_left_radius, gim_radius, "TVC左端 vs 万向节右端"),
    ("万向节-喷管", get_section_radius(gim, -765, 'Y') - 8, nozzle_in_radius - 4, "万向节内径 vs 喷管入口"),
]

for name, a, b, desc in radius_checks:
    diff = abs(a - b)
    status = "✅" if diff < 2 else "⚠️"
    print(f"  {desc}: {a:.1f}mm vs {b:.1f}mm → 差{diff:.1f}mm {status}")

print()
if all_ok:
    print("🎉 所有连接正确! 火箭模型完整无间隙")
else:
    print("⚠️ 部分连接有间隙")

print("\n" + "=" * 60)
print("完成! 文件保存在:", OUTPUT)
print("在浏览器打开: http://localhost:8000/viewer.html")
print("=" * 60)
