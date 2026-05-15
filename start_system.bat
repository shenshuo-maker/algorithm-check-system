@echo off
chcp 65001 >nul
echo ==============================================
echo    算法备案文本智能合规检测系统 - 一键启动
echo ==============================================
echo.

:: 1. 启动后端服务（新窗口）
echo [1/2] 正在启动后端服务...
start "后端服务" cmd /k "cd /d ""%~dp0backend"" && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && python main.py"

:: 等待3秒，给后端一点启动时间
timeout /t 3 /nobreak >nul

:: 2. 启动前端HTTP服务器（新窗口，与后端 8000 错开端口）
echo [2/2] 正在启动前端服务...
start "前端服务" cmd /k "cd /d ""%~dp0frontend"" && python -m http.server 5500"

:: 等待1秒，再打开浏览器
timeout /t 1 /nobreak >nul

:: 3. 自动打开前端页面
start http://localhost:5500/index.html

echo.
echo ==============================================
echo  系统启动中...
echo  后端地址: http://127.0.0.1:8000
echo  前端地址: http://localhost:5500/index.html
echo ==============================================
echo.
pause