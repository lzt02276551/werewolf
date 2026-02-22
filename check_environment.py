# -*- coding: utf-8 -*-
"""
环境兼容性检查脚本

检查当前环境是否与12人狼人杀模板兼容
"""

import sys
import subprocess

def check_python_version():
    """检查Python版本"""
    print("=" * 60)
    print("检查Python版本")
    print("=" * 60)
    
    version = sys.version_info
    print(f"当前版本: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 8:
        print("✓ Python版本兼容（需要Python 3.8+）")
        return True
    else:
        print("✗ Python版本不兼容（需要Python 3.8+）")
        return False


def check_package_version(package_name, required_version=None):
    """检查包版本"""
    try:
        if package_name == "sklearn":
            import sklearn
            current_version = sklearn.__version__
        elif package_name == "numpy":
            import numpy
            current_version = numpy.__version__
        elif package_name == "fastapi":
            import fastapi
            current_version = fastapi.__version__
        elif package_name == "openai":
            import openai
            current_version = openai.__version__
        elif package_name == "pyyaml":
            import yaml
            current_version = yaml.__version__
        elif package_name == "pydantic":
            import pydantic
            current_version = pydantic.__version__
        else:
            return None, "未知包"
        
        return current_version, None
    except ImportError as e:
        return None, f"未安装: {e}"


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("狼人杀AI系统 - 环境兼容性检查")
    print("=" * 60 + "\n")
    
    # 检查Python版本
    python_ok = check_python_version()
    print()
    
    # 检查关键包
    print("=" * 60)
    print("检查关键依赖包")
    print("=" * 60)
    
    packages = {
        "numpy": "1.24.0-2.0.0",
        "sklearn": "1.3.2",
        "fastapi": "0.100.0+",
        "openai": "1.0.0+",
        "pyyaml": "6.0+",
        "pydantic": "2.0.0+"
    }
    
    all_ok = True
    
    for package, required in packages.items():
        current, error = check_package_version(package)
        
        if error:
            print(f"✗ {package}: {error}")
            all_ok = False
        else:
            print(f"✓ {package}: {current} (要求: {required})")
            
            # 特殊检查
            if package == "sklearn":
                major, minor, patch = current.split('.')
                if int(major) == 1 and int(minor) == 4:
                    print(f"  ⚠️  警告: 你的sklearn版本是{current}，12人模板要求1.3.2")
                    print(f"      建议: pip install scikit-learn==1.3.2")
                    print(f"      影响: 可能导致ML模型不兼容")
            
            elif package == "numpy":
                major, minor = current.split('.')[:2]
                if int(major) == 1 and int(minor) >= 26:
                    print(f"  ℹ️  信息: numpy {current}与12人模板兼容")
    
    print()
    
    # 检查werewolf-agent-build-sdk
    print("=" * 60)
    print("检查werewolf-agent-build-sdk")
    print("=" * 60)
    
    try:
        import agent_build_sdk
        print(f"✓ werewolf-agent-build-sdk: 已安装")
        
        # 检查版本
        try:
            version = agent_build_sdk.__version__
            print(f"  版本: {version}")
            if version != "0.0.10":
                print(f"  ⚠️  警告: 12人模板要求版本0.0.10")
        except AttributeError:
            print(f"  ℹ️  无法获取版本信息")
    except ImportError:
        print(f"✗ werewolf-agent-build-sdk: 未安装")
        print(f"  安装命令: pip install werewolf-agent-build-sdk==0.0.10")
        all_ok = False
    
    print()
    
    # 总结
    print("=" * 60)
    print("检查总结")
    print("=" * 60)
    
    if python_ok and all_ok:
        print("✓ 环境检查通过！你的项目与12人狼人杀模板兼容。")
    else:
        print("✗ 环境检查发现问题，请根据上述提示修复。")
        print()
        print("快速修复命令:")
        print("  pip install -r requirements-lite.txt")
        print("  或")
        print("  pip install -r requirements-full.txt")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
