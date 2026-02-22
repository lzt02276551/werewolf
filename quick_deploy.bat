@echo off
REM 快速部署脚本 - 魔搭平台 (Windows版本)
setlocal enabledelayedexpansion

echo ==========================================
echo 魔搭平台快速部署脚本
echo ==========================================
echo.

REM 1. 运行部署检查
echo 步骤 1/4: 运行部署就绪检查...
python check_deploy_readiness.py
if errorlevel 1 (
    echo.
    echo X 部署检查未通过,请修复问题后重试
    pause
    exit /b 1
)
echo.

REM 2. 检查Git状态
echo 步骤 2/4: 检查Git状态...
git rev-parse --git-dir >nul 2>&1
if errorlevel 1 (
    echo X 当前目录不是Git仓库
    echo 请先初始化Git仓库: git init
    pause
    exit /b 1
)

REM 检查是否有未提交的更改
git diff-index --quiet HEAD -- 2>nul
if errorlevel 1 (
    echo 警告: 检测到未提交的更改
    git status --short
    echo.
    set /p continue="是否继续提交这些更改? (y/n): "
    if /i not "!continue!"=="y" (
        echo X 部署已取消
        pause
        exit /b 1
    )
) else (
    echo √ 没有未提交的更改
)
echo.

REM 3. 提交代码
echo 步骤 3/4: 提交代码到Git...
git add .
git commit -m "准备部署到魔搭平台 - %date% %time%" 2>nul
if errorlevel 1 (
    echo 没有新的更改需要提交
)
echo.

REM 4. 推送到远程仓库
echo 步骤 4/4: 推送到远程仓库...
set /p remote_name="请输入远程仓库名称 (默认: origin): "
if "!remote_name!"=="" set remote_name=origin

set /p branch_name="请输入分支名称 (默认: main): "
if "!branch_name!"=="" set branch_name=main

echo 推送到 !remote_name!/!branch_name!...
git push !remote_name! !branch_name!

if errorlevel 1 (
    echo.
    echo X 推送失败,请检查:
    echo   1. 远程仓库是否存在
    echo   2. 是否有推送权限
    echo   3. 网络连接是否正常
    pause
    exit /b 1
)

echo.
echo ==========================================
echo √ 代码已成功推送到远程仓库!
echo ==========================================
echo.
echo 下一步:
echo   1. 登录魔搭平台: https://modelscope.cn/
echo   2. 进入你的创空间
echo   3. 配置环境变量:
echo      - MODEL_NAME=deepseek-chat
echo      - OPENAI_API_KEY=你的API密钥
echo      - OPENAI_BASE_URL=https://api.deepseek.com/v1
echo   4. 点击'重新构建'
echo   5. 等待构建完成(约3-5分钟)
echo.
echo 详细说明请查看: 魔搭部署指南.md
echo ==========================================
echo.
pause
