#!/bin/bash
# 快速部署脚本 - 魔搭平台

set -e  # 遇到错误立即退出

echo "=========================================="
echo "魔搭平台快速部署脚本"
echo "=========================================="
echo ""

# 1. 运行部署检查
echo "步骤 1/4: 运行部署就绪检查..."
python check_deploy_readiness.py
if [ $? -ne 0 ]; then
    echo ""
    echo "✗ 部署检查未通过,请修复问题后重试"
    exit 1
fi
echo ""

# 2. 检查Git状态
echo "步骤 2/4: 检查Git状态..."
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "✗ 当前目录不是Git仓库"
    echo "请先初始化Git仓库: git init"
    exit 1
fi

# 检查是否有未提交的更改
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠ 检测到未提交的更改"
    git status --short
    echo ""
    read -p "是否继续提交这些更改? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✗ 部署已取消"
        exit 1
    fi
else
    echo "✓ 没有未提交的更改"
fi
echo ""

# 3. 提交代码
echo "步骤 3/4: 提交代码到Git..."
git add .
git commit -m "准备部署到魔搭平台 - $(date '+%Y-%m-%d %H:%M:%S')" || echo "没有新的更改需要提交"
echo ""

# 4. 推送到远程仓库
echo "步骤 4/4: 推送到远程仓库..."
read -p "请输入远程仓库名称 (默认: origin): " remote_name
remote_name=${remote_name:-origin}

read -p "请输入分支名称 (默认: main): " branch_name
branch_name=${branch_name:-main}

echo "推送到 $remote_name/$branch_name..."
git push $remote_name $branch_name

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ 代码已成功推送到远程仓库!"
    echo "=========================================="
    echo ""
    echo "下一步:"
    echo "  1. 登录魔搭平台: https://modelscope.cn/"
    echo "  2. 进入你的创空间"
    echo "  3. 配置环境变量:"
    echo "     - MODEL_NAME=deepseek-chat"
    echo "     - OPENAI_API_KEY=你的API密钥"
    echo "     - OPENAI_BASE_URL=https://api.deepseek.com/v1"
    echo "  4. 点击'重新构建'"
    echo "  5. 等待构建完成(约3-5分钟)"
    echo ""
    echo "详细说明请查看: 魔搭部署指南.md"
    echo "=========================================="
else
    echo ""
    echo "✗ 推送失败,请检查:"
    echo "  1. 远程仓库是否存在"
    echo "  2. 是否有推送权限"
    echo "  3. 网络连接是否正常"
    exit 1
fi
