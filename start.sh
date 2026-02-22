#!/bin/bash

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
echo ""
echo "检查环境变量..."
if [ -z "$MODEL_NAME" ]; then
    echo "✗ 错误: MODEL_NAME 环境变量未设置"
    echo ""
    echo "请在魔搭平台设置以下环境变量："
    echo "  MODEL_NAME=deepseek-chat"
    echo "  OPENAI_API_KEY=你的API密钥"
    echo "  OPENAI_BASE_URL=https://api.deepseek.com/v1"
    echo ""
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "✗ 错误: OPENAI_API_KEY 环境变量未设置"
    echo ""
    echo "请在魔搭平台设置环境变量："
    echo "  OPENAI_API_KEY=你的API密钥"
    echo ""
    exit 1
fi

echo "✓ MODEL_NAME: $MODEL_NAME"
echo "✓ OPENAI_BASE_URL: ${OPENAI_BASE_URL:-未设置}"
echo "✓ OPENAI_API_KEY: ${OPENAI_API_KEY:0:8}..."

# 检查必需的目录
echo ""
echo "检查目录结构..."
for dir in ml_models game_data logs; do
    if [ ! -d "$dir" ]; then
        echo "创建目录: $dir"
        mkdir -p "$dir"
    else
        echo "✓ $dir"
    fi
done

# 测试Python环境
echo ""
echo "测试Python环境..."
python -c "import sys; print(f'✓ Python路径: {sys.executable}')"
python -c "import werewolf; print('✓ werewolf模块可导入')" || {
    echo "✗ 错误: 无法导入werewolf模块"
    echo ""
    echo "可能的原因："
    echo "  1. PYTHONPATH未正确设置"
    echo "  2. werewolf目录不存在"
    echo "  3. 缺少依赖包"
    echo ""
    exit 1
}

# 启动应用
cd /app
echo ""
echo "=========================================="
echo "✓ 所有检查通过，启动应用..."
echo "=========================================="
echo ""
exec python werewolf/app.py
