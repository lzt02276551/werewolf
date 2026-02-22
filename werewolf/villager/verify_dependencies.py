#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
平民代理依赖验证脚本

验证所有依赖是否正确安装和可导入
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def check_dependency(module_path, description=""):
    """检查单个依赖"""
    try:
        parts = module_path.split('.')
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        print(f"✅ {module_path:<60} {description}")
        return True
    except ImportError as e:
        print(f"❌ {module_path:<60} {description}")
        print(f"   错误: {e}")
        return False
    except AttributeError as e:
        print(f"⚠️  {module_path:<60} {description}")
        print(f"   警告: {e}")
        return False
    except Exception as e:
        print(f"❌ {module_path:<60} {description}")
        print(f"   未知错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 80)
    print("平民代理依赖验证")
    print("=" * 80)
    print()
    
    results = []
    
    # 1. SDK依赖
    print("【1. SDK框架依赖】")
    results.append(check_dependency("agent_build_sdk.sdk.role_agent", "SDK基类"))
    results.append(check_dependency("agent_build_sdk.model.roles", "角色定义"))
    results.append(check_dependency("agent_build_sdk.model.werewolf_model", "游戏模型"))
    results.append(check_dependency("agent_build_sdk.utils.logger", "日志工具"))
    results.append(check_dependency("agent_build_sdk.sdk.agent", "Agent基类"))
    print()
    
    # 2. 核心依赖
    print("【2. 核心模块依赖】")
    results.append(check_dependency("werewolf.core.base_good_agent", "好人基类"))
    results.append(check_dependency("werewolf.core.base_good_config", "好人配置"))
    results.append(check_dependency("werewolf.core.base_components", "基础组件"))
    results.append(check_dependency("werewolf.core.llm_detectors", "LLM检测器"))
    results.append(check_dependency("werewolf.core.decision_engine", "决策引擎"))
    print()
    
    # 3. 通用工具依赖
    print("【3. 通用工具依赖】")
    results.append(check_dependency("werewolf.common.utils", "通用工具"))
    results.append(check_dependency("werewolf.common.detectors", "检测器"))
    print()
    
    # 4. 平民模块依赖
    print("【4. 平民模块依赖】")
    results.append(check_dependency("werewolf.villager.config", "平民配置"))
    results.append(check_dependency("werewolf.villager.decision_makers", "决策器"))
    results.append(check_dependency("werewolf.villager.analyzers", "分析器"))
    results.append(check_dependency("werewolf.villager.prompt", "提示词"))
    print()
    
    # 5. 优化模块依赖
    print("【5. 优化模块依赖】")
    results.append(check_dependency("werewolf.optimization.utils.safe_math", "安全数学"))
    results.append(check_dependency("werewolf.optimization.algorithms.trust_score", "信任分数算法"))
    results.append(check_dependency("werewolf.optimization.algorithms.bayesian_inference", "贝叶斯推理"))
    print()
    
    # 6. 可选依赖（不影响核心功能）
    print("【6. 可选依赖（缺失不影响核心功能）】")
    optional_deps = [
        ("ml_agent", "ML增强"),
        ("incremental_learning", "增量学习"),
        ("game_end_handler", "游戏结束处理"),
        ("game_utils", "游戏工具"),
    ]
    
    for module, desc in optional_deps:
        try:
            __import__(module)
            print(f"✅ {module:<60} {desc}")
        except ImportError:
            print(f"⚠️  {module:<60} {desc} (可选，未安装)")
    print()
    
    # 7. 测试实际导入
    print("【7. 测试实际导入】")
    try:
        from werewolf.villager import VillagerAgent, VillagerConfig
        print(f"✅ {'werewolf.villager.VillagerAgent':<60} 平民代理类")
        print(f"✅ {'werewolf.villager.VillagerConfig':<60} 平民配置类")
        
        # 测试初始化
        config = VillagerConfig()
        print(f"✅ {'VillagerConfig()':<60} 配置初始化成功")
        
        # 测试代理初始化（需要模型名称）
        try:
            agent = VillagerAgent("test-model")
            print(f"✅ {'VillagerAgent(model_name)':<60} 代理初始化成功")
        except Exception as e:
            print(f"⚠️  {'VillagerAgent(model_name)':<60} 代理初始化警告: {e}")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        results.append(False)
    print()
    
    # 统计结果
    print("=" * 80)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"验证完成: {passed}/{total} 通过")
    
    if failed > 0:
        print(f"⚠️  {failed} 个依赖检查失败")
        print("请检查上述失败的依赖并确保正确安装")
        return 1
    else:
        print("✅ 所有核心依赖检查通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
