# 使用官方Python镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（最小化）
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制轻量级依赖文件
COPY requirements-lite.txt .

# 安装Python依赖（轻量级版本，不含torch/transformers）
RUN pip install --no-cache-dir -r requirements-lite.txt

# 仅复制运行必需的文件
COPY werewolf/ ./werewolf/
COPY config.py utils.py ./
COPY start.sh .

# 创建必要的目录
RUN mkdir -p ml_models game_data

# 暴露端口7860（魔搭创空间要求）
EXPOSE 7860

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENABLE_GOLDEN_PATH=false \
    ML_AUTO_TRAIN=true \
    ML_TRAIN_INTERVAL=10 \
    ML_MIN_SAMPLES=50

# 设置启动脚本权限
RUN chmod +x start.sh

# 启动应用
CMD ["./start.sh"]
