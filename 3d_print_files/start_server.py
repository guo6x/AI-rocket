#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Ad Astra 3D 模型预览服务器
一键启动本地 HTTP 服务，让浏览器可以正确加载 STL 文件
"""
import http.server
import socketserver
import os
import sys
import webbrowser
from pathlib import Path

PORT = 8000

def main():
    # 获取脚本所在目录
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    print("\n" + "="*60)
    print("  🚀 Ad Astra 3D 模型预览服务器")
    print("="*60)
    print(f"\n[目录] {script_dir}")
    print(f"[端口] {PORT}")

    # 检查模型文件是否存在 (v11 文件名, 同步 rocket_config.py)
    models = [
        "00_full_rocket_assembly.stl",
        "01_nose_cone.stl",
        "02_body_tube.stl",
        "03_fins.stl",
        "04_avionics_bay.stl",
        "05_motor_nozzle.stl",
        "06_recovery_bay.stl",
        "07_bolts.stl",
        "viewer.html",
    ]

    print("\n[检查] 模型文件:")
    all_ok = True
    for model in models:
        exists = Path(model).exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {model}")
        if not exists:
            all_ok = False

    if not all_ok:
        print("\n[警告] 部分文件缺失，请先运行 generate_all_3d_models.py")
        sys.exit(1)

    print("\n" + "-"*60)
    print(f"  服务器启动成功！")
    print("-"*60)
    print(f"\n  👉 在浏览器中打开: http://localhost:{PORT}/viewer.html")
    print(f"  👉 或访问: http://127.0.0.1:{PORT}/viewer.html")
    print("\n  按 Ctrl+C 停止服务器\n")

    # 自动打开浏览器
    try:
        url = f"http://localhost:{PORT}/viewer.html"
        print(f"  正在自动打开浏览器...\n")
        webbrowser.open(url)
    except Exception:
        pass

    # 启动服务器
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n[停止] 服务器已停止")
            httpd.server_close()

if __name__ == "__main__":
    main()
