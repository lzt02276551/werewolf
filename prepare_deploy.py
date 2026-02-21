#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
魔搭平台部署准备脚本

清理不必要的文件，只保留部署必需的组件
"""

import os
import shutil
import sys
from pathlib import Path


def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent


def create_deploy_directory():
    """创建部署目录"""
    deploy_dir = get_project_root() / "deploy_package"
    
    if deploy_dir.exists():
        print(f"删除现有部署目录: {deploy_dir}")
        shutil.rmtree(deploy_dir)
    
    print(f"创建部署目录: {deploy_dir}")
    deploy_dir.mkdir()
    
    return deploy_dir


def copy_essential_files(deploy_dir):
    """复制必需的文件"""
    root = get_project_root()
    
    # 必需的文件列表
    essential_files = [
        'config.py',
        'utils.py',
        'requirements-lite.txt',
        'Dockerfile',
        'start.sh',
        'ms_deploy.json',
        'README.md',
        '.dockerignore',
        '.gitignore',
    ]
    
    print("\n复制必需文件:")
    for file in essential_files:
        src = root / file
        if src.exists():
            dst = deploy_dir / file
            shutil.copy2(src, dst)
            print(f"  ✓ {file}")
        else:
            print(f"  ⚠ {file} (不存在，跳过)")
    
    # 复制werewolf目录（排除不必要的文件）
    print("\n复制werewolf目录:")
    src_werewolf = root / "werewolf"
    dst_werewolf = deploy_dir / "werewolf"
    
    if src_werewolf.exists():
        shutil.copytree(
            src_werewolf,
            dst_werewolf,
            ignore=shutil.ignore_patterns(
                '__pycache__',
                '*.pyc',
                '*.pyo',
                '*.pyd',
                '.DS_Store',
                '*.so',
                '*.dylib',
                '.pytest_cache',
                '*.egg-info'
            )
        )
        print(f"  ✓ werewolf/ (已复制)")
    else:
        print(f"  ✗ werewolf/ (不存在)")
        return False
    
    # 创建必要的目录
    print("\n创建必要目录:")
    for dir_name in ['ml_models', 'game_data', 'logs']:
        dir_path = deploy_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"  ✓ {dir_name}/")
    
    return True


def create_deployment_readme(deploy_dir):
    """创建部署说明文件"""
    readme_content = """# 狼人杀AI系统 - 魔搭平台部署包

## 📦 包内容

此部署包包含运行狼人杀AI系统所需的所有文件。

### 核心文件
- `werewolf/` - 核心代码目录
- `config.py` - 全局配置
- `utils.py` - 工具函数
- `requirements-lite.txt` - 精简依赖
- `Dockerfile` - Docker配置
- `start.sh` - 启动脚本
- `ms_deploy.json` - 魔搭平台配置

### 数据目录
- `ml_models/` - ML模型保存目录
- `game_data/` - 游戏数据保存目录
- `logs/` - 日志目录

## 🚀 部署步骤

### 1. 上传到Git仓库
```bash
git init
git add .
git commit -m "Initial commit for ModelScope deployment"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2. 在魔搭平台部署
1. 访问 https://modelscope.cn/studios
2. 创建新的创空间
3. 选择"从Git导入"
4. 输入仓库地址
5. 配置环境变量:
   - `MODEL_NAME=qwen-plus` (必需)
   - `DETECTION_MODEL_NAME=qwen-plus` (可选)
6. 选择资源配置: `platform/2v-cpu-8g-mem`
7. 点击部署

### 3. 验证部署
访问应用URL，检查:
- [ ] 应用成功启动
- [ ] 健康检查通过 (访问 /health)
- [ ] 游戏功能正常

## 📝 环境变量

### 必需变量
- `MODEL_NAME` - 主模型名称（如: qwen-plus）

### 可选变量（已在ms_deploy.json中配置）
- `ENABLE_GOLDEN_PATH=false` - 禁用深度学习
- `ML_AUTO_TRAIN=true` - 启用ML训练
- `ML_TRAIN_INTERVAL=10` - 训练间隔
- `ML_MIN_SAMPLES=50` - 最小训练样本数
- `LOG_LEVEL=INFO` - 日志级别

## 🔧 资源需求

- CPU: 2核
- 内存: 8GB (推荐) / 4GB (最低)
- 磁盘: 2GB

## 📚 更多信息

详细部署指南请参考项目根目录的 `deploy_to_modelscope.md`

## ✅ 修复状态

此版本包含所有P0/P1修复（10个关键bug已修复）:
- ✅ ML预测错误处理
- ✅ 权重归一化修复
- ✅ 内存泄漏修复
- ✅ 类型验证增强
- ✅ 增量学习错误处理
- ✅ 投票准确度验证
- ✅ 决策引擎验证
- ✅ 游戏结束处理
- ✅ LLM检测器降级
- ✅ 信任分数历史

---

**版本**: 1.1.0-lite  
**更新日期**: 2026-02-21  
**状态**: ✅ 生产就绪
"""
    
    readme_path = deploy_dir / "DEPLOY_README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"\n创建部署说明: DEPLOY_README.md")


def calculate_size(path):
    """计算目录大小"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def print_summary(deploy_dir):
    """打印部署包摘要"""
    print("\n" + "="*60)
    print("部署包准备完成")
    print("="*60)
    
    # 计算大小
    total_size = calculate_size(deploy_dir)
    
    print(f"\n部署目录: {deploy_dir}")
    print(f"总大小: {format_size(total_size)}")
    
    # 统计文件数量
    file_count = sum(1 for _ in deploy_dir.rglob('*') if _.is_file())
    dir_count = sum(1 for _ in deploy_dir.rglob('*') if _.is_dir())
    
    print(f"文件数量: {file_count}")
    print(f"目录数量: {dir_count}")
    
    print("\n下一步:")
    print("1. 检查部署包内容:")
    print(f"   cd {deploy_dir}")
    print("   ls -la")
    print()
    print("2. 测试部署包:")
    print(f"   cd {deploy_dir}")
    print("   docker build -t werewolf-lite .")
    print("   docker run -p 7860:7860 -e MODEL_NAME=qwen-plus werewolf-lite")
    print()
    print("3. 上传到Git并部署到魔搭平台")
    print()
    print("详细部署指南: deploy_to_modelscope.md")
    print("="*60)


def main():
    """主函数"""
    print("="*60)
    print("魔搭平台部署准备脚本")
    print("="*60)
    
    try:
        # 创建部署目录
        deploy_dir = create_deploy_directory()
        
        # 复制必需文件
        if not copy_essential_files(deploy_dir):
            print("\n✗ 复制文件失败")
            return 1
        
        # 创建部署说明
        create_deployment_readme(deploy_dir)
        
        # 打印摘要
        print_summary(deploy_dir)
        
        print("\n✓ 部署包准备成功！")
        return 0
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
