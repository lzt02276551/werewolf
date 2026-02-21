#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署前验证脚本 - 快速检查项目是否准备好部署
"""

import os
import sys
from pathlib import Path

def check_files():
    """检查必需文件"""
    required = [
        "Dockerfile",
        "requirements-lite.txt",
        "ms_deploy.json",
        "start.sh",
        "werewolf/app.py",
        "config.py",
        "utils.py"
    ]
    
    missing = []
    for f in required:
        if not Path(f).exists():
            missing.append(f)
    
    return missing

def check_excluded():
    """检查不应存在的文件"""
    excluded = [
        "test_fixes.py",
        "check_deploy_ready.py",
        "requirements-dev.txt",
        "pytest.ini",
        "tests/",
        ".pytest_cache/",
        "htmlcov/"
    ]
    
    found = []
    for pattern in excluded:
        p = Path(pattern)
        if p.exists():
            found.append(pattern)
    
    return found

def main():
    print("=" * 60)
    print("魔搭平台部署验证")
    print("=" * 60)
    
    # 检查必需文件
    missing = check_files()
    if missing:
        print(f"\n❌ 缺少必需文件: {', '.join(missing)}")
        return 1
    else:
        print("\n✅ 所有必需文件存在")
    
    # 检查排除文件
    excluded = check_excluded()
    if excluded:
        print(f"\n⚠️  发现应排除的文件: {', '.join(excluded)}")
    else:
        print("✅ 无多余文件")
    
    # 统计代码大小
    total_size = 0
    py_count = 0
    errors = []
    
    for root, _, files in os.walk("werewolf"):
        for f in files:
            if f.endswith(".py"):
                try:
                    filepath = os.path.join(root, f)
                    total_size += os.path.getsize(filepath)
                    py_count += 1
                except (OSError, IOError) as e:
                    errors.append(f"Failed to read {filepath}: {e}")
    
    print(f"\n📊 代码统计:")
    print(f"  - Python文件: {py_count}")
    print(f"  - 代码大小: {total_size/1024:.1f} KB")
    
    if errors:
        print(f"\n⚠️  文件读取错误:")
        for error in errors:
            print(f"  - {error}")
    
    print("\n" + "=" * 60)
    if not missing:
        print("✅ 项目已准备好部署到魔搭平台")
        return 0
    else:
        print("❌ 请修复上述问题后重试")
        return 1

if __name__ == "__main__":
    sys.exit(main())
