"""
增强决策引擎 - 阶段五优化
替代简单线性逻辑，引入复杂决策树和贝叶斯推理
"""
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class EnhancedDecisionEngine:
    """增强决策引擎 - 复杂决策树 + 贝叶斯推理 + ML融合"""
    
    def __init__(self, ml_agent=None):
        self.ml_agent = ml_agent
        self.ml_enabled = ml_agent is not None
        self.ml_fusion_ratio = float(os.getenv('ML_FUSION_RATIO', '0.6'))
        
        logger.info("✓ EnhancedDecisionEngine initialized")
        logger.info(f"  - ML enabled: {self.ml_enabled}")
        logger.info(f"  - ML fusion ratio: {self.ml_fusion_ratio}")
    
    def decide_vote(
        self,
        candidates: List[str],
        context: Dict[str, Any],
        game_phase: str = "midgame"
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        投票决策 - 复杂决策树 + ML融合
        
        Args:
            candidates: 候选人列表
            context: 游戏上下文
            game_phase: 游戏阶段 (early/midgame/endgame)
        
        Returns:
            (目标玩家, 置信度, 所有候选人分数)
        """
        if not candidates:
            logger.warning("候选人列表为空")
            return None, 0.0, {}
        
        if not isinstance(candidates, list):
            logger.error(f"候选人列表类型错误: {type(candidates)}")
            return None, 0.0, {}
        
        if not isinstance(context, dict):
            logger.error(f"上下文类型错误: {type(context)}")
            return candidates[0] if candidates else None, 0.5, {}
        
        # 验证游戏阶段
        valid_phases = ['early', 'midgame', 'endgame']
        if game_phase not in valid_phases:
            logger.warning(f"无效的游戏阶段: {game_phase}, 使用默认值 'midgame'")
            game_phase = 'midgame'
        
        try:
            # 1. 决策树评分
            dt_scores = self._decision_tree_scoring(candidates, context, game_phase)
            
            # 2. ML预测评分
            ml_scores = self._ml_scoring(candidates, context) if self.ml_enabled else {}
            
            # 3. 动态融合
            final_scores = self._dynamic_fusion(dt_scores, ml_scores, context)
            
            if not final_scores:
                logger.warning("最终分数为空，返回第一个候选人")
                return candidates[0], 0.5, {}
            
            # 4. 选择最高分
            target = max(final_scores, key=final_scores.get)
            confidence = self._calculate_confidence(final_scores[target], final_scores)
            
            logger.info(f"[VOTE DECISION] Target: {target}, Confidence: {confidence:.2f}")
            
            return target, confidence, final_scores
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"投票决策失败: {e}")
            return candidates[0] if candidates else None, 0.5, {}
        except Exception as e:
            logger.error(f"投票决策未知错误: {e}", exc_info=True)
            return candidates[0] if candidates else None, 0.5, {}

    
    def _decision_tree_scoring(
        self,
        candidates: List[str],
        context: Dict[str, Any],
        game_phase: str
    ) -> Dict[str, float]:
        """
        决策树评分 - 20+维度非线性评分
        
        评分维度分类：
        A. 信任与历史行为（5维）
        B. 发言分析（5维）
        C. 行为异常检测（5维）
        D. 角色与身份（4维）
        E. 社交网络（3维）
        F. 投票与站队（4维）
        G. 生存与时机（3维）
        H. 预言家验证（1维）
        
        总计：30维度
        """
        scores = {}
        trust_scores = context.get('trust_scores', {})
        player_data = context.get('player_data', {})
        seer_checks = context.get('seer_checks', {})
        voting_history = context.get('voting_history', {})
        current_day = context.get('current_day', 1)
        
        for candidate in candidates:
            score = 0.0
            data = player_data.get(candidate, {})
            
            # ========== A. 信任与历史行为（5维）==========
            
            # A1. 信任分数（基础维度，权重最高）
            trust = trust_scores.get(candidate, 50)
            if trust < 15:
                score += 100  # 极度怀疑
            elif trust < 25:
                score += 80
            elif trust < 35:
                score += 60
            elif trust < 45:
                score += 40
            elif trust < 55:
                score += 20  # 轻度怀疑
            elif trust > 85:
                score -= 50  # 极度信任
            elif trust > 75:
                score -= 35
            elif trust > 65:
                score -= 20
            
            # A2. 信任变化趋势
            trust_trend = data.get('trust_trend', 0)  # 正数=上升，负数=下降
            if trust_trend < -15:
                score += 30  # 信任快速下降
            elif trust_trend < -5:
                score += 15
            elif trust_trend > 15:
                score -= 20  # 信任快速上升
            
            # A3. 投票准确度（历史行为）
            vote_accuracy = data.get('vote_accuracy', 0.5)
            if vote_accuracy < 0.2:
                score += 60  # 投票极度不准
            elif vote_accuracy < 0.35:
                score += 45
            elif vote_accuracy < 0.5:
                score += 25
            elif vote_accuracy > 0.8:
                score -= 35  # 投票很准
            elif vote_accuracy > 0.65:
                score -= 20
            
            # A4. 历史被投票次数
            被投票次数 = data.get('被投票次数', 0)
            if 被投票次数 >= 3:
                score += 40  # 多次被投
            elif 被投票次数 >= 2:
                score += 25
            elif 被投票次数 == 1:
                score += 10
            
            # A5. 生存天数异常（狼人通常活得久）
            survival_days = data.get('survival_days', current_day)
            alive_count = context.get('alive_players', 12)
            if survival_days >= current_day and current_day >= 4 and alive_count <= 7:
                score += 25  # 残局还活着
            
            # ========== B. 发言分析（5维）==========
            
            # B1. 发言逻辑性
            if 'llm_analysis' in data:
                analysis = data['llm_analysis']
                logic_score = analysis.get('logic_score', 50)
                if logic_score < 25:
                    score += 45  # 逻辑极度混乱
                elif logic_score < 35:
                    score += 35
                elif logic_score < 45:
                    score += 20
                elif logic_score > 80:
                    score -= 25  # 逻辑清晰
                elif logic_score > 70:
                    score -= 15
                
                # B2. 信息量
                info_score = analysis.get('information_score', 50)
                if info_score < 30:
                    score += 30  # 信息量极少
                elif info_score < 45:
                    score += 15
                elif info_score > 75:
                    score -= 20  # 信息量丰富
                
                # B3. 说服力
                persuasion_score = analysis.get('persuasion_score', 50)
                if persuasion_score < 30:
                    score += 25  # 说服力弱
                elif persuasion_score > 75:
                    score -= 15  # 说服力强
                
                # B4. 战略性
                strategy_score = analysis.get('strategy_score', 50)
                if strategy_score < 30:
                    score += 20  # 缺乏战略
                elif strategy_score > 75:
                    score -= 10  # 战略清晰
            
            # B5. 发言频率异常
            speech_count = data.get('speech_count', 0)
            avg_speech_count = context.get('avg_speech_count', 3)
            if speech_count < avg_speech_count * 0.5:
                score += 25  # 发言过少
            elif speech_count > avg_speech_count * 2:
                score += 15  # 发言过多（可能在带节奏）
            
            # ========== C. 行为异常检测（5维）==========
            
            # C1. 注入攻击
            injection_count = data.get('injection_attempts', 0)
            if injection_count >= 3:
                score += 90  # 多次注入
            elif injection_count == 2:
                score += 70
            elif injection_count == 1:
                score += 45
            
            # C2. 虚假引用
            false_quote_count = data.get('false_quotes', 0)
            if false_quote_count >= 3:
                score += 70
            elif false_quote_count == 2:
                score += 50
            elif false_quote_count == 1:
                score += 30
            
            # C3. 前后矛盾
            contradiction_count = data.get('contradictions', 0)
            if contradiction_count >= 3:
                score += 60
            elif contradiction_count == 2:
                score += 40
            elif contradiction_count == 1:
                score += 20
            
            # C4. 态度转变异常
            attitude_changes = data.get('attitude_changes', 0)
            if attitude_changes >= 3:
                score += 35  # 频繁改变态度
            elif attitude_changes >= 2:
                score += 20
            
            # C5. 跟风投票
            follow_vote_rate = data.get('follow_vote_rate', 0.5)
            if follow_vote_rate > 0.8:
                score += 30  # 总是跟风
            
            # ========== D. 角色与身份（4维）==========
            
            # D1. 虚假角色声称
            if data.get('fake_role_claim'):
                score += 95  # 虚假角色声称（强证据）
            
            # D2. 角色声称冲突
            role_conflict = data.get('role_conflict', False)
            if role_conflict:
                score += 80  # 与他人角色冲突
            
            # D3. 跳神职但无验证
            claimed_role = data.get('claimed_role', '')
            if claimed_role in ['seer', 'witch', 'guard', 'hunter']:
                has_proof = data.get('has_role_proof', False)
                if not has_proof and current_day >= 3:
                    score += 50  # 跳神职但无证明
            
            # D4. 悍跳预言家
            if data.get('claimed_seer') and data.get('is_fake_seer'):
                score += 85  # 悍跳预言家
            
            # ========== E. 社交网络（3维）==========
            
            # E1. 被提及频率
            mentioned_count = data.get('mentioned_by_others', 0)
            if mentioned_count >= 8:
                score += 25  # 被频繁提及
            elif mentioned_count >= 5:
                score += 15
            
            # E2. 站队关系
            team_with_wolves = data.get('team_with_wolves', 0)
            if team_with_wolves >= 2:
                score += 40  # 多次与狼人站队
            elif team_with_wolves == 1:
                score += 20
            
            # E3. 保护可疑玩家
            protect_suspicious = data.get('protect_suspicious_count', 0)
            if protect_suspicious >= 2:
                score += 35  # 多次保护可疑玩家
            elif protect_suspicious == 1:
                score += 18
            
            # ========== F. 投票与站队（4维）==========
            
            # F1. 投票目标分析
            vote_targets = voting_history.get(candidate, [])
            voted_good_players = sum(1 for t in vote_targets if context.get('player_data', {}).get(t, {}).get('is_good', False))
            if len(vote_targets) > 0:
                good_vote_rate = voted_good_players / max(1, len(vote_targets))  # 防止除零
                if good_vote_rate > 0.7:
                    score += 45  # 经常投好人
            
            # F2. 关键投票表现
            key_vote_mistakes = data.get('key_vote_mistakes', 0)
            if key_vote_mistakes >= 2:
                score += 50  # 关键时刻投错
            elif key_vote_mistakes == 1:
                score += 25
            
            # F3. 警长竞选表现
            if data.get('sheriff_candidate'):
                sheriff_speech_quality = data.get('sheriff_speech_quality', 50)
                if sheriff_speech_quality < 40:
                    score += 30  # 竞选发言差
            
            # F4. 投票犹豫度
            vote_hesitation = data.get('vote_hesitation', 0)
            if vote_hesitation > 0.7:
                score += 20  # 经常犹豫
            
            # ========== G. 生存与时机（3维）==========
            
            # G1. 夜晚生存率异常
            night_survival_rate = data.get('night_survival_rate', 0.5)
            if night_survival_rate > 0.8 and current_day >= 4:
                score += 30  # 夜晚总是活着
            
            # G2. 关键时刻发言
            critical_moment_speech = data.get('critical_moment_speech', 0)
            if critical_moment_speech >= 2:
                score += 25  # 关键时刻频繁发言（可能在带节奏）
            
            # G3. 技能使用时机异常
            skill_timing_suspicious = data.get('skill_timing_suspicious', False)
            if skill_timing_suspicious:
                score += 40  # 技能使用时机可疑
            
            # ========== H. 预言家验证（1维，最强证据）==========
            
            # H1. 预言家验证结果
            if candidate in seer_checks:
                seer_result = seer_checks[candidate]
                if isinstance(seer_result, dict):
                    is_wolf = seer_result.get('is_wolf', False)
                    if is_wolf:
                        score += 200  # 预言家验出狼人（最强证据）
                    else:
                        score -= 150  # 预言家验出好人（强排除）
                elif isinstance(seer_result, str):
                    if 'wolf' in seer_result.lower():
                        score += 200
                    else:
                        score -= 150
            
            # ========== 游戏阶段调整 ==========
            phase_multiplier = {
                'early': 0.75,    # 前期更保守
                'midgame': 1.0,   # 中期正常
                'endgame': 1.4    # 残局更激进
            }.get(game_phase, 1.0)
            
            score *= phase_multiplier
            
            scores[candidate] = score
        
        return scores
    
    def _ml_scoring(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        ML预测评分
        
        使用ML模型预测狼人概率
        """
        if not self.ml_agent or not self.ml_enabled:
            return {}
        
        scores = {}
        player_data = context.get('player_data', {})
        
        for candidate in candidates:
            try:
                # 提取特征
                features = self._extract_ml_features(candidate, player_data, context)
                
                # ML预测
                wolf_prob = self.ml_agent.predict_wolf_probability(features)
                
                # 转换为分数（0-100）
                scores[candidate] = wolf_prob * 100
                
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"ML特征提取失败 for {candidate}: {e}")
                scores[candidate] = 50  # 默认中性分数
            except Exception as e:
                logger.error(f"ML评分失败 for {candidate}: {e}", exc_info=True)
                scores[candidate] = 50  # 默认中性分数
        
        return scores
    
    def _extract_ml_features(
        self,
        player: str,
        player_data: Dict,
        context: Dict
    ) -> np.ndarray:
        """提取ML特征"""
        try:
            from ml_enhanced.feature_extractor import StandardFeatureExtractor
            
            data = player_data.get(player, {})
            features = StandardFeatureExtractor.extract_player_features(
                player, data, context
            )
            return StandardFeatureExtractor.features_to_array(features)
        except ImportError as e:
            logger.error(f"无法导入StandardFeatureExtractor: {e}")
            # 返回默认特征向量
            return np.zeros(19)  # 假设19个特征
        except Exception as e:
            logger.error(f"特征提取失败: {e}", exc_info=True)
            return np.zeros(19)
    
    def _dynamic_fusion(
        self,
        dt_scores: Dict[str, float],
        ml_scores: Dict[str, float],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        动态融合 - 根据置信度动态调整融合比例
        
        融合策略：
        1. ML置信度高 -> 增加ML权重
        2. 游戏前期 -> 降低ML权重（数据不足）
        3. 证据充分 -> 增加决策树权重
        """
        if not ml_scores:
            return dt_scores
        
        final_scores = {}
        current_day = context.get('current_day', 1)
        
        for player in dt_scores.keys():
            dt_score = dt_scores[player]
            ml_score = ml_scores.get(player, 50)
            
            # 动态调整融合比例
            fusion_ratio = self._calculate_fusion_ratio(
                player, dt_score, ml_score, current_day, context
            )
            
            # 融合
            final_scores[player] = (
                dt_score * (1 - fusion_ratio) +
                ml_score * fusion_ratio
            )
        
        return final_scores
    
    def _calculate_fusion_ratio(
        self,
        player: str,
        dt_score: float,
        ml_score: float,
        current_day: int,
        context: Dict
    ) -> float:
        """
        计算动态融合比例
        
        Returns:
            融合比例 (0.0-1.0)，越大表示ML权重越高
        """
        base_ratio = self.ml_fusion_ratio
        
        # 1. 游戏阶段调整
        if current_day <= 2:
            # 前期数据不足，降低ML权重
            base_ratio *= 0.6
        elif current_day >= 5:
            # 后期数据充分，增加ML权重
            base_ratio *= 1.2
        
        # 2. 证据充分度调整
        player_data = context.get('player_data', {}).get(player, {})
        evidence_count = (
            player_data.get('injection_attempts', 0) +
            player_data.get('false_quotes', 0) +
            player_data.get('contradictions', 0)
        )
        
        if evidence_count >= 3:
            # 证据充分，增加决策树权重
            base_ratio *= 0.7
        
        # 3. 分数差异调整
        score_diff = abs(dt_score - ml_score)
        if score_diff > 40:
            # 分数差异大，降低融合（避免过度平滑）
            base_ratio *= 0.8
        
        # 限制范围
        return max(0.2, min(0.9, base_ratio))
    
    def _calculate_confidence(
        self,
        target_score: float,
        all_scores: Dict[str, float]
    ) -> float:
        """
        计算决策置信度
        
        置信度基于：
        1. 目标分数绝对值
        2. 与第二名的差距
        3. 分数分布
        """
        if not all_scores:
            return 0.0
        
        try:
            scores_list = sorted(all_scores.values(), reverse=True)
            
            # 1. 绝对分数（归一化到0-1）
            abs_confidence = min(1.0, max(0.0, target_score / 100))
            
            # 2. 相对差距
            if len(scores_list) > 1:
                gap = scores_list[0] - scores_list[1]
                gap_confidence = min(1.0, max(0.0, gap / 50))
            else:
                gap_confidence = 1.0
            
            # 3. 分数分布（标准差）
            if len(scores_list) > 1:
                std = np.std(scores_list)
                dist_confidence = min(1.0, max(0.0, std / 30))
            else:
                dist_confidence = 0.5
            
            # 综合置信度
            confidence = (
                abs_confidence * 0.4 +
                gap_confidence * 0.4 +
                dist_confidence * 0.2
            )
            
            return max(0.0, min(1.0, confidence))
        except (ValueError, TypeError) as e:
            logger.error(f"置信度计算失败: {e}")
            return 0.5
        except Exception as e:
            logger.error(f"置信度计算未知错误: {e}", exc_info=True)
            return 0.5


class BayesianInferenceEngine:
    """贝叶斯推理引擎 - 用于角色推断和概率更新"""
    
    def __init__(self):
        logger.info("✓ BayesianInferenceEngine initialized")
    
    def update_wolf_probability(
        self,
        player: str,
        prior_prob: float,
        evidence: Dict[str, Any]
    ) -> float:
        """
        使用贝叶斯定理更新狼人概率
        
        P(Wolf|Evidence) = P(Evidence|Wolf) * P(Wolf) / P(Evidence)
        
        使用似然比简化计算：
        Posterior_Odds = Prior_Odds * Likelihood_Ratio
        """
        # 计算先验几率（防止除零）
        prior_odds = prior_prob / max(1e-10, 1 - prior_prob)
        
        # 计算似然比
        likelihood_ratio = self._calculate_likelihood_ratio(evidence)
        
        # 计算后验几率
        posterior_odds = prior_odds * likelihood_ratio
        
        # 转换为概率（防止除零）
        posterior_prob = posterior_odds / max(1.0, 1 + posterior_odds)
        
        # 限制范围
        return max(0.01, min(0.99, posterior_prob))

    
    def _calculate_likelihood_ratio(self, evidence: Dict[str, Any]) -> float:
        """
        计算似然比 - 证据在狼人和好人中的出现概率比
        
        Likelihood_Ratio = P(Evidence|Wolf) / P(Evidence|Good)
        """
        ratio = 1.0
        
        # 1. 注入攻击证据
        if evidence.get('injection_detected'):
            # 狼人注入概率 vs 好人注入概率 = 0.7 / 0.1 = 7
            ratio *= 7.0
        
        # 2. 虚假引用证据
        if evidence.get('false_quote_detected'):
            # 狼人虚假引用 vs 好人虚假引用 = 0.6 / 0.15 = 4
            ratio *= 4.0
        
        # 3. 投票准确度证据
        vote_accuracy = evidence.get('vote_accuracy')
        if vote_accuracy is not None:
            if vote_accuracy < 0.3:
                # 低准确度更可能是狼人
                ratio *= 3.0
            elif vote_accuracy > 0.7:
                # 高准确度更可能是好人
                ratio *= 0.3
        
        # 4. 发言质量证据
        speech_quality = evidence.get('speech_quality')
        if speech_quality is not None:
            if speech_quality < 30:
                # 低质量发言
                ratio *= 2.0
            elif speech_quality > 70:
                # 高质量发言
                ratio *= 0.5
        
        # 5. 矛盾证据
        contradiction_count = evidence.get('contradictions', 0)
        if contradiction_count > 0:
            ratio *= (1.5 ** contradiction_count)
        
        # 6. 角色声称证据
        if evidence.get('fake_role_claim'):
            # 虚假角色声称强烈指向狼人
            ratio *= 10.0
        
        # 7. 预言家验证证据（最强证据）
        seer_result = evidence.get('seer_result')
        if seer_result == 'wolf':
            ratio *= 50.0  # 预言家验出狼人
        elif seer_result == 'good':
            ratio *= 0.02  # 预言家验出好人
        
        return ratio
    
    def infer_role(
        self,
        player: str,
        context: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        推断玩家角色
        
        Returns:
            (角色, 置信度)
        """
        player_data = context.get('player_data', {}).get(player, {})
        
        # 1. 预言家验证（最高优先级）
        seer_checks = context.get('seer_checks', {})
        if player in seer_checks:
            result = seer_checks[player]
            if isinstance(result, dict):
                is_wolf = result.get('is_wolf', False)
                return ('wolf' if is_wolf else 'good', 0.95)
            elif isinstance(result, str):
                is_wolf = 'wolf' in result.lower()
                return ('wolf' if is_wolf else 'good', 0.95)
        
        # 2. 角色声称 + 行为验证
        if player_data.get('claimed_seer') and player_data.get('seer_checks'):
            # 声称预言家且有验人记录
            return ('seer', 0.8)
        
        if player_data.get('claimed_witch') and player_data.get('potion_used'):
            # 声称女巫且使用过药
            return ('witch', 0.8)
        
        if player_data.get('claimed_guard'):
            return ('guard', 0.7)
        
        if player_data.get('claimed_hunter'):
            return ('hunter', 0.7)
        
        # 3. 贝叶斯推断狼人概率
        evidence = {
            'injection_detected': player_data.get('injection_attempts', 0) > 0,
            'false_quote_detected': player_data.get('false_quotes', 0) > 0,
            'vote_accuracy': player_data.get('vote_accuracy', 0.5),
            'speech_quality': player_data.get('llm_analysis', {}).get('overall_score', 50),
            'contradictions': player_data.get('contradictions', 0),
            'fake_role_claim': player_data.get('fake_role_claim', False)
        }
        
        wolf_prob = self.update_wolf_probability(player, 0.33, evidence)
        
        if wolf_prob > 0.7:
            return ('wolf', wolf_prob)
        elif wolf_prob < 0.3:
            return ('villager', 1 - wolf_prob)
        else:
            return ('unknown', 0.5)


class SkillDecisionEngine:
    """技能决策引擎 - 用于预言家/女巫/守卫/猎人的技能使用决策"""
    
    def __init__(self, ml_agent=None):
        self.ml_agent = ml_agent
        self.bayesian_engine = BayesianInferenceEngine()
        logger.info("✓ SkillDecisionEngine initialized")
    
    def decide_seer_check(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        预言家验人决策
        
        优先级：
        1. 高怀疑度玩家
        2. 关键位置玩家（警长候选）
        3. 发言模糊玩家
        
        Returns:
            (目标玩家, 理由)
        """
        if not candidates:
            return None, "无可验证玩家"
        
        scores = {}
        trust_scores = context.get('trust_scores', {})
        player_data = context.get('player_data', {})
        
        for candidate in candidates:
            score = 0.0
            data = player_data.get(candidate, {})
            
            # 1. 怀疑度（信任分数低）
            trust = trust_scores.get(candidate, 50)
            if trust < 40:
                score += 60
            elif trust < 50:
                score += 30
            
            # 2. 关键位置
            if data.get('is_sheriff'):
                score += 50  # 警长优先验证
            elif data.get('sheriff_candidate'):
                score += 35
            
            # 3. 发言模糊
            if 'llm_analysis' in data:
                logic_score = data['llm_analysis'].get('logic_score', 50)
                if logic_score < 40:
                    score += 25
            
            # 4. 行为异常
            if data.get('injection_attempts', 0) > 0:
                score += 40
            
            scores[candidate] = score
        
        target = max(scores, key=scores.get)
        reason = self._generate_check_reason(target, scores[target], context)
        
        return target, reason
    
    def _generate_check_reason(
        self,
        target: str,
        score: float,
        context: Dict
    ) -> str:
        """生成验人理由"""
        trust_scores = context.get('trust_scores', {})
        trust = trust_scores.get(target, 50)
        
        if trust < 30:
            return f"{target}信任度极低，需要验证身份"
        elif score > 80:
            return f"{target}行为高度可疑，优先验证"
        else:
            return f"{target}发言模糊，需要确认身份"
    
    def decide_witch_save(
        self,
        victim: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        女巫救人决策
        
        Returns:
            (是否救, 理由)
        """
        if not victim:
            return False, "无死亡玩家"
        
        trust_scores = context.get('trust_scores', {})
        player_data = context.get('player_data', {})
        current_day = context.get('current_day', 1)
        
        trust = trust_scores.get(victim, 50)
        data = player_data.get(victim, {})
        
        # 决策逻辑
        should_save = False
        reason = ""
        
        # 1. 第一晚不救（保留解药）
        if current_day == 1:
            should_save = False
            reason = "第一晚保留解药"
        
        # 2. 高信任玩家
        elif trust > 70:
            should_save = True
            reason = f"{victim}信任度高，值得救"
        
        # 3. 关键角色
        elif data.get('claimed_seer') or data.get('is_sheriff'):
            should_save = True
            reason = f"{victim}是关键角色，必须救"
        
        # 4. 自己
        elif victim == context.get('my_name'):
            should_save = True
            reason = "救自己"
        
        else:
            should_save = False
            reason = f"{victim}信任度不足，不救"
        
        return should_save, reason
    
    def decide_witch_poison(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], str]:
        """
        女巫毒人决策
        
        Returns:
            (目标玩家, 理由)
        """
        if not candidates:
            return None, "无可毒玩家"
        
        # 使用增强决策引擎
        engine = EnhancedDecisionEngine(self.ml_agent)
        target, confidence, scores = engine.decide_vote(
            candidates, context, game_phase="midgame"
        )
        
        # 只有高置信度才毒
        if confidence > 0.7:
            return target, f"{target}狼人概率极高（置信度{confidence:.2f}），使用毒药"
        else:
            return None, f"没有高置信度目标，保留毒药"
    
    def decide_guard_protect(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        守卫守护决策
        
        Returns:
            (目标玩家, 理由)
        """
        if not candidates:
            return None, "无可守护玩家"
        
        scores = {}
        trust_scores = context.get('trust_scores', {})
        player_data = context.get('player_data', {})
        
        for candidate in candidates:
            score = 0.0
            data = player_data.get(candidate, {})
            trust = trust_scores.get(candidate, 50)
            
            # 1. 高信任度
            if trust > 70:
                score += 50
            elif trust > 60:
                score += 30
            
            # 2. 关键角色
            if data.get('claimed_seer'):
                score += 60  # 预言家优先守护
            elif data.get('is_sheriff'):
                score += 40
            
            # 3. 被狼人关注
            mentioned = data.get('mentioned_by_wolves', 0)
            if mentioned > 0:
                score += 30
            
            scores[candidate] = score
        
        target = max(scores, key=scores.get)
        reason = f"{target}是关键玩家，需要守护"
        
        return target, reason
    
    def decide_hunter_shoot(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        猎人开枪决策
        
        Returns:
            (目标玩家, 理由)
        """
        if not candidates:
            return None, "无可开枪目标"
        
        # 使用增强决策引擎
        engine = EnhancedDecisionEngine(self.ml_agent)
        target, confidence, scores = engine.decide_vote(
            candidates, context, game_phase="endgame"  # 开枪通常在残局
        )
        
        reason = f"{target}狼人概率最高（置信度{confidence:.2f}），开枪带走"
        
        return target, reason
