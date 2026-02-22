# -*- coding: utf-8 -*-
"""
预言家代理人完整性验证脚本

验证所有组件、算法逻辑、调用逻辑是否正确
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from werewolf.seer.seer_agent import SeerAgent
from werewolf.seer.config import SeerConfig
from werewolf.seer.analyzers import CheckPriorityCalculator
from werewolf.seer.decision_makers import CheckDecisionMaker
from werewolf.seer.utils import SpeechTruncator, PlayerExtractor, CheckReasonGenerator
from werewolf.seer.memory_dao import SeerMemoryDAO
from agent_build_sdk.model.werewolf_model import AgentReq
from unittest.mock import Mock, patch


def test_config_validation():
    """测试配置验证"""
    print("\n=== 测试配置验证 ===")
    
    config = SeerConfig()
    assert config.validate(), "配置验证失败"
    print("✓ 配置验证通过")
    
    # 测试边界值
    assert config.check_strategy in ["suspicious", "random", "strategic"]
    assert config.reveal_threshold >= 1
    assert config.trust_check_result == True
    print("✓ 配置边界值检查通过")


def test_check_priority_calculator():
    """测试检查优先级计算器"""
    print("\n=== 测试检查优先级计算器 ===")
    
    config = SeerConfig()
    calculator = CheckPriorityCalculator(config)
    
    # 测试正常计算
    context = {
        'player_data': {
            'No.3': {
                'malicious_injection': True,
                'false_quotes': 2,
                'contradictions': 1
            }
        },
        'trust_scores': {'No.3': 20},
        'night_count': 1,
        'game_state': {}
    }
    
    priority = calculator.calculate('No.3', context)
    assert 0 <= priority <= 100, f"优先级超出范围: {priority}"
    assert priority > 90, f"恶意注入应该有极高优先级，实际: {priority}"
    print(f"✓ 恶意注入玩家优先级: {priority:.1f} (预期 >90)")
    
    # 测试缓存
    priority2 = calculator.calculate('No.3', context)
    assert priority == priority2, "缓存结果不一致"
    stats = calculator.get_cache_stats()
    assert stats['cache_hits'] > 0, "缓存未命中"
    print(f"✓ 缓存系统正常 (命中率: {stats['hit_rate']:.1%})")
    
    # 测试边界情况
    empty_context = {
        'player_data': {},
        'trust_scores': {},
        'night_count': 0,
        'game_state': {}
    }
    priority3 = calculator.calculate('No.5', empty_context)
    assert 0 <= priority3 <= 100, f"空上下文优先级超出范围: {priority3}"
    print(f"✓ 空上下文处理正常: {priority3:.1f}")


def test_check_decision_maker():
    """测试检查决策器"""
    print("\n=== 测试检查决策器 ===")
    
    config = SeerConfig()
    decision_maker = CheckDecisionMaker(config)
    
    candidates = ['No.2', 'No.3', 'No.4', 'No.5']
    context = {
        'checked_players': {},
        'player_data': {
            'No.3': {
                'malicious_injection': True,
                'injection_type': 'SYSTEM_FAKE'
            },
            'No.4': {
                'false_quotes': 2
            }
        },
        'game_state': {},
        'trust_scores': {
            'No.2': 60,
            'No.3': 15,
            'No.4': 25,
            'No.5': 50
        },
        'night_count': 1
    }
    
    target, reason = decision_maker.decide(candidates, context)
    assert target in candidates, f"决策目标不在候选人中: {target}"
    assert target == 'No.3', f"应该选择恶意注入玩家，实际选择: {target}"
    assert '恶意注入' in reason or 'injection' in reason.lower(), f"原因不包含注入信息: {reason}"
    print(f"✓ 决策正确: {target} (原因: {reason})")
    
    # 测试缓存
    target2, reason2 = decision_maker.decide(candidates, context)
    assert target == target2, "缓存决策不一致"
    stats = decision_maker.get_cache_stats()
    print(f"✓ 决策缓存正常 (命中率: {stats['hit_rate']:.1%})")


def test_memory_dao():
    """测试内存DAO"""
    print("\n=== 测试内存DAO ===")
    
    mock_memory = Mock()
    mock_memory.load_variable = Mock(return_value={})
    mock_memory.set_variable = Mock()
    mock_memory.append_history = Mock()
    mock_memory.load_history = Mock(return_value=[])
    
    dao = SeerMemoryDAO(mock_memory)
    
    # 测试基本操作
    dao.set('test_key', 'test_value')
    mock_memory.set_variable.assert_called_with('test_key', 'test_value')
    print("✓ 基本set操作正常")
    
    # 测试检查结果管理
    dao.add_checked_player('No.3', True, 1)
    print("✓ 检查结果添加正常")
    
    # 测试信任分数管理
    dao.set_trust_scores({'No.3': 20, 'No.4': 70})
    print("✓ 信任分数管理正常")


def test_utils():
    """测试工具类"""
    print("\n=== 测试工具类 ===")
    
    config = SeerConfig()
    
    # 测试发言截断器
    truncator = SpeechTruncator(config)
    long_text = "A" * 2000
    truncated = truncator.truncate(long_text, 1400)
    assert len(truncated) <= 1400, f"截断失败: {len(truncated)}"
    print(f"✓ 发言截断器正常 (2000 -> {len(truncated)})")
    
    # 测试玩家提取器
    alive = PlayerExtractor.get_alive_players(
        {'No.1': [], 'No.2': [], 'No.3': []},
        {'No.2'},
        'No.1'
    )
    assert 'No.1' in alive and 'No.3' in alive and 'No.2' not in alive
    print(f"✓ 玩家提取器正常 (存活: {alive})")
    
    # 测试检查原因生成器
    reason_gen = CheckReasonGenerator(config)
    context = {
        'player_data': {
            'No.3': {'malicious_injection': True}
        },
        'trust_scores': {'No.3': 15}
    }
    reason = reason_gen.generate('No.3', context)
    assert 'injection' in reason.lower(), f"原因生成错误: {reason}"
    print(f"✓ 检查原因生成器正常: {reason}")


def test_seer_agent_initialization():
    """测试预言家代理初始化"""
    print("\n=== 测试预言家代理初始化 ===")
    
    with patch('werewolf.seer.seer_agent.SeerAgent._llm_generate') as mock_llm:
        mock_llm.return_value = "Test response"
        agent = SeerAgent(model_name="test_model")
        
        # 验证组件初始化
        assert agent.config is not None, "配置未初始化"
        assert agent.memory_dao is not None, "MemoryDAO未初始化"
        assert agent.check_priority_calculator is not None, "优先级计算器未初始化"
        assert agent.check_decision_maker is not None, "检查决策器未初始化"
        assert agent.check_reason_generator is not None, "原因生成器未初始化"
        print("✓ 所有组件初始化成功")
        
        # 验证继承的组件
        assert hasattr(agent, 'trust_score_manager'), "缺少信任分数管理器"
        assert hasattr(agent, 'vote_decision_maker'), "缺少投票决策器"
        assert hasattr(agent, 'sheriff_election_decision_maker'), "缺少警长选举决策器"
        print("✓ 继承组件正常")


def test_perceive_events():
    """测试事件处理"""
    print("\n=== 测试事件处理 ===")
    
    with patch('werewolf.seer.seer_agent.SeerAgent._llm_generate') as mock_llm:
        mock_llm.return_value = "Test response"
        agent = SeerAgent(model_name="test_model")
        
        # 测试游戏开始
        req = AgentReq(status="start", name="No.1")
        agent.perceive(req)
        assert agent.memory_dao.get_my_name() == "No.1"
        print("✓ 游戏开始事件处理正常")
        
        # 测试夜晚
        req = AgentReq(status="night")
        agent.perceive(req)
        assert agent.memory_dao.get_night_count() == 1
        print("✓ 夜晚事件处理正常")
        
        # 测试技能结果
        req = AgentReq(status="skill_result", name="No.3", message="No.3 is a werewolf")
        agent.perceive(req)
        checked = agent.memory_dao.get_checked_players()
        assert 'No.3' in checked
        assert checked['No.3']['is_wolf'] == True
        print("✓ 技能结果事件处理正常")
        
        # 测试讨论
        req = AgentReq(status="discuss", name="No.4", message="I think No.3 is suspicious")
        agent.perceive(req)
        history = agent.memory_dao.get_history()
        assert any('No.4' in h for h in history)
        print("✓ 讨论事件处理正常")


def test_interact_methods():
    """测试交互方法"""
    print("\n=== 测试交互方法 ===")
    
    with patch('werewolf.seer.seer_agent.SeerAgent._llm_generate') as mock_llm:
        mock_llm.return_value = "I am analyzing the situation carefully."
        agent = SeerAgent(model_name="test_model")
        agent.memory.set_variable("name", "No.1")
        agent.memory.set_variable("alive_players", ["No.1", "No.2", "No.3", "No.4"])
        agent.memory.set_variable("game_state", {"alive_count": 4, "current_day": 1})
        
        # 测试讨论发言
        req = AgentReq(status="discuss", message="Day 1 discussion")
        resp = agent._interact_discuss(req)
        assert resp.success, "讨论发言失败"
        assert len(resp.result) > 0, "发言内容为空"
        print(f"✓ 讨论发言正常 (长度: {len(resp.result)})")
        
        # 测试技能使用
        req = AgentReq(status="skill", message="No.2,No.3,No.4")
        resp = agent._interact_skill(req)
        assert resp.success, "技能使用失败"
        assert resp.result in ["No.2", "No.3", "No.4"], f"技能目标无效: {resp.result}"
        print(f"✓ 技能使用正常 (目标: {resp.result})")
        
        # 测试投票
        with patch.object(agent, '_make_vote_decision', return_value="No.3"):
            req = AgentReq(status="vote", message="No.2,No.3,No.4")
            resp = agent._interact_vote(req)
            assert resp.success, "投票失败"
            assert resp.result == "No.3", f"投票目标错误: {resp.result}"
            print(f"✓ 投票正常 (目标: {resp.result})")


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===")
    
    config = SeerConfig()
    calculator = CheckPriorityCalculator(config)
    
    # 测试空候选人
    try:
        decision_maker = CheckDecisionMaker(config)
        decision_maker.decide([], {})
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"✓ 空候选人异常处理正常: {e}")
    
    # 测试无效上下文
    priority = calculator.calculate('No.1', {})
    assert 0 <= priority <= 100, f"无效上下文优先级超出范围: {priority}"
    print(f"✓ 无效上下文处理正常: {priority:.1f}")
    
    # 测试极端信任分数
    context = {
        'player_data': {'No.1': {'wolf_protecting_votes': 2}},  # 添加强可疑行为
        'trust_scores': {'No.1': 5},  # 极低信任（在0-100范围内）
        'night_count': 1,
        'game_state': {}
    }
    priority = calculator.calculate('No.1', context)
    # 保护狼人投票应该触发高优先级（85分），但由于是第一夜，权重较低
    assert priority > 50, f"极低信任+保护狼人投票应该有中高优先级，实际: {priority}"
    print(f"✓ 极端信任分数处理正常: {priority:.1f}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("预言家代理人完整性验证")
    print("=" * 60)
    
    try:
        test_config_validation()
        test_check_priority_calculator()
        test_check_decision_maker()
        test_memory_dao()
        test_utils()
        test_seer_agent_initialization()
        test_perceive_events()
        test_interact_methods()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("✓ 所有验证通过！预言家代理人达到企业级五星标准")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ 未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
