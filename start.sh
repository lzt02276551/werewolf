#!/bin/bash
set -e  # 遇到错误立即退出

# 设置端口为7860（魔搭创空间要求）
export PORT=7860
export HOST=0.0.0.0

# 打印启动信息
echo "=========================================="
echo "狼人杀AI系统启动中（轻量级版本）..."
echo "端口: $PORT"
echo "主机: $HOST"
echo "Golden Path: ${ENABLE_GOLDEN_PATH:-false}"
echo "ML训练: ${ML_AUTO_TRAIN:-true}"
echo "Python版本: $(python --version)"
echo "工作目录: $(pwd)"
echo "=========================================="

# 检查必需的环境变量
if [ -z "$MODEL_NAME" ]; then
    echo "警告: MODEL_NAME 环境变量未设置"
fi

# 检查必需的目录
for dir in ml_models game_data logs; do
    if [ ! -d "$dir" ]; then
        echo "创建目录: $dir"
        mkdir -p "$dir"
    fi
done

# 启动应用
cd /app
echo "启动应用..."
exec python werewolf/app.py
