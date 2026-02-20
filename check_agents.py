#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
角色代理实现检查脚本
快速检查所有角色的实现状态和功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_agent_features(agent, role_name):
    """检查代理的功能特性"""
    features = {
        'ML增强': hasattr(agent, 'ml_agent'),
        '注入检测': hasattr(agent, 'injection_detector'),
        '信任分析': hasattr(agent, 'trust_analyzer'),
        '增量学习': hasattr(agent, 'learning_system'),
        '双模型': hasattr(agent, 'analysis_client') or hasattr(agent, 'analysis_model_name'),
        '检测系统': hasattr(agent, 'detector_manager'),
        '决策引擎': hasattr(agent, 'decision_engine'),
    }
    return features

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🎭 狼人杀AI系统 - 角色代理实现检查")
    print("=" * 80)
    
    agents_config = [
        ('👤 平民', 'werewolf.villager.villager_agent', 'VillagerAgent'),
        ('🐺 狼人', 'werewolf.wolf.wolf_agent', 'WolfAgent'),
        ('🔮 预言家', 'werewolf.seer.seer_agent', 'SeerAgent'),
        ('🧙 女巫', 'werewolf.witch.witch_agent', 'WitchAgent'),
        ('🛡️ 守卫', 'werewolf.guard.guard_agent', 'GuardAgent'),
        ('🏹 猎人', 'werewolf.hunter.hunter_agent', 'HunterAgent'),
        ('👑 狼王', 'werewolf.wolf_king.wolf_king_agent', 'WolfKingAgent'),
    ]
    
    results = []
    
    for emoji_name, module_path, class_name in agents_config:
        print(f"\n{'─' * 80}")
        print(f"检查角色: {emoji_name}")
        print(f"{'─' * 80}")
        
        try:
            # 导入模块
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # 实例化
            agent = agent_class('test-model')
            
            # 检查功能
            features = check_agent_features(agent, emoji_name)
            
            print(f"✅ 状态: 实现完整")
            print(f"📦 模块: {module_path}")
            print(f"🏷️  类名: {class_name}")
            print(f"\n🔧 功能特性:")
            
            for feature_name, has_feature in features.items():
                status = "✅" if has_feature else "❌"
                print(f"   {status} {feature_name}")
            
            # 检查关键方法
            key_methods = ['__init__', 'run', 'memory']
            print(f"\n🔑 关键组件:")
            for method in key_methods:
                has_method = hasattr(agent, method)
                status = "✅" if has_method else "❌"
                print(f"   {status} {method}")
            
            results.append((emoji_name, True, features))
            
        except Exception as e:
            print(f"❌ 状态: 实现失败")
            print(f"⚠️  错误: {str(e)}")
            results.append((emoji_name, False, {}))
    
    # 打印总结
    print("\n" + "=" * 80)
    print("📊 检查总结")
    print("=" * 80)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    print(f"\n总角色数: {total_count}")
    print(f"实现成功: {success_count}")
    print(f"实现失败: {total_count - success_count}")
    print(f"完成度: {success_count / total_count * 100:.1f}%")
    
    # 功能统计
    print(f"\n🎯 功能统计:")
    feature_stats = {}
    for _, success, features in results:
        if success:
            for feature_name, has_feature in features.items():
                if feature_name not in feature_stats:
                    feature_stats[feature_name] = 0
                if has_feature:
                    feature_stats[feature_name] += 1
    
    for feature_name, count in sorted(feature_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = count / success_count * 100
        bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
        print(f"   {feature_name:12} [{bar}] {count}/{success_count} ({percentage:.0f}%)")
    
    # 详细列表
    print(f"\n📋 角色列表:")
    for emoji_name, success, features in results:
        status = "✅" if success else "❌"
        feature_count = sum(1 for has in features.values() if has) if success else 0
        print(f"   {status} {emoji_name:12} - {feature_count} 个功能")
    
    print("\n" + "=" * 80)
    
    if success_count == total_count:
        print("🎉 所有角色代理均已完整实现！系统可以正常运行！")
    else:
        print(f"⚠️  有 {total_count - success_count} 个角色实现失败，请检查错误信息")
    
    print("=" * 80 + "\n")
    
    return 0 if success_count == total_count else 1

if __name__ == '__main__':
    sys.exit(main())
