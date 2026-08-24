@echo off
chcp 65001 >nul
title ========================================
title  🚀 Ad Astra 3D 模型预览服务器
title ========================================
echo.
echo ========================================
echo   🚀 Ad Astra 3D 模型预览服务器
echo ========================================
echo.
echo [信息] 正在启动本地 HTTP 服务器...
echo [信息] 端口: 8000
echo [信息] 目录: %~dp0
echo.

cd /d "%~dp0"

rem 尝试使用 Python 启动服务器
where python >nul 2>nul
if %errorlevel%==0 (
    echo [成功] 检测到 Python，正在启动服务器...
    echo [提示] 服务器启动后，请在浏览器打开: http://localhost:8000/3d_preview.html
    echo [提示] 按 Ctrl+C 停止服务器
    echo.
    python -m http.server 8000
    goto :eof
)

where python3 >nul 2>nul
if %errorlevel%==0 (
    echo [成功] 检测到 Python3，正在启动服务器...
    echo [提示] 服务器启动后，请在浏览器打开: http://localhost:8000/3d_preview.html
    echo [提示] 按 Ctrl+C 停止服务器
    echo.
    python3 -m http.server 8000
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    echo [成功] 检测到 Python (py)，正在启动服务器...
    echo [提示] 服务器启动后，请在浏览器打开: http://localhost:8000/3d_preview.html
    echo [提示] 按 Ctrl+C 停止服务器
    echo.
    py -m http.server 8000
    goto :eof
)

echo [错误] 未检测到 Python！
echo.
echo 请安装 Python: https://www.python.org/downloads/
echo 或使用 VS Code 的 Live Server 扩展
echo.
pause
