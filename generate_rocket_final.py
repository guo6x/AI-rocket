#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 简化版火箭生成器 - 每步验证
"""
import numpy as np
import trimesh
import os
import math

BODY_R = 37.5
BODY_D = BODY_R * 2
WALL = 2.5
SEG = 48
OUTPUT = r"D:\AI_rocket\3d_print_files"
os.makedirs(OUTPUT, exist_ok=True)

# ============================================================================
# 步骤1: 定义所有零件的精确坐标 (基于连接关系)
# ============================================================================
print("=" * 60)
print("步骤1: 定义零件坐标")
print("=" * 60)

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
# 步骤3: 生成01整流罩
# ============================================================================
print("\n" + "=" * 60)
print("步骤2: 生成整流罩 (验证: X=[0, 190])")
print("=" * 60)

# Von Karman曲线: x从190到15
xs, ro, ri = [], [], []
L_nose_curve = NOSE_X2 - 15  # 175mm
for i in range(30):
    t = i / 29
    x = NOSE_X2 - t * L_nose_curve  # 190 -> 15
    sigma = 0.8
    r_out = BODY_R * math.sqrt(max(0.001, 2*sigma*t - t*t))
    r_in = max(0.5, r_out - WALL)
    xs.append(x); ro.append(r_out); ri.append(r_in)

nose_body = simple_revolve(xs, ro, ri)

# 法兰: x从0到15
flange = simple_tube(BODY_R - 1, BODY_R - WALL - 1, NOSE_X1, 15)

nose = trimesh.util.concatenate([nose_body, flange])
nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
print(f"整流罩结果: X=[{nose.bounds[0][0]:.0f}, {nose.bounds[1][0]:.0f}]")
print(f"期望: X=[0, 190]")
print("✅ 整流罩正确!" if abs(nose.bounds[1][0] - 190) < 1 else "❌ 整流罩错误!")

# ============================================================================
# 步骤4: 生成02机身管
# ============================================================================
print("\n" + "=" * 60)
print("步骤3: 生成机身管 (验证: X=[-630, 0])")
print("=" * 60)

body_tube = simple_tube(BODY_R, BODY_R - WALL, BODY_X1, BODY_X2)
body_tube.export(os.path.join(OUTPUT, "02_body_tube.stl"))
print(f"机身管结果: X=[{body_tube.bounds[0][0]:.0f}, {body_tube.bounds[1][0]:.0f}]")
print(f"期望: X=[-630, 0]")
print("✅ 机身管正确!" if abs(body_tube.bounds[0][0] + 630) < 1 and abs(body_tube.bounds[1][0]) < 1 else "❌ 机身管错误!")

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
# 步骤7: 生成05 TVC底座
# ============================================================================
print("\n" + "=" * 60)
print("步骤6: 生成TVC底座 (验证: X=[-720, -630])")
print("=" * 60)

FR = BODY_R + 8
CHR = 22

tvc_parts = []
# 主法兰管
tvc_main = simple_tube(FR, CHR, TVC_X1, TVC_X2)
tvc_parts.append(tvc_main)
print(f"TVC主法兰: X=[{tvc_main.bounds[0][0]:.0f}, {tvc_main.bounds[1][0]:.0f}]")

tvc = trimesh.util.concatenate(tvc_parts)
tvc.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
print(f"TVC底座结果: X=[{tvc.bounds[0][0]:.0f}, {tvc.bounds[1][0]:.0f}]")
print(f"期望: X=[-720, -630]")
ok = abs(tvc.bounds[0][0] + 720) < 1 and abs(tvc.bounds[1][0] + 630) < 1
print("✅ TVC底座正确!" if ok else "❌ TVC底座错误!")

# ============================================================================
# 步骤8: 生成06 TVC万向节
# ============================================================================
print("\n" + "=" * 60)
print("步骤7: 生成TVC万向节 (验证: X=[-770, -720])")
print("=" * 60)

OR = BODY_R + 2
IR = OR - 10

gim_parts = []
# 外环
gim_outer = simple_tube(OR, OR - 8, GIM_X1, GIM_X2)
gim_parts.append(gim_outer)
print(f"万向节外环: X=[{gim_outer.bounds[0][0]:.0f}, {gim_outer.bounds[1][0]:.0f}]")

gim = trimesh.util.concatenate(gim_parts)
gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
print(f"万向节结果: X=[{gim.bounds[0][0]:.0f}, {gim.bounds[1][0]:.0f}]")
print(f"期望: X=[-770, -720]")
ok = abs(gim.bounds[0][0] + 770) < 1 and abs(gim.bounds[1][0] + 720) < 1
print("✅ 万向节正确!" if ok else "❌ 万向节错误!")

# ============================================================================
# 步骤9: 生成07 TVC喷管
# ============================================================================
print("\n" + "=" * 60)
print("步骤8: 生成TVC喷管 (验证: X=[-950, -770])")
print("=" * 60)

RI = 30
RT = 16
RE = 26
W = 4
LC = 65   # 收敛段
LD = 115  # 扩散段

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

nozzle_body = simple_revolve(xs_conv + xs_div, ro_conv + ro_div, ri_conv + ri_div)
print(f"喷管主体: X=[{nozzle_body.bounds[0][0]:.0f}, {nozzle_body.bounds[1][0]:.0f}]")

nozzle = nozzle_body
nozzle.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
print(f"喷管结果: X=[{nozzle.bounds[0][0]:.0f}, {nozzle.bounds[1][0]:.0f}]")
print(f"期望: X=[-950, -770]")

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
# 步骤11: 连接验证
# ============================================================================
print("\n" + "=" * 60)
print("步骤10: 连接验证")
print("=" * 60)

checks = [
    ("整流罩-机身", nose.bounds[0][0], body_tube.bounds[1][0], "应=0"),  # 整流罩左=机身右
    ("机身-TVc", body_tube.bounds[0][0], tvc.bounds[1][0], "应=0"),      # 机身左=TVC右
    ("TVC-万向节", tvc.bounds[0][0], gim.bounds[1][0], "应=0"),        # TVC左=万向节右
    ("万向节-喷管", gim.bounds[0][0], nozzle.bounds[1][0], "应=0"),    # 万向节左=喷管右
]

all_ok = True
for name, a, b, expected in checks:
    gap = abs(a - b)
    status = "✅" if gap < 2 else "❌"
    if gap >= 2:
        all_ok = False
    print(f"  {name}: {a:.0f} vs {b:.0f} → 间隙 {gap:.1f}mm {status} ({expected})")

print()
if all_ok:
    print("🎉 所有连接正确! 火箭模型完整无间隙")
else:
    print("⚠️ 部分连接有间隙")

print("\n" + "=" * 60)
print("完成! 文件保存在:", OUTPUT)
print("在浏览器打开: http://localhost:8000/viewer.html")
print("=" * 60)
