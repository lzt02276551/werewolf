# 使用官方Python镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制轻量级依赖文件
COPY requirements-lite.txt .

# 安装Python依赖（轻量级版本，不含torch/transformers）
# 使用国内镜像加速安装
RUN pip install --no-cache-dir -r requirements-lite.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p ml_models game_data

# 暴露端口7860（魔搭创空间要求）
EXPOSE 7860

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV ENABLE_GOLDEN_PATH=false

# 复制启动脚本并设置权限
COPY start.sh .
RUN chmod +x start.sh

# 启动应用
CMD ["./start.sh"]
