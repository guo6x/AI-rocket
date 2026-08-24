import numpy as np
import trimesh
from scipy.spatial import cKDTree
import time
import os
from skimage.measure import marching_cubes

# ==============================================================================
# 航天级 航电舱异星骨骼防护套 V3 (High-Resolution Edition)
# 核心特性：
# 1. 超高分辨率：采用 150^3 体素网格，消除锯齿。
# 2. 有机拓扑：Voronoi 晶格生成，轻量化且高强度。
# 3. 极速平滑：Taubin 滤波 + 二次衰减简化，确保工业级表面质感。
# ==============================================================================

def generate_voronoi_sleeve_v3(
    inner_radius=26.0,   # 内部中空半径 (STM32 + 电池空间，略微加大)
    outer_radius=32.5,   # 外部边界半径 (对应火箭 75mm 外壳内径)
    height=100.0,        # 保护套总高度
    num_points=250,      # 晶格密度
    thickness=2.0,       # 骨架厚度
    output_file="AI_Avionics_Sleeve_V3.stl"
):
    print(f"🚀 [Generative V3] 正在由 AI 生长高精细度航电防护套...")
    start_time = time.time()

    # --- 1. 高维体素空间建立 ---
    voxel_res = 150 # 150^3 = 337.5 万个体素，确保精度
    print(f"--> [1/3] 建立高维体素空间 (Res: {voxel_res}^3)...")
    
    x = np.linspace(-outer_radius-2, outer_radius+2, voxel_res)
    y = np.linspace(-outer_radius-2, outer_radius+2, voxel_res)
    z = np.linspace(-height/2-2, height/2+2, voxel_res)
    X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
    
    # 基础掩模：圆筒体
    R = np.sqrt(X**2 + Y**2)
    base_mask = (R >= inner_radius) & (R <= outer_radius) & (Z >= -height/2) & (Z <= height/2)
    
    # --- 2. Voronoi 有机挖空计算 ---
    print(f"--> [2/3] 计算 Voronoi 有机晶格 (种子数={num_points})...")
    # 在圆环壁内部随机撒种
    seed_points = []
    while len(seed_points) < num_points:
        pt = np.array([
            np.random.uniform(-outer_radius, outer_radius),
            np.random.uniform(-outer_radius, outer_radius),
            np.random.uniform(-height/2, height/2)
        ])
        r_pt = np.sqrt(pt[0]**2 + pt[1]**2)
        if inner_radius <= r_pt <= outer_radius:
            seed_points.append(pt)
    seed_points = np.array(seed_points)
    
    # 使用 KDTree 寻找最近的两个种子点
    tree = cKDTree(seed_points)
    grid_points = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T
    distances, _ = tree.query(grid_points, k=2)
    dist_diff = (distances[:, 1] - distances[:, 0]).reshape(X.shape)
    
    # 骨架逻辑：种子势力交界处保留 + 极薄的内外保护层（防止完全散架）
    skin = 0.8
    inner_skin = (R >= inner_radius) & (R <= inner_radius + skin)
    outer_skin = (R >= outer_radius - skin) & (R <= outer_radius)
    top_bottom_cap = (np.abs(Z) >= height/2 - skin) & (R >= inner_radius) & (R <= outer_radius)
    
    skeleton = (dist_diff < thickness)
    final_mask = base_mask & (skeleton | inner_skin | outer_skin | top_bottom_cap)
    
    # --- 3. 网格析出与工业级平滑 ---
    print(f"--> [3/3] 体素硬化与表面精修...")
    verts, faces, _, _ = marching_cubes(final_mask, level=0.5, spacing=(
        x[1]-x[0], y[1]-y[0], z[1]-z[0]
    ))
    
    # 坐标校正
    verts += np.array([x[0], y[0], z[0]])
    
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    
    # 工业平滑算法
    print("    正在执行 Taubin 非收缩平滑...")
    trimesh.smoothing.filter_taubin(mesh, iterations=20)
    
    # 自动减面 (由于缺少 fast_simplification 库，暂时跳过)
    # print("    正在优化网格拓扑...")
    # mesh = mesh.simplify_quadric_decimation(100000) 
    
    # 导出
    mesh.export(output_file)
    
    # 同时导出 GLB 预览
    preview_file = output_file.replace(".stl", ".glb")
    mesh.export(preview_file)
    
    end_time = time.time()
    print(f"🎉 成功！高精细度防护套已产出 -> [{output_file}] (耗时: {end_time - start_time:.2f}s)")

if __name__ == "__main__":
    out_dir = r"D:\AI_rocket\cad_automation"
    file_path = os.path.join(out_dir, "AI_Avionics_Sleeve_V3.stl")
    generate_voronoi_sleeve_v3(output_file=file_path)
