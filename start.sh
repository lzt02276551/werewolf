#!/bin/bash

# 设置端口为7860（魔搭创空间要求）
export PORT=7860
export HOST=0.0.0.0

# 打印启动信息
echo "=========================================="
echo "狼人杀AI系统启动中（轻量级版本）..."
echo "端口: $PORT"
echo "主机: $HOST"
echo "Golden Path: $ENABLE_GOLDEN_PATH"
echo "ML训练: $ML_AUTO_TRAIN"
echo "=========================================="

# 启动应用
cd /app
python werewolf/app.py
