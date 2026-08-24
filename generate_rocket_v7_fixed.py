#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
🚀 Ad Astra 火箭 - v7.1 修复版
修复所有连接问题
==============================================================================
"""
import numpy as np
import trimesh
import os
import math
from datetime import datetime

BODY_R = 37.5
BODY_D = BODY_R * 2
WALL = 2.5
SEG = 48
OUTPUT = r"D:\AI_rocket\3d_print_files"
os.makedirs(OUTPUT, exist_ok=True)

# ============================================================================
# 零件尺寸
# ============================================================================
L_NOSE = 190
L_BODY = 630
L_AV = 120
L_TVC = 85
L_GIM = 50
L_NOZ = 180

# ============================================================================
# 精确坐标 (右端=+X, 左端=-X, 紧密连接)
# ============================================================================
# 整流罩: 0 ~ 190
X_NOSE_END = L_NOSE

# 机身: -630 ~ 0 (右端接整流罩)
X_BODY_END = 0
X_BODY_START = -L_BODY

# 航电舱: 机身内部
X_AV_START = X_BODY_START + 150
X_AV_END = X_AV_START + L_AV

# TVC底座: 机身左端
X_TVC_END = X_BODY_START
X_TVC_START = X_TVC_END - L_TVC

# 万向节: TVC底座左端
X_GIM_END = X_TVC_START
X_GIM_START = X_GIM_END - L_GIM

# 喷管: 万向节左端
X_NOZ_END = X_GIM_START
X_NOZ_START = X_NOZ_END - L_NOZ

print("=" * 60)
print("坐标验证:")
print(f"  整流罩: {0} ~ {X_NOSE_END} (L={L_NOSE})")
print(f"  机身:   {X_BODY_START} ~ {X_BODY_END} (L={L_BODY})")
print(f"  TVC底:  {X_TVC_START} ~ {X_TVC_END} (L={L_TVC})")
print(f"  万向节: {X_GIM_START} ~ {X_GIM_END} (L={L_GIM})")
print(f"  喷管:   {X_NOZ_START} ~ {X_NOZ_END} (L={L_NOZ})")
print(f"  总长: {X_NOSE_END - X_NOZ_START}mm")
print()

# ============================================================================
# 基础几何
# ============================================================================
def cyl(radius, x1, x2, seg=SEG):
    """创建圆柱体, 从x1到x2"""
    L = x2 - x1
    c = trimesh.creation.cylinder(radius=radius, height=L, sections=seg)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    c.apply_translation([x1 + L/2, 0, 0])
    return c

def tube(outer_r, inner_r, x1, x2, seg=SEG):
    """创建空心管, 从x1到x2"""
    L = x2 - x1
    outer = trimesh.creation.cylinder(radius=outer_r, height=L, sections=seg)
    inner = trimesh.creation.cylinder(radius=inner_r, height=L, sections=seg)
    outer.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    inner.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 1, 0]))
    outer.apply_translation([x1 + L/2, 0, 0])
    inner.apply_translation([x1 + L/2, 0, 0])
    try:
        result = outer.difference(inner)
        if result and len(result.vertices) > 0:
            return result
    except:
        pass
    # 手动构建
    verts, faces = [], []
    for i, theta in enumerate(np.linspace(0, 2*np.pi, seg, endpoint=False)):
        c, s = np.cos(theta), np.sin(theta)
        for x in [x1, x2]:
            verts.append([x, outer_r*c, outer_r*s])
        for x in [x1, x2]:
            verts.append([x, inner_r*c, inner_r*s])
    for i in range(seg):
        i2 = (i+1)%seg
        a0,a1,a2,a3 = 4*i,4*i+1,4*i+2,4*i+3
        b0,b1,b2,b3 = 4*i2,4*i2+1,4*i2+2,4*i2+3
        faces += [[a0,b0,b1],[a0,b1,a1],[a2,a3,b3],[a2,b3,b2],
                   [a0,a2,b2],[a0,b2,b0],[a1,b1,b3],[a1,b3,a3]]
    return trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))

def revolve(xs, rs_out, rs_in, seg=SEG):
    """旋转体"""
    n = len(xs)
    verts = []
    for xi, ro, ri in zip(xs, rs_out, rs_in):
        for theta in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
            verts.append([xi, ro*c, ro*s])
    outer_n = len(verts)
    for xi, ro, ri in zip(xs, rs_out, rs_in):
        for theta in np.linspace(0, 2*np.pi, seg, endpoint=False):
            c, s = np.cos(theta), np.sin(theta)
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
# 01. 整流罩
# ============================================================================
def build_nose():
    parts = []
    
    # Von Karman 主体: x 从 X_NOSE_END(=190) 到 15
    xs, ro, ri = [], [], []
    for i in range(40):
        t = i / 39
        x = X_NOSE_END - t * (L_NOSE - 15)
        sigma = 0.8
        r_out = BODY_R * math.sqrt(max(0.001, 2*sigma*t - t*t))
        r_in = max(0.5, r_out - WALL)
        xs.append(x)
        ro.append(r_out)
        ri.append(r_in)
    parts.append(revolve(xs, ro, ri))
    
    # 法兰: x 从 0 到 15
    parts.append(tube(BODY_R - 1, BODY_R - WALL - 1, 0, 15))
    
    # O型圈槽: x=5 到 9
    parts.append(tube(BODY_R + 0.5, BODY_R - 2, 5, 9))
    
    # 6个M3螺栓孔
    for i in range(6):
        theta = math.radians(i * 60)
        hy = (BODY_R - 8) * math.cos(theta)
        hz = (BODY_R - 8) * math.sin(theta)
        h = cyl(1.5, 8, 22, seg=8)
        h.apply_translation([0, hy, hz])
        parts.append(h)
    
    nose = trimesh.util.concatenate(parts)
    nose.export(os.path.join(OUTPUT, "01_nose_cone.stl"))
    nose.export(os.path.join(OUTPUT, "01_nose_cone.glb"))
    b = nose.bounds
    print(f"  01 整流罩: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return nose

# ============================================================================
# 02. 机身管
# ============================================================================
def build_body():
    parts = []
    
    # 主空心管: x=-630 到 x=0
    parts.append(tube(BODY_R, BODY_R - WALL, X_BODY_START, X_BODY_END))
    
    # 加强肋 (内部, 不影响外径)
    for i in range(4):
        theta = math.radians(i * 90)
        rib = tube(3, 0, X_BODY_START + 20, X_BODY_END - 20, seg=12)
        v = rib.vertices.copy()
        v[:, 1] += (BODY_R - WALL - 1.5) * math.cos(theta)
        v[:, 2] += (BODY_R - WALL - 1.5) * math.sin(theta)
        rib.vertices = v
        parts.append(rib)
    
    # 穿线孔
    for wx in [-480, -380, -280]:
        for sign in [-1, 1]:
            h = cyl(3, wx - 8, wx + 8, seg=10)
            h.apply_translation([0, (BODY_R + 2) * sign, 0])
            parts.append(h)
    
    # 机身两端螺栓孔
    for bx in [X_BODY_END - 15, X_BODY_START + 15]:
        for i in range(4):
            theta = math.radians(i * 90 + 45)
            by = (BODY_R - 5) * math.cos(theta)
            bz = (BODY_R - 5) * math.sin(theta)
            h = cyl(2.5, bx - 15, bx + 15, seg=8)
            h.apply_translation([0, by, bz])
            parts.append(h)
    
    body = trimesh.util.concatenate(parts)
    body.export(os.path.join(OUTPUT, "02_body_tube.stl"))
    body.export(os.path.join(OUTPUT, "02_body_tube.glb"))
    b = body.bounds
    print(f"  02 机身管: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return body

# ============================================================================
# 03. 尾翼
# ============================================================================
def build_fins():
    fins = []
    ROOT = 150
    TIP = 50
    SPAN = 65
    THICK = 5
    FIN_X = X_BODY_START + 5  # -625
    
    for f in range(4):
        theta = math.radians(f * 90)
        cy0, cz0 = math.cos(theta), math.sin(theta)
        ty, tz = -cz0, cy0
        
        corners = [
            [FIN_X, BODY_R],
            [FIN_X + ROOT, BODY_R],
            [FIN_X + ROOT, BODY_R + SPAN],
            [FIN_X + ROOT - TIP + 15, BODY_R + SPAN],  # 后掠
        ]
        
        verts = []
        for px, pr in corners:
            by, bz = pr*cy0, pr*cz0
            h = THICK / 2 * (1.5 if px < FIN_X + 30 else 1.0)
            verts.append([px, by - ty*h, bz - tz*h])
            verts.append([px, by + ty*h, bz + tz*h])
        
        faces = [
            [0,2,3],[0,3,1],[2,4,5],[2,5,3],
            [4,6,7],[4,7,5],[6,0,1],[6,1,7],
            [0,4,2],[0,6,4],[1,3,5],[1,5,7]
        ]
        fin = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
        fins.append(fin)
        
        # M4螺栓孔
        for bt in [0.25, 0.5, 0.75]:
            bx = FIN_X + bt * ROOT
            h = cyl(2, FIN_X - 5, FIN_X + 5, seg=8)
            h.apply_translation([bx, 0, 0])
            v = h.vertices.copy()
            new = np.zeros_like(v)
            new[:, 0] = v[:, 0]
            new[:, 1] = v[:, 1]*cy0 - v[:, 2]*cz0
            new[:, 2] = v[:, 1]*cz0 + v[:, 2]*cy0
            h.vertices = new
            fins.append(h)
    
    all_fins = trimesh.util.concatenate(fins)
    all_fins.export(os.path.join(OUTPUT, "03_fins_x4.stl"))
    all_fins.export(os.path.join(OUTPUT, "03_fins_x4.glb"))
    b = all_fins.bounds
    print(f"  03 尾翼×4: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return all_fins

# ============================================================================
# 04. 航电舱
# ============================================================================
def build_avionics():
    parts = []
    AV_R = BODY_R - WALL - 3
    AW = 2
    
    parts.append(tube(AV_R, AV_R - AW, X_AV_START, X_AV_END))
    
    # 端盖
    for ex in [X_AV_START - 2, X_AV_END]:
        parts.append(cyl(AV_R - AW, ex, ex + 2))
    
    # 检修盖板
    hx = X_AV_START + 30
    parts.append(cyl(AV_R * 0.7, hx, hx + 3))
    for i in range(6):
        theta = math.radians(i * 60)
        h = cyl(1.5, hx - 2, hx + 2, seg=8)
        h.apply_translation([0, (AV_R * 0.7 + 4) * math.cos(theta), (AV_R * 0.7 + 4) * math.sin(theta)])
        parts.append(h)
    
    av = trimesh.util.concatenate(parts)
    av.export(os.path.join(OUTPUT, "04_avionics_bay.stl"))
    av.export(os.path.join(OUTPUT, "04_avionics_bay.glb"))
    b = av.bounds
    print(f"  04 航电舱: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return av

# ============================================================================
# 05. TVC底座
# ============================================================================
def build_tvc():
    parts = []
    FR = BODY_R + 8
    CHR = 22
    L = L_TVC
    
    parts.append(tube(FR, CHR, X_TVC_START, X_TVC_END))
    
    # 连接法兰 (在 TVC 内部, 不延伸到机身)
    parts.append(tube(BODY_R + 3, CHR, X_TVC_END - 5, X_TVC_END))
    
    # M5螺栓孔
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        h = cyl(2.5, X_TVC_START - 10, X_TVC_START + 10, seg=8)
        h.apply_translation([0, (FR - 5) * math.cos(theta), (FR - 5) * math.sin(theta)])
        parts.append(h)
    
    # 轴承座
    for i in range(4):
        theta = math.radians(i * 90)
        bcx = X_TVC_START + L/2
        bcy = (FR + 12) * math.cos(theta)
        bcz = (FR + 12) * math.sin(theta)
        b = cyl(10, bcx - 6, bcx + 6, seg=16)
        v = b.vertices.copy()
        v[:, 1] += bcy
        v[:, 2] += bcz
        b.vertices = v
        parts.append(b)
        # 轴承孔
        bh = cyl(5, bcx - 12, bcx + 12, seg=12)
        bh.apply_translation([0, bcy, bcz])
        parts.append(bh)
    
    # 舵机安装孔
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        h = cyl(3, X_TVC_START + 5, X_TVC_START + 18, seg=10)
        h.apply_translation([0, (CHR + 8) * math.cos(theta), (CHR + 8) * math.sin(theta)])
        parts.append(h)
    
    tvc = trimesh.util.concatenate(parts)
    tvc.export(os.path.join(OUTPUT, "05_tvc_base.stl"))
    tvc.export(os.path.join(OUTPUT, "05_tvc_base.glb"))
    b = tvc.bounds
    print(f"  05 TVC底座: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return tvc

# ============================================================================
# 06. TVC万向节
# ============================================================================
def build_gimbal():
    parts = []
    OR = BODY_R + 2
    IR = OR - 10
    MID = X_GIM_START + L_GIM / 2
    
    parts.append(tube(OR, OR - 8, X_GIM_START + 3, X_GIM_END))
    parts.append(tube(IR, IR - 6, X_GIM_START + 15, X_GIM_END - 15))
    
    for i in range(4):
        theta = math.radians(i * 90)
        py = (OR + 12) * math.cos(theta)
        pz = (OR + 12) * math.sin(theta)
        p = cyl(4, MID - 4, MID + 4, seg=14)
        p.apply_translation([0, py, pz])
        parts.append(p)
        bh = cyl(2.5, MID - 18, MID + 18, seg=10)
        bh.apply_translation([0, py, pz])
        parts.append(bh)
    
    for i in range(4):
        theta = math.radians(i * 90 + 45)
        ay = (IR + 18) * math.cos(theta)
        az = (IR + 18) * math.sin(theta)
        a = cyl(5, MID - 4, MID + 4, seg=12)
        a.apply_translation([0, ay, az])
        parts.append(a)
    
    gim = trimesh.util.concatenate(parts)
    gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.stl"))
    gim.export(os.path.join(OUTPUT, "06_tvc_gimbal.glb"))
    b = gim.bounds
    print(f"  06 TVC万向节: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return gim

# ============================================================================
# 07. TVC喷管
# ============================================================================
def build_nozzle():
    parts = []
    RI = 30
    RT = 16
    RE = 26
    W = 4
    LC = 50
    LD = LC * 2
    
    x_in = X_NOZ_END
    x_th = x_in - LC
    x_ex = x_th - LD
    
    # 入口法兰
    FRI = RI + 12
    parts.append(tube(FRI, RI, x_in - 5, x_in + 5))  # 短法兰，不延伸
    for i in range(8):
        theta = math.radians(i * 45)
        h = cyl(2.5, x_in - 3, x_in + 18, seg=8)
        h.apply_translation([0, (FRI - 5) * math.cos(theta), (FRI - 5) * math.sin(theta)])
        parts.append(h)
    
    # 收敛-扩散段
    xs, ro, ri = [], [], []
    for i in range(25):
        t = i / 24
        x = x_in - t * LC
        r = RI - (RI - RT) * (t ** 0.7)
        xs.append(x); ro.append(r + W); ri.append(r)
    for i in range(1, 40):
        t = i / 40
        x = x_th - t * LD
        r = RT + (RE - RT) * (t ** 1.3)
        xs.append(x); ro.append(r + W); ri.append(r)
    parts.append(revolve(xs, ro, ri))
    
    # 喉道加强
    parts.append(tube(RT + W + 3, RT, x_th - 3, x_th + 3))
    
    # 出口法兰
    FRE = RE + 10
    parts.append(tube(FRE, RE, x_ex - 10, x_ex))
    for i in range(8):
        theta = math.radians(i * 45)
        h = cyl(2.5, x_ex - 15, x_ex + 3, seg=8)
        h.apply_translation([0, (FRE - 5) * math.cos(theta), (FRE - 5) * math.sin(theta)])
        parts.append(h)
    
    # 散热肋
    for i in range(4):
        theta = math.radians(i * 90)
        rib = tube(W * 0.6, W * 0.3, x_in + 15, x_ex - 10, seg=8)
        v = rib.vertices.copy()
        v[:, 1] += (RI + W + 3) * math.cos(theta)
        v[:, 2] += (RI + W + 3) * math.sin(theta)
        rib.vertices = v
        parts.append(rib)
    
    noz = trimesh.util.concatenate(parts)
    noz.export(os.path.join(OUTPUT, "07_tvc_nozzle.stl"))
    noz.export(os.path.join(OUTPUT, "07_tvc_nozzle.glb"))
    b = noz.bounds
    print(f"  07 TVC喷管: X=[{b[0][0]:.0f},{b[1][0]:.0f}] ✅")
    return noz

# ============================================================================
# 主程序
# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Ad Astra 火箭 v7.1 修复版")
    print("=" * 60)
    
    parts = []
    parts.append(build_nose())
    parts.append(build_body())
    parts.append(build_fins())
    parts.append(build_avionics())
    parts.append(build_tvc())
    parts.append(build_gimbal())
    parts.append(build_nozzle())
    
    assembly = trimesh.util.concatenate(parts)
    assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.stl"))
    assembly.export(os.path.join(OUTPUT, "08_full_rocket_assembly.glb"))
    
    b = assembly.bounds
    print()
    print("=" * 60)
    print(f"✅ 完整装配: X=[{b[0][0]:.0f},{b[1][0]:.0f}] 总长 {b[1][0]-b[0][0]:.0f}mm")
    print(f"   面数: {len(assembly.faces):,}")
    print("=" * 60)
    
    # 连接验证
    print()
    print("🔍 连接验证:")
    nose_b = parts[0].bounds
    body_b = parts[1].bounds
    tvc_b = parts[4].bounds
    gim_b = parts[5].bounds
    noz_b = parts[6].bounds
    
    checks = [
        ("整流罩-机身", nose_b[0][0], body_b[1][0]),
        ("机身-TVc", body_b[0][0], tvc_b[0][0]),
        ("TVC-万向节", tvc_b[0][0], gim_b[0][0]),
        ("万向节-喷管", gim_b[0][0], noz_b[1][0]),
    ]
    
    all_ok = True
    for name, a, b_val in checks:
        gap = abs(a - b_val)
        status = "✅" if gap < 1 else "❌"
        if gap >= 1:
            all_ok = False
        print(f"  {name}: {a:.0f} 与 {b_val:.0f} → 间隙 {gap:.1f}mm {status}")
    
    if all_ok:
        print("  所有连接紧密无间隙!")
    print()
    print("🌐 http://localhost:8000/viewer.html")
