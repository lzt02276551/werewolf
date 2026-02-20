#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署就绪检查脚本
验证所有必需文件和配置是否正确
"""

import os
import sys
from pathlib import Path

def check_file(path: str, required: bool = True) -> bool:
    """检查文件是否存在"""
    exists = Path(path).exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_str = "必需" if required else "可选"
    print(f"{status} {path:40s} [{req_str}]")
    return exists or not required

def check_directory(path: str, required: bool = True) -> bool:
    """检查目录是否存在"""
    exists = Path(path).is_dir()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_str = "必需" if required else "可选"
    print(f"{status} {path:40s} [{req_str}]")
    return exists or not required

def main():
    print("=" * 70)
    print("狼人杀AI系统 - 部署就绪检查")
    print("=" * 70)
    
    all_ok = True
    
    # 检查部署配置文件
    print("\n【部署配置文件】")
    all_ok &= check_file("Dockerfile", required=True)
    all_ok &= check_file("requirements-lite.txt", required=True)
    all_ok &= check_file("ms_deploy.json", required=True)
    all_ok &= check_file("start.sh", required=True)
    all_ok &= check_file(".dockerignore", required=True)
    
    # 检查核心代码文件
    print("\n【核心代码文件】")
    all_ok &= check_file("config.py", required=True)
    all_ok &= check_file("utils.py", required=True)
    all_ok &= check_file("werewolf/app.py", required=True)
    
    # 检查角色智能体
    print("\n【角色智能体】")
    roles = ["villager", "wolf", "seer", "witch", "guard", "hunter", "wolf_king"]
    for role in roles:
        all_ok &= check_directory(f"werewolf/{role}", required=True)
        all_ok &= check_file(f"werewolf/{role}/{role}_agent.py", required=True)
    
    # 检查核心模块
    print("\n【核心模块】")
    all_ok &= check_directory("werewolf/core", required=True)
    all_ok &= check_directory("werewolf/common", required=True)
    
    # 检查不应包含的文件（会增加镜像大小）
    print("\n【排除文件检查】")
    excluded = [
        "ml_golden_path/",
        "golden_path_integration.py",
        "test_*.py",
        "check_*.py",
        "generate_*.py"
    ]
    
    for pattern in excluded:
        if "*" in pattern:
            # 通配符匹配
            import glob
            files = glob.glob(pattern)
            if files:
                print(f"⚠ 发现应排除的文件: {', '.join(files)}")
        else:
            path = Path(pattern)
            if path.exists():
                print(f"⚠ 发现应排除的文件/目录: {pattern}")
    
    # 检查环境变量配置
    print("\n【环境变量配置】")
    import json
    try:
        with open("ms_deploy.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            env_vars = {item["name"]: item["value"] for item in config.get("environment_variables", [])}
            
            print(f"✓ ENABLE_GOLDEN_PATH: {env_vars.get('ENABLE_GOLDEN_PATH', 'N/A')}")
            print(f"✓ ML_AUTO_TRAIN: {env_vars.get('ML_AUTO_TRAIN', 'N/A')}")
            print(f"✓ ML_TRAIN_INTERVAL: {env_vars.get('ML_TRAIN_INTERVAL', 'N/A')}")
            print(f"✓ ML_MIN_SAMPLES: {env_vars.get('ML_MIN_SAMPLES', 'N/A')}")
            print(f"✓ 资源配置: {config.get('resource_configuration', 'N/A')}")
            
            # 验证关键配置
            if env_vars.get('ENABLE_GOLDEN_PATH') != 'false':
                print("⚠ 警告: ENABLE_GOLDEN_PATH应设为false以减少资源占用")
                all_ok = False
                
    except Exception as e:
        print(f"✗ 无法读取ms_deploy.json: {e}")
        all_ok = False
    
    # 检查依赖文件内容
    print("\n【依赖文件检查】")
    try:
        with open("requirements-lite.txt", "r", encoding="utf-8") as f:
            content = f.read()
            
            # 检查不应包含的重量级依赖（排除注释）
            heavy_deps = ["torch", "transformers", "tensorflow"]
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
            content_no_comments = ' '.join(lines)
            found_heavy = [dep for dep in heavy_deps if dep in content_no_comments.lower()]
            
            if found_heavy:
                print(f"✗ 发现重量级依赖: {', '.join(found_heavy)}")
                all_ok = False
            else:
                print("✓ 依赖文件正确（无重量级依赖）")
                
            # 检查必需依赖
            required_deps = ["fastapi", "openai", "werewolf-agent-build-sdk", "scikit-learn"]
            missing_deps = [dep for dep in required_deps if dep not in content.lower()]
            
            if missing_deps:
                print(f"✗ 缺少必需依赖: {', '.join(missing_deps)}")
                all_ok = False
            else:
                print("✓ 所有必需依赖已包含")
                
    except Exception as e:
        print(f"✗ 无法读取requirements-lite.txt: {e}")
        all_ok = False
    
    # 估算镜像大小
    print("\n【镜像大小估算】")
    total_size = 0
    for root, dirs, files in os.walk("werewolf"):
        # 排除__pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if file.endswith(".py"):
                total_size += os.path.getsize(os.path.join(root, file))
    
    print(f"✓ Python代码大小: {total_size / 1024:.1f} KB")
    print(f"✓ 预计镜像大小: ~150-200 MB（含依赖）")
    
    # 最终结果
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ 所有检查通过！系统已准备好部署到魔搭平台")
        print("\n下一步:")
        print("1. 确保设置了MODEL_NAME环境变量")
        print("2. 将代码推送到Git仓库")
        print("3. 在魔搭平台创建创空间并导入")
        print("4. 配置环境变量后点击部署")
    else:
        print("❌ 检查未通过，请修复上述问题后重试")
        return 1
    
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
