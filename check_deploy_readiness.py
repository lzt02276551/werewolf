#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
魔搭平台部署就绪检查脚本
在部署前运行此脚本,确保所有配置正确
"""

import os
import sys
from pathlib import Path
import json


def check_file_exists(filepath: str, required: bool = True) -> bool:
    """检查文件是否存在"""
    exists = Path(filepath).exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    print(f"  {status} {filepath}: {'存在' if exists else '缺失'}")
    return exists or not required


def check_directory_exists(dirpath: str) -> bool:
    """检查目录是否存在"""
    exists = Path(dirpath).is_dir()
    status = "✓" if exists else "✗"
    print(f"  {status} {dirpath}/: {'存在' if exists else '缺失'}")
    return exists


def check_json_valid(filepath: str) -> bool:
    """检查JSON文件是否有效"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"  ✓ {filepath}: JSON格式有效")
        return True
    except json.JSONDecodeError as e:
        print(f"  ✗ {filepath}: JSON格式错误 - {e}")
        return False
    except FileNotFoundError:
        print(f"  ✗ {filepath}: 文件不存在")
        return False


def check_api_keys_not_exposed(filepath: str) -> bool:
    """检查是否暴露了真实的API密钥"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否包含真实的API密钥模式
        if 'sk-' in content and 'YOUR_API_KEY_HERE' not in content:
            # 进一步检查是否是真实密钥（长度检查）
            import re
            keys = re.findall(r'sk-[a-zA-Z0-9]{30,}', content)
            if keys:
                print(f"  ⚠ {filepath}: 可能包含真实API密钥,请检查!")
                return False
        
        print(f"  ✓ {filepath}: 未暴露真实API密钥")
        return True
    except FileNotFoundError:
        return True


def check_dockerfile() -> bool:
    """检查Dockerfile配置"""
    print("\n检查 Dockerfile...")
    
    if not check_file_exists("Dockerfile"):
        return False
    
    with open("Dockerfile", 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'EXPOSE 7860': '端口7860已暴露',
        'requirements-lite.txt': '使用轻量级依赖',
        'CMD ["./start.sh"]': '启动脚本已配置',
    }
    
    all_passed = True
    for pattern, desc in checks.items():
        if pattern in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc} - 未找到: {pattern}")
            all_passed = False
    
    return all_passed


def check_start_script() -> bool:
    """检查启动脚本"""
    print("\n检查 start.sh...")
    
    if not check_file_exists("start.sh"):
        return False
    
    with open("start.sh", 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'PORT=7860': '端口配置正确',
        'MODEL_NAME': '检查MODEL_NAME环境变量',
        'OPENAI_API_KEY': '检查API密钥环境变量',
        'python werewolf/app.py': '启动命令正确',
    }
    
    all_passed = True
    for pattern, desc in checks.items():
        if pattern in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ⚠ {desc} - 未找到: {pattern}")
            all_passed = False
    
    return all_passed


def check_requirements() -> bool:
    """检查依赖文件"""
    print("\n检查依赖文件...")
    
    has_lite = check_file_exists("requirements-lite.txt")
    has_full = check_file_exists("requirements-full.txt", required=False)
    
    if has_lite:
        with open("requirements-lite.txt", 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_packages = [
            'fastapi',
            'uvicorn',
            'openai',
            'werewolf-agent-build-sdk',
            'scikit-learn',
            'numpy'
        ]
        
        all_found = True
        for package in required_packages:
            if package in content:
                print(f"  ✓ {package}")
            else:
                print(f"  ✗ {package} - 缺失")
                all_found = False
        
        return all_found
    
    return False


def check_werewolf_module() -> bool:
    """检查werewolf模块结构"""
    print("\n检查 werewolf 模块...")
    
    required_dirs = [
        'werewolf',
        'werewolf/core',
        'werewolf/common',
        'werewolf/seer',
        'werewolf/villager',
        'werewolf/witch',
        'werewolf/wolf',
        'werewolf/guard',
        'werewolf/hunter',
        'werewolf/wolf_king',
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if not check_directory_exists(dir_path):
            all_exist = False
    
    # 检查关键文件
    required_files = [
        'werewolf/app.py',
        'werewolf/__init__.py',
        'werewolf/core/__init__.py',
    ]
    
    for file_path in required_files:
        if not check_file_exists(file_path):
            all_exist = False
    
    return all_exist


def check_golden_path_integration() -> bool:
    """检查golden_path_integration模块"""
    print("\n检查 golden_path_integration 模块...")
    
    if check_file_exists("golden_path_integration.py"):
        try:
            # 尝试导入
            sys.path.insert(0, str(Path.cwd()))
            import golden_path_integration
            print("  ✓ 模块可以成功导入")
            return True
        except ImportError as e:
            print(f"  ✗ 模块导入失败: {e}")
            return False
    
    return False


def main():
    """主函数"""
    print("=" * 70)
    print("魔搭平台部署就绪检查")
    print("=" * 70)
    
    checks = [
        ("部署配置文件", lambda: check_json_valid("ms_deploy.json")),
        ("API密钥安全", lambda: check_api_keys_not_exposed("ms_deploy.json")),
        ("Dockerfile", check_dockerfile),
        ("启动脚本", check_start_script),
        ("依赖文件", check_requirements),
        ("werewolf模块", check_werewolf_module),
        ("golden_path_integration", check_golden_path_integration),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 检查失败: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 70)
    print("检查总结")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    print("=" * 70)
    print(f"总计: {passed}/{total} 项检查通过")
    print("=" * 70)
    
    if passed == total:
        print("\n✓ 所有检查通过! 项目已准备好部署到魔搭平台。")
        print("\n下一步:")
        print("  1. 在魔搭平台的环境变量中设置你的API密钥")
        print("  2. 提交代码: git add . && git commit -m 'Ready for deploy'")
        print("  3. 推送到仓库: git push")
        print("  4. 在魔搭平台重新构建")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 项检查未通过,请修复后再部署。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
