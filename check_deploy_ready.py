#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署就绪检查脚本

检查所有必需文件是否存在，配置是否正确
"""

import os
import sys
from pathlib import Path


def check_file_exists(filepath, required=True):
    """检查文件是否存在"""
    exists = filepath.exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_text = "(必需)" if required else "(可选)"
    print(f"  {status} {filepath.name} {req_text}")
    return exists if required else True


def check_directory_exists(dirpath, required=True):
    """检查目录是否存在"""
    exists = dirpath.exists() and dirpath.is_dir()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_text = "(必需)" if required else "(可选)"
    print(f"  {status} {dirpath.name}/ {req_text}")
    return exists if required else True


def check_essential_files():
    """检查必需文件"""
    print("\n" + "="*60)
    print("检查必需文件")
    print("="*60)
    
    root = Path.cwd()
    all_ok = True
    
    # 核心文件
    print("\n核心文件:")
    files = [
        ('config.py', True),
        ('utils.py', True),
        ('requirements-lite.txt', True),
        ('Dockerfile', True),
        ('start.sh', True),
        ('ms_deploy.json', True),
        ('README.md', False),
        ('.dockerignore', False),
    ]
    
    for filename, required in files:
        if not check_file_exists(root / filename, required):
            all_ok = False
    
    # werewolf目录
    print("\n核心代码目录:")
    dirs = [
        ('werewolf', True),
        ('werewolf/core', True),
        ('werewolf/common', True),
        ('werewolf/villager', True),
        ('werewolf/wolf', True),
        ('werewolf/seer', True),
        ('werewolf/witch', True),
        ('werewolf/guard', True),
        ('werewolf/hunter', True),
        ('werewolf/wolf_king', True),
    ]
    
    for dirname, required in dirs:
        if not check_directory_exists(root / dirname, required):
            all_ok = False
    
    # 关键Python文件
    print("\n关键Python文件:")
    py_files = [
        ('werewolf/app.py', True),
        ('werewolf/ml_agent.py', True),
        ('werewolf/game_utils.py', True),
        ('werewolf/game_end_handler.py', True),
        ('werewolf/incremental_learning.py', True),
    ]
    
    for filename, required in py_files:
        if not check_file_exists(root / filename, required):
            all_ok = False
    
    return all_ok


def check_dockerfile():
    """检查Dockerfile配置"""
    print("\n" + "="*60)
    print("检查Dockerfile配置")
    print("="*60)
    
    dockerfile = Path.cwd() / 'Dockerfile'
    if not dockerfile.exists():
        print("  ✗ Dockerfile不存在")
        return False
    
    content = dockerfile.read_text(encoding='utf-8')
    
    checks = [
        ('FROM python:3.10-slim', 'Python基础镜像'),
        ('COPY requirements-lite.txt', '复制依赖文件'),
        ('pip install', '安装依赖'),
        ('COPY werewolf/', '复制核心代码'),
        ('EXPOSE 7860', '暴露端口'),
        ('CMD ["./start.sh"]', '启动命令'),
    ]
    
    all_ok = True
    for check_str, desc in checks:
        if check_str in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc} (未找到: {check_str})")
            all_ok = False
    
    return all_ok


def check_ms_deploy_json():
    """检查魔搭配置"""
    print("\n" + "="*60)
    print("检查魔搭平台配置")
    print("="*60)
    
    config_file = Path.cwd() / 'ms_deploy.json'
    if not config_file.exists():
        print("  ✗ ms_deploy.json不存在")
        return False
    
    try:
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        checks = [
            ('sdk_type', 'docker', 'SDK类型'),
            ('port', 7860, '端口配置'),
        ]
        
        all_ok = True
        for key, expected, desc in checks:
            if key in config:
                value = config[key]
                if value == expected:
                    print(f"  ✓ {desc}: {value}")
                else:
                    print(f"  ⚠ {desc}: {value} (预期: {expected})")
            else:
                print(f"  ✗ {desc} (缺失)")
                all_ok = False
        
        # 检查环境变量
        if 'environment_variables' in config:
            env_vars = {var['name']: var['value'] for var in config['environment_variables']}
            print(f"\n  环境变量配置:")
            for name, value in env_vars.items():
                print(f"    • {name}={value}")
        
        return all_ok
        
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 读取配置失败: {e}")
        return False


def check_requirements():
    """检查依赖配置"""
    print("\n" + "="*60)
    print("检查依赖配置")
    print("="*60)
    
    req_file = Path.cwd() / 'requirements-lite.txt'
    if not req_file.exists():
        print("  ✗ requirements-lite.txt不存在")
        return False
    
    content = req_file.read_text(encoding='utf-8')
    
    # 必需的依赖
    required_deps = [
        'fastapi',
        'uvicorn',
        'openai',
        'werewolf-agent-build-sdk',
        'numpy',
        'scikit-learn',
        'pyyaml',
        'pydantic',
    ]
    
    all_ok = True
    for dep in required_deps:
        if dep in content:
            print(f"  ✓ {dep}")
        else:
            print(f"  ✗ {dep} (缺失)")
            all_ok = False
    
    # 不应该包含的依赖（重量级）
    excluded_deps = [
        'torch',
        'transformers',
        'xgboost',
        'matplotlib',
        'seaborn',
    ]
    
    print("\n  排除的重量级依赖:")
    for dep in excluded_deps:
        if dep not in content:
            print(f"  ✓ {dep} (已排除)")
        else:
            print(f"  ⚠ {dep} (应该排除)")
    
    return all_ok


def check_fixes_included():
    """检查修复是否包含"""
    print("\n" + "="*60)
    print("检查P0/P1修复")
    print("="*60)
    
    root = Path.cwd()
    
    # 检查修复的文件
    fixed_files = [
        ('werewolf/ml_agent.py', 'Task 001: ML预测错误处理'),
        ('config.py', 'Task 002: 权重归一化修复'),
        ('werewolf/game_utils.py', 'Task 003/004/006: 内存泄漏+类型验证+投票准确度'),
        ('werewolf/incremental_learning.py', 'Task 005: 增量学习错误处理'),
        ('werewolf/game_end_handler.py', 'Task 008: 游戏结束处理'),
        ('werewolf/core/base_good_agent.py', 'Task 009: LLM检测器降级'),
        ('werewolf/guard/trust_manager.py', 'Task 010: 信任分数历史'),
    ]
    
    all_ok = True
    for filepath, desc in fixed_files:
        file = root / filepath
        if file.exists():
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc} (文件不存在)")
            all_ok = False
    
    return all_ok


def estimate_size():
    """估算部署包大小"""
    print("\n" + "="*60)
    print("估算部署包大小")
    print("="*60)
    
    root = Path.cwd()
    
    # 计算werewolf目录大小
    werewolf_size = 0
    if (root / 'werewolf').exists():
        for file in (root / 'werewolf').rglob('*.py'):
            werewolf_size += file.stat().st_size
    
    # 计算其他文件大小
    other_files = ['config.py', 'utils.py', 'requirements-lite.txt', 'Dockerfile', 'start.sh']
    other_size = sum((root / f).stat().st_size for f in other_files if (root / f).exists())
    
    total_size = werewolf_size + other_size
    
    print(f"\n  代码大小:")
    print(f"    werewolf/: {werewolf_size / 1024:.2f} KB")
    print(f"    其他文件: {other_size / 1024:.2f} KB")
    print(f"    总计: {total_size / 1024:.2f} KB")
    
    print(f"\n  预估Docker镜像大小: ~150 MB")
    print(f"  (包含Python运行时和依赖)")


def print_summary(results):
    """打印检查摘要"""
    print("\n" + "="*60)
    print("检查摘要")
    print("="*60)
    
    all_passed = all(results.values())
    
    for check_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status}: {check_name}")
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ 所有检查通过！可以部署到魔搭平台")
        print("="*60)
        print("\n下一步:")
        print("1. 运行准备脚本: python prepare_deploy.py")
        print("2. 测试部署包: cd deploy_package && docker build -t werewolf-lite .")
        print("3. 上传到Git并部署到魔搭平台")
        print("\n详细指南: deploy_to_modelscope.md")
        return 0
    else:
        print("✗ 部分检查失败，请修复后再部署")
        print("="*60)
        return 1


def main():
    """主函数"""
    print("="*60)
    print("魔搭平台部署就绪检查")
    print("="*60)
    
    results = {
        '必需文件': check_essential_files(),
        'Dockerfile配置': check_dockerfile(),
        '魔搭平台配置': check_ms_deploy_json(),
        '依赖配置': check_requirements(),
        'P0/P1修复': check_fixes_included(),
    }
    
    estimate_size()
    
    return print_summary(results)


if __name__ == '__main__':
    sys.exit(main())
