#!/bin/bash

# 设置端口为7860（魔搭创空间要求）
export PORT=7860
export HOST=0.0.0.0

# 打印启动信息
echo "=========================================="
echo "狼人杀AI系统启动中..."
echo "端口: $PORT"
echo "主机: $HOST"
echo "=========================================="

# 启动应用
cd /app

# 检查 AgentBuilder 是否支持 PORT 环境变量
# 如果不支持，可能需要修改 werewolf/app.py
python werewolf/app.py
