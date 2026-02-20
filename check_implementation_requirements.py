#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查实现需求
- 好人阵营：所有功能必须实现
- 狼人阵营：除信任分析外，其他功能必须实现
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_good_camp():
    """检查好人阵营功能"""
    print("\n" + "=" * 80)
    print("🌟 好人阵营功能检查 (必须全部实现)")
    print("=" * 80)
    
    good_agents = [
        ('👤 平民', 'werewolf.villager.villager_agent', 'VillagerAgent', [
            'ml_agent', 'injection_detector', 'false_quote_detector', 
            'message_parser', 'speech_quality_evaluator'  # 正确的属性名
        ]),
        ('🔮 预言家', 'werewolf.seer.seer_agent', 'SeerAgent', [
            'ml_agent', 'injection_detector', 'ml_data_collector'  # 正确的属性名
        ]),
        ('🧙 女巫', 'werewolf.witch.witch_agent', 'WitchAgent', [
            'ml_agent', 'decision_engine', 'message_analyzer'  # 正确的属性名
        ]),
        ('🛡️ 守卫', 'werewolf.guard.guard_agent', 'GuardAgent', [
            'ml_agent', 'injection_detector', 'false_quotation_detector',
            'status_contradiction_detector', 'speech_quality_detector'
        ]),
        ('🏹 猎人', 'werewolf.hunter.hunter_agent', 'HunterAgent', [
            'ml_agent', 'trust_analyzer', 'voting_analyzer', 
            'speech_analyzer', 'threat_analyzer', 'wolf_prob_calculator',
            'detector_manager'
        ]),
    ]
    
    all_passed = True
    
    for emoji_name, module_path, class_name, required_attrs in good_agents:
        print(f"\n{'─' * 80}")
        print(f"检查: {emoji_name}")
        print(f"{'─' * 80}")
        
        try:
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            agent = agent_class('test-model')
            
            missing = []
            for attr in required_attrs:
                if not hasattr(agent, attr):
                    missing.append(attr)
            
            if missing:
                print(f"❌ 缺失功能: {', '.join(missing)}")
                all_passed = False
            else:
                print(f"✅ 所有功能已实现 ({len(required_attrs)} 个)")
                for attr in required_attrs:
                    print(f"   ✓ {attr}")
                    
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            all_passed = False
    
    return all_passed

def check_wolf_camp():
    """检查狼人阵营功能"""
    print("\n" + "=" * 80)
    print("🐺 狼人阵营功能检查 (除信任分析外必须全部实现)")
    print("=" * 80)
    
    wolf_agents = [
        ('🐺 狼人', 'werewolf.wolf.wolf_agent', 'WolfAgent', [
            'ml_agent', 'decision_engine', 'analysis_client',  # 双模型
            'injection_detector', 'detector_manager'
        ]),
        ('👑 狼王', 'werewolf.wolf_king.wolf_king_agent', 'WolfKingAgent', [
            'ml_agent', 'decision_engine', 'analysis_client',  # 双模型
            'injection_detector', 'detector_manager'
        ]),
    ]
    
    all_passed = True
    
    for emoji_name, module_path, class_name, required_attrs in wolf_agents:
        print(f"\n{'─' * 80}")
        print(f"检查: {emoji_name}")
        print(f"{'─' * 80}")
        
        try:
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            agent = agent_class('test-model')
            
            missing = []
            for attr in required_attrs:
                if not hasattr(agent, attr):
                    missing.append(attr)
            
            # 确认没有信任分析（这是预期的）
            has_trust = hasattr(agent, 'trust_analyzer')
            
            if missing:
                print(f"❌ 缺失功能: {', '.join(missing)}")
                all_passed = False
            else:
                print(f"✅ 所有必需功能已实现 ({len(required_attrs)} 个)")
                for attr in required_attrs:
                    print(f"   ✓ {attr}")
            
            if has_trust:
                print(f"⚠️  警告: 不应该有 trust_analyzer (狼人不需要)")
                    
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            all_passed = False
    
    return all_passed

def main():
    print("\n" + "=" * 80)
    print("🎭 狼人杀AI系统 - 实现需求检查")
    print("=" * 80)
    
    good_passed = check_good_camp()
    wolf_passed = check_wolf_camp()
    
    print("\n" + "=" * 80)
    print("📊 检查结果")
    print("=" * 80)
    
    print(f"\n好人阵营: {'✅ 通过' if good_passed else '❌ 未通过'}")
    print(f"狼人阵营: {'✅ 通过' if wolf_passed else '❌ 未通过'}")
    
    if good_passed and wolf_passed:
        print("\n🎉 所有需求均已满足！")
        return 0
    else:
        print("\n⚠️  部分需求未满足，请查看上方详情")
        return 1

if __name__ == '__main__':
    sys.exit(main())
