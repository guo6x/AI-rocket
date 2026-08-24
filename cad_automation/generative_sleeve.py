import numpy as np
import trimesh
from scipy.spatial import Voronoi
import time
import os

def generate_voronoi_sleeve(
    inner_radius=25.0,   # 内部中空半径 (容纳 STM32 飞控的圆柱空间)
    outer_radius=32.0,   # 外部边界半径 (对应火箭外壳内径)
    height=80.0,         # 保护套总高度
    num_points=150,      # Voronoi 细胞（打孔）的数量。越多网格越密
    thickness=2.5,       # 遗留的骨架厚度
    output_file="avionics_lattice_sleeve.stl"
):
    print(f"🚀 [Generative AI] 开始生长飞控舱异星骨骼保护套...")
    print(f"参数: 内径={inner_radius}mm, 外径={outer_radius}mm, 高度={height}mm, 晶格数={num_points}")
    start_time = time.time()

    # 1. 构建包络基础体 (即我们允许材料生长的完整空间: 一个带孔的厚壁圆筒)
    # 创建外层圆柱
    outer_cyl = trimesh.creation.cylinder(radius=outer_radius, height=height)
    # 创建内侧挖空体 (稍高一点保证布尔穿透)
    inner_cyl = trimesh.creation.cylinder(radius=inner_radius, height=height + 10)
    
    # 基础几何：外圆柱 减去 内圆柱 形成的中空管
    # 这里用 trimesh 自带的 boolean 模块。需要注意，布尔运算很容易因为浮点精度崩溃。
    # 为了演示生成式思想，我们这里采用“空间点位逻辑过滤”或者“体素网格化”来替代脆弱的布尔差集。
    # 
    # 更稳健的生成式做法是：使用 Voxel (体素) 进行雕刻！
    
    # 我们采用三维体素网格空间，就像《我的世界》方块一样。
    voxel_resolution = 60 # 分辨率越高越精细但也越慢
    print(f"--> [1/3] 正在建立高维体素空间矩阵 (Res: {voxel_resolution}^3)...")
    
    x = np.linspace(-outer_radius, outer_radius, voxel_resolution)
    y = np.linspace(-outer_radius, outer_radius, voxel_resolution)
    z = np.linspace(-height/2, height/2, voxel_resolution)
    X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
    
    # 将整个宇宙清空为 0 (False)
    voxels = np.zeros((voxel_resolution, voxel_resolution, voxel_resolution), dtype=bool)
    
    # 定义基础管状蒙皮：到 Z 轴的距离 r 在 inner_radius 和 outer_radius 之间
    R = np.sqrt(X**2 + Y**2)
    base_mask = (R >= inner_radius) & (R <= outer_radius) & (Z >= -height/2) & (Z <= height/2)
    
    print(f"--> [2/3] 计算 Voronoi 场进行有机挖空 (细胞数={num_points})...")
    # 生成随机种子点 (这些点将成为被挖空的中心空洞，仿佛气泡)
    # 气泡只产生在圆环壁的内部空间
    seed_points = []
    while len(seed_points) < num_points:
        pt = np.array([
            np.random.uniform(-outer_radius, outer_radius),
            np.random.uniform(-outer_radius, outer_radius),
            np.random.uniform(-height/2, height/2)
        ])
        r_pt = np.sqrt(pt[0]**2 + pt[1]**2)
        if inner_radius + thickness/2 <= r_pt <= outer_radius - thickness/2:
            seed_points.append(pt)
    seed_points = np.array(seed_points)
    
    # 对空间中的每一个体素，找到它最近的种子点
    # 使用 KDTree 极速搜索
    from scipy.spatial import cKDTree
    tree = cKDTree(seed_points)
    
    # 将网格坐标展平供 KDTree 吞噬
    grid_points = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T
    
    # 找出每个网格点距离最近的两个种子点，如果距离差小于 thickness 的一半，说明这条缝是“骨干细胞壁”
    distances, _ = tree.query(grid_points, k=2)
    dist_diff = distances[:, 1] - distances[:, 0]
    
    # 骨架逻辑：位于两个细胞势力交界处的体素（厚度边界）将被保留，同时为了让圆筒不散架，保留内外蒙皮最薄的一层
    skin_thickness = 1.0
    inner_skin = (R >= inner_radius) & (R <= inner_radius + skin_thickness)
    outer_skin = (R >= outer_radius - skin_thickness) & (R <= outer_radius)
    
    # 核心公式：你是骨架（邻居势力差很小）或者 你是内外侧蒙皮，并且你在合法包裹圈内
    skeleton_mask = (dist_diff < thickness).reshape(X.shape)
    final_shape = base_mask & (skeleton_mask | inner_skin | outer_skin)
    
    print(f"--> [3/3] 体素硬化：使用 Marching Cubes 算法析出物理三维网格模型...")
    from skimage.measure import marching_cubes
    # 进行网格表面提取
    verts, faces, normals, values = marching_cubes(final_shape, level=0.5, spacing=(
        x[1]-x[0], y[1]-y[0], z[1]-z[0]
    ))
    
    # 平移顶点回真实坐标系中心
    verts -= np.array([outer_radius, outer_radius, height/2])
    
    # 将面片缝合成 Trimesh 实体
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    
    # 平滑化网格去掉乐高方块感（这会耗费一些时间）
    trimesh.smoothing.filter_taubin(mesh, iterations=10)
    
    # 导出模型
    mesh.export(output_file)
    
    end_time = time.time()
    print(f"🎉 成功！异星骨骼防护套已产出 -> [{output_file}] (用时: {end_time - start_time:.2f}s)")
    print(f"实体信息: 面片数={len(mesh.faces)}, 体体积=大概很轻。可以直接丢进 3D 打印机切片！")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(out_dir, "AI_Avionics_Sleeve.stl")
    generate_voronoi_sleeve(output_file=file_path)
