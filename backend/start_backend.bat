@echo off
chcp 65001
echo 正在安装后端依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo 依赖安装完成，启动后端服务...
python main.py
pause