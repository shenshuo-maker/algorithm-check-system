@echo off
chcp 65001 >nul
echo 正在启动前端服务...
cd /d "%~dp0"
start http://localhost:5500/index.html
python -m http.server 5500
pause