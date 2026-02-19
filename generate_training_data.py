#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成更多训练数据 - 模拟不同游戏场景
"""

import json
import random
import os
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_wolf_data(player_name: str, game_id: str, skill_level: str = "medium") -> Dict:
    """生成狼人数据"""
    
    if skill_level == "high":
        # 高水平狼人：伪装好，但有细微破绽
        trust_score = random.uniform(55, 75)
        vote_accuracy = random.uniform(0.4, 0.6)
        contradiction_count = random.randint(1, 3)
        injection_attempts = random.randint(0, 1)
        false_quotation_count = random.randint(0, 1)
        speech_lengths = [random.randint(120, 180) for _ in range(random.randint(2, 4))]
        voting_speed_avg = random.uniform(3.0, 5.0)
        aggressive_score = random.uniform(0.4, 0.6)
        defensive_score = random.uniform(0.5, 0.7)
        emotion_keyword_count = random.randint(6, 10)
        logic_keyword_count = random.randint(8, 15)
        speech_consistency_score = random.uniform(0.6, 0.8)
        
    elif skill_level == "low":
        # 低水平狼人：破绽明显
        trust_score = random.uniform(20, 40)
        vote_accuracy = random.uniform(0.2, 0.4)
        contradiction_count = random.randint(5, 8)
        injection_attempts = random.randint(2, 4)
        false_quotation_count = random.randint(1, 3)
        speech_lengths = [random.randint(40, 80) for _ in range(random.randint(1, 3))]
        voting_speed_avg = random.uniform(1.5, 3.0)
        aggressive_score = random.uniform(0.7, 0.9)
        defensive_score = random.uniform(0.8, 1.0)
        emotion_keyword_count = random.randint(10, 18)
        logic_keyword_count = random.randint(2, 6)
        speech_consistency_score = random.uniform(0.2, 0.4)
        
    else:  # medium
        # 中等水平狼人
        trust_score = random.uniform(40, 60)
        vote_accuracy = random.uniform(0.3, 0.5)
        contradiction_count = random.randint(3, 5)
        injection_attempts = random.randint(1, 2)
        false_quotation_count = random.randint(0, 2)
        speech_lengths = [random.randint(60, 120) for _ in range(random.randint(2, 3))]
        voting_speed_avg = random.uniform(2.0, 4.0)
        aggressive_score = random.uniform(0.6, 0.8)
        defensive_score = random.uniform(0.6, 0.9)
        emotion_keyword_count = random.randint(8, 14)
        logic_keyword_count = random.randint(4, 10)
        speech_consistency_score = random.uniform(0.3, 0.6)
    
    return {
        "game_id": game_id,
        "player_name": player_name,
        "role": "wolf",
        "data": {
            "trust_score": trust_score,
            "vote_accuracy": vote_accuracy,
            "contradiction_count": contradiction_count,
            "injection_attempts": injection_attempts,
            "false_quotation_count": false_quotation_count,
            "speech_lengths": speech_lengths,
            "voting_speed_avg": voting_speed_avg,
            "vote_targets": [f"No.{random.randint(1, 12)}" for _ in range(random.randint(1, 3))],
            "mentions_others_count": random.randint(10, 20),
            "mentioned_by_others_count": random.randint(2, 8),
            "aggressive_score": aggressive_score,
            "defensive_score": defensive_score,
            "emotion_keyword_count": emotion_keyword_count,
            "logic_keyword_count": logic_keyword_count,
            "night_survival_rate": random.uniform(0.7, 1.0),
            "alliance_strength": random.uniform(0.6, 0.9),
            "isolation_score": random.uniform(0.5, 0.8),
            "speech_consistency_score": speech_consistency_score,
            "avg_response_time": voting_speed_avg
        }
    }


def generate_good_data(player_name: str, game_id: str, skill_level: str = "medium") -> Dict:
    """生成好人数据"""
    
    if skill_level == "high":
        # 高水平好人：逻辑清晰，投票准确
        trust_score = random.uniform(70, 90)
        vote_accuracy = random.uniform(0.7, 0.9)
        contradiction_count = random.randint(0, 1)
        injection_attempts = 0
        false_quotation_count = 0
        speech_lengths = [random.randint(140, 200) for _ in range(random.randint(3, 5))]
        voting_speed_avg = random.uniform(4.0, 6.0)
        aggressive_score = random.uniform(0.3, 0.5)
        defensive_score = random.uniform(0.2, 0.4)
        emotion_keyword_count = random.randint(3, 7)
        logic_keyword_count = random.randint(15, 25)
        speech_consistency_score = random.uniform(0.8, 0.95)
        
    elif skill_level == "low":
        # 低水平好人：容易被误导
        trust_score = random.uniform(45, 65)
        vote_accuracy = random.uniform(0.4, 0.6)
        contradiction_count = random.randint(1, 3)
        injection_attempts = 0
        false_quotation_count = random.randint(0, 1)
        speech_lengths = [random.randint(60, 100) for _ in range(random.randint(1, 3))]
        voting_speed_avg = random.uniform(3.0, 5.0)
        aggressive_score = random.uniform(0.4, 0.6)
        defensive_score = random.uniform(0.4, 0.6)
        emotion_keyword_count = random.randint(6, 12)
        logic_keyword_count = random.randint(6, 12)
        speech_consistency_score = random.uniform(0.5, 0.7)
        
    else:  # medium
        # 中等水平好人
        trust_score = random.uniform(60, 80)
        vote_accuracy = random.uniform(0.6, 0.8)
        contradiction_count = random.randint(0, 2)
        injection_attempts = 0
        false_quotation_count = random.randint(0, 1)
        speech_lengths = [random.randint(100, 160) for _ in range(random.randint(2, 4))]
        voting_speed_avg = random.uniform(3.5, 5.5)
        aggressive_score = random.uniform(0.3, 0.5)
        defensive_score = random.uniform(0.3, 0.5)
        emotion_keyword_count = random.randint(4, 10)
        logic_keyword_count = random.randint(10, 18)
        speech_consistency_score = random.uniform(0.7, 0.85)
    
    return {
        "game_id": game_id,
        "player_name": player_name,
        "role": "good",
        "data": {
            "trust_score": trust_score,
            "vote_accuracy": vote_accuracy,
            "contradiction_count": contradiction_count,
            "injection_attempts": injection_attempts,
            "false_quotation_count": false_quotation_count,
            "speech_lengths": speech_lengths,
            "voting_speed_avg": voting_speed_avg,
            "vote_targets": [f"No.{random.randint(1, 12)}" for _ in range(random.randint(1, 3))],
            "mentions_others_count": random.randint(8, 15),
            "mentioned_by_others_count": random.randint(5, 12),
            "aggressive_score": aggressive_score,
            "defensive_score": defensive_score,
            "emotion_keyword_count": emotion_keyword_count,
            "logic_keyword_count": logic_keyword_count,
            "night_survival_rate": random.uniform(0.3, 0.7),
            "alliance_strength": random.uniform(0.4, 0.7),
            "isolation_score": random.uniform(0.2, 0.5),
            "speech_consistency_score": speech_consistency_score,
            "avg_response_time": voting_speed_avg
        }
    }


def generate_game_data(game_id: str, num_players: int = 12) -> List[Dict]:
    """生成一局游戏的数据"""
    
    # 标准12人局：4狼8好人
    num_wolves = 4
    num_good = num_players - num_wolves
    
    game_data = []
    
    # 随机分配技能水平
    skill_levels = ["low", "medium", "high"]
    
    # 生成狼人数据
    for i in range(num_wolves):
        skill = random.choice(skill_levels)
        player_name = f"No.{i+1}"
        game_data.append(generate_wolf_data(player_name, game_id, skill))
    
    # 生成好人数据
    for i in range(num_good):
        skill = random.choice(skill_levels)
        player_name = f"No.{num_wolves + i + 1}"
        game_data.append(generate_good_data(player_name, game_id, skill))
    
    # 打乱顺序
    random.shuffle(game_data)
    
    return game_data


def generate_dataset(num_games: int = 100, output_file: str = "game_data/collected_data.json"):
    """生成完整数据集"""
    
    logger.info(f"Generating {num_games} games of training data...")
    
    all_data = []
    
    for game_num in range(1, num_games + 1):
        game_id = f"game_{game_num}"
        game_data = generate_game_data(game_id)
        all_data.extend(game_data)
        
        if game_num % 10 == 0:
            logger.info(f"Generated {game_num}/{num_games} games ({len(all_data)} samples)")
    
    # 保存数据
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    output = {
        "game_count": num_games,
        "data": all_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ Generated {num_games} games with {len(all_data)} samples")
    logger.info(f"✓ Data saved to {output_file}")
    
    # 统计信息
    wolf_count = sum(1 for d in all_data if d['role'] == 'wolf')
    good_count = len(all_data) - wolf_count
    
    logger.info(f"\nDataset Statistics:")
    logger.info(f"  Total samples: {len(all_data)}")
    logger.info(f"  Wolf samples: {wolf_count} ({wolf_count/len(all_data)*100:.1f}%)")
    logger.info(f"  Good samples: {good_count} ({good_count/len(all_data)*100:.1f}%)")
    logger.info(f"  Samples per game: {len(all_data)/num_games:.1f}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate training data for Werewolf AI")
    parser.add_argument("--games", type=int, default=100, help="Number of games to generate (default: 100)")
    parser.add_argument("--output", type=str, default="game_data/collected_data.json", help="Output file path")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Werewolf AI Training Data Generator")
    logger.info("=" * 60)
    
    generate_dataset(num_games=args.games, output_file=args.output)
    
    logger.info("=" * 60)
    logger.info("✓ Data generation completed!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
