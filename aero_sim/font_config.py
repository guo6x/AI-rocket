"""
Matplotlib 中文字体配置 — Windows 平台
导入此模块即可让 matplotlib 图表正确显示中文
"""
import matplotlib
import matplotlib.pyplot as plt
import platform

def setup_chinese_font():
    """配置 matplotlib 使用系统中文字体"""
    if platform.system() == 'Windows':
        # Windows 自带微软雅黑
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

# 导入时自动执行
setup_chinese_font()
