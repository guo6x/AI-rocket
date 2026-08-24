import trimesh
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import art3d
import numpy as np
import os

def render_stl(stl_path, output_png, title):
    if not os.path.exists(stl_path):
        print(f"File not found: {stl_path}")
        return

    print(f"Rendering {stl_path}...")
    # 加载 STL
    mesh = trimesh.load(stl_path)
    
    # 创建 matplotlib 3D 图形
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 提取三角面片
    # 为了防止面片过多导致渲染卡死，如果面片超过 20000 个则进行简化预览
    if len(mesh.faces) > 20000:
        print("Simplifying mesh for preview...")
        mesh = mesh.simplify_quadratic_decimation(10000)

    # 创建集合
    collection = art3d.Poly3DCollection(mesh.vertices[mesh.faces], alpha=0.8)
    # 设置颜色
    collection.set_facecolor('#A0A0A0')
    collection.set_edgecolor('#303030')
    collection.set_linewidth(0.1)
    
    ax.add_collection3d(collection)
    
    # 自动缩放
    scale = mesh.vertices.flatten()
    ax.auto_scale_xyz(scale, scale, scale)
    
    # 设置视角
    ax.view_init(elev=30, azim=45)
    
    # 隐藏坐标轴
    ax.set_axis_off()
    plt.title(title, fontsize=15)
    
    # 保存
    plt.savefig(output_png, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_png}")

if __name__ == "__main__":
    # 渲染 TVC 装配体
    render_stl(
        r"D:\AI_rocket\pro_outputs\tvc_assembly_v2.stl",
        r"D:\AI_rocket\pro_outputs\tvc_render.png",
        "EDF TVC Assembly (High-Fidelity)"
    )
    
    # 渲染航电套
    render_stl(
        r"D:\AI_rocket\cad_automation\AI_Avionics_Sleeve.stl",
        r"D:\AI_rocket\cad_automation\sleeve_render.png",
        "Generative Avionics Sleeve (Voronoi)"
    )
