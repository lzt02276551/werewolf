"""
Bayesian Network for Probabilistic Inference
贝叶斯网络：概率推理框架
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    from pgmpy.models import BayesianNetwork
    from pgmpy.factors.discrete import TabularCPD
    from pgmpy.inference import VariableElimination
    PGMPY_AVAILABLE = True
except ImportError:
    logger.warning("pgmpy not available, using simplified Bayesian inference")
    PGMPY_AVAILABLE = False


if PGMPY_AVAILABLE:
    class WolfInferenceBayesian:
        """基于贝叶斯网络的狼人推理"""
        
        def __init__(self):
            # 定义网络结构
            # IsWolf -> VotingPattern, SpeechStyle, NightBehavior
            # VotingPattern -> TrustScore
            # SpeechStyle -> ContradictionCount
            self.model = BayesianNetwork([
                ('IsWolf', 'VotingPattern'),
                ('IsWolf', 'SpeechStyle'),
                ('IsWolf', 'NightBehavior'),
                ('VotingPattern', 'TrustScore'),
                ('SpeechStyle', 'ContradictionCount'),
                ('IsWolf', 'InjectionAttack')
            ])
            
            self._define_cpds()
            self.inference = None
            
            logger.info("WolfInferenceBayesian initialized with pgmpy")
        
        def _define_cpds(self):
            """定义条件概率分布"""
            
            # P(IsWolf) - 先验概率
            cpd_is_wolf = TabularCPD(
                variable='IsWolf',
                variable_card=2,
                values=[[0.67], [0.33]]  # 67%好人, 33%狼人
            )
            
            # P(VotingPattern | IsWolf)
            cpd_voting = TabularCPD(
                variable='VotingPattern',
                variable_card=3,  # 0=accurate, 1=protecting, 2=random
                values=[
                    [0.7, 0.1],  # accurate
                    [0.1, 0.7],  # protecting wolves
                    [0.2, 0.2]   # random
                ],
                evidence=['IsWolf'],
                evidence_card=[2]
            )
            
            # P(SpeechStyle | IsWolf)
            cpd_speech = TabularCPD(
                variable='SpeechStyle',
                variable_card=3,  # 0=logical, 1=emotional, 2=defensive
                values=[
                    [0.6, 0.2],  # logical
                    [0.2, 0.3],  # emotional
                    [0.2, 0.5]   # defensive
                ],
                evidence=['IsWolf'],
                evidence_card=[2]
            )
            
            # P(NightBehavior | IsWolf)
            cpd_night = TabularCPD(
                variable='NightBehavior',
                variable_card=2,  # 0=killed, 1=survived
                values=[
                    [0.3, 0.9],  # killed (good players more likely killed)
                    [0.7, 0.1]   # survived
                ],
                evidence=['IsWolf'],
                evidence_card=[2]
            )
            
            # P(TrustScore | VotingPattern)
            cpd_trust = TabularCPD(
                variable='TrustScore',
                variable_card=3,  # 0=low, 1=medium, 2=high
                values=[
                    [0.1, 0.7, 0.4],  # low
                    [0.3, 0.2, 0.4],  # medium
                    [0.6, 0.1, 0.2]   # high
                ],
                evidence=['VotingPattern'],
                evidence_card=[3]
            )
            
            # P(ContradictionCount | SpeechStyle)
            cpd_contradiction = TabularCPD(
                variable='ContradictionCount',
                variable_card=3,  # 0=low, 1=medium, 2=high
                values=[
                    [0.7, 0.3, 0.1],  # low
                    [0.2, 0.4, 0.3],  # medium
                    [0.1, 0.3, 0.6]   # high
                ],
                evidence=['SpeechStyle'],
                evidence_card=[3]
            )
            
            # P(InjectionAttack | IsWolf)
            cpd_injection = TabularCPD(
                variable='InjectionAttack',
                variable_card=2,  # 0=no, 1=yes
                values=[
                    [0.95, 0.4],  # no injection
                    [0.05, 0.6]   # injection detected
                ],
                evidence=['IsWolf'],
                evidence_card=[2]
            )
            
            # 添加CPD到模型
            self.model.add_cpds(
                cpd_is_wolf, cpd_voting, cpd_speech, cpd_night,
                cpd_trust, cpd_contradiction, cpd_injection
            )
            
            # 验证模型
            if not self.model.check_model():
                raise ValueError("Bayesian model validation failed")
            
            # 创建推理引擎
            self.inference = VariableElimination(self.model)
        
        def infer_wolf_probability(self, evidence):
            """
            给定证据推理狼人概率
            
            Args:
                evidence: 证据字典，例如：
                    {
                        'VotingPattern': 1,  # protecting wolves
                        'SpeechStyle': 2,    # defensive
                        'TrustScore': 0,     # low
                        'InjectionAttack': 1 # yes
                    }
            
            Returns:
                float: P(IsWolf=1 | evidence)
            """
            if self.inference is None:
                logger.warning("Inference engine not initialized")
                return 0.5
            
            try:
                result = self.inference.query(
                    variables=['IsWolf'],
                    evidence=evidence
                )
                wolf_prob = result.values[1]  # P(IsWolf=1)
                
                logger.debug(f"Bayesian inference - Evidence: {evidence}, "
                           f"Wolf prob: {wolf_prob:.3f}")
                
                return wolf_prob
            except Exception as e:
                logger.error(f"Inference failed: {e}")
                return 0.5
        
        def encode_evidence(self, player_data):
            """
            将玩家数据编码为贝叶斯网络证据
            
            Args:
                player_data: 玩家数据字典
            
            Returns:
                dict: 编码后的证据
            """
            evidence = {}
            
            # 投票模式
            vote_accuracy = player_data.get('vote_accuracy', 0.5)
            if vote_accuracy > 0.6:
                evidence['VotingPattern'] = 0  # accurate
            elif vote_accuracy < 0.4:
                evidence['VotingPattern'] = 1  # protecting wolves
            else:
                evidence['VotingPattern'] = 2  # random
            
            # 发言风格
            logic_score = player_data.get('logic_keyword_count', 5)
            emotion_score = player_data.get('emotion_keyword_count', 5)
            defensive_score = player_data.get('defensive_score', 0.5)
            
            if logic_score > 10:
                evidence['SpeechStyle'] = 0  # logical
            elif emotion_score > 8:
                evidence['SpeechStyle'] = 1  # emotional
            elif defensive_score > 0.6:
                evidence['SpeechStyle'] = 2  # defensive
            else:
                # 默认为逻辑型（如果都不满足条件）
                evidence['SpeechStyle'] = 0
            
            # 夜间行为
            night_survival_rate = player_data.get('night_survival_rate', 0.5)
            if night_survival_rate > 0.7:
                evidence['NightBehavior'] = 1  # survived
            else:
                evidence['NightBehavior'] = 0  # killed
            
            # 信任分数
            trust_score = player_data.get('trust_score', 50)
            if trust_score > 60:
                evidence['TrustScore'] = 2  # high
            elif trust_score > 40:
                evidence['TrustScore'] = 1  # medium
            else:
                evidence['TrustScore'] = 0  # low
            
            # 矛盾次数
            contradiction_count = player_data.get('contradiction_count', 0)
            if contradiction_count > 3:
                evidence['ContradictionCount'] = 2  # high
            elif contradiction_count > 1:
                evidence['ContradictionCount'] = 1  # medium
            else:
                evidence['ContradictionCount'] = 0  # low
            
            # 注入攻击
            injection_attempts = player_data.get('injection_attempts', 0)
            evidence['InjectionAttack'] = 1 if injection_attempts > 0 else 0
            
            return evidence

else:
    # Fallback: 简化的贝叶斯推理
    class WolfInferenceBayesian:
        """简化的贝叶斯推理（不依赖pgmpy）"""
        
        def __init__(self):
            # 先验概率
            self.prior_wolf = 0.33
            self.prior_good = 0.67
            
            logger.info("WolfInferenceBayesian initialized (simplified version)")
        
        def infer_wolf_probability(self, evidence):
            """简化的贝叶斯推理（使用对数空间避免溢出）"""
            import math
            
            # 先验（对数空间）
            log_p_wolf = math.log(self.prior_wolf)
            log_p_good = math.log(self.prior_good)
            
            # 对数似然比
            log_likelihood_ratio = 0.0
            
            # 投票模式
            if 'VotingPattern' in evidence:
                if evidence['VotingPattern'] == 1:  # protecting wolves
                    log_likelihood_ratio += math.log(7.0)
                elif evidence['VotingPattern'] == 0:  # accurate
                    log_likelihood_ratio += math.log(0.14)
            
            # 发言风格
            if 'SpeechStyle' in evidence:
                if evidence['SpeechStyle'] == 2:  # defensive
                    log_likelihood_ratio += math.log(2.5)
                elif evidence['SpeechStyle'] == 0:  # logical
                    log_likelihood_ratio += math.log(0.33)
            
            # 注入攻击
            if 'InjectionAttack' in evidence and evidence['InjectionAttack'] == 1:
                log_likelihood_ratio += math.log(12.0)
            
            # 信任分数
            if 'TrustScore' in evidence:
                if evidence['TrustScore'] == 0:  # low
                    log_likelihood_ratio += math.log(7.0)
                elif evidence['TrustScore'] == 2:  # high
                    log_likelihood_ratio += math.log(0.17)
            
            # 后验概率（对数空间）- 使用数值稳定的计算方式
            log_numerator = log_likelihood_ratio + log_p_wolf
            a = log_numerator
            b = log_p_good
            
            # 使用数值稳定的logsumexp计算
            # log(exp(a) + exp(b)) = max(a,b) + log(1 + exp(-|a-b|))
            max_val = max(a, b)
            
            # 提前检查极端情况，避免不必要的计算
            diff = abs(a - b)
            if diff > 20:  # 差值过大，直接返回结果
                return 0.999 if a > b else 0.001
            
            try:
                # 使用log1p提高数值稳定性
                if a > b:
                    log_denominator = a + math.log1p(math.exp(b - a))
                else:
                    log_denominator = b + math.log1p(math.exp(a - b))
                
                # 计算最终概率
                log_diff = log_numerator - log_denominator
                
                # 使用expm1提高小值精度，或直接exp
                if -1 < log_diff < 1:
                    # 对于接近0的值，使用更精确的计算
                    p_wolf_given_evidence = math.expm1(log_diff) + 1
                else:
                    p_wolf_given_evidence = math.exp(log_diff)
                
                # 检查结果有效性
                if not (0 <= p_wolf_given_evidence <= 1) or math.isnan(p_wolf_given_evidence):
                    logger.warning(f"Invalid probability: {p_wolf_given_evidence}, using fallback")
                    return 0.999 if log_diff > 0 else 0.001
                
                # 限制在合理范围内
                return max(0.001, min(0.999, p_wolf_given_evidence))
                
            except (OverflowError, ValueError, ArithmeticError) as e:
                logger.debug(f"Numerical error in Bayesian inference: {e}, using approximation")
                # 根据符号返回近似值
                return 0.999 if a > b else 0.001
        
        def encode_evidence(self, player_data):
            """编码证据（优化：减少重复的get调用，使用局部变量缓存）"""
            evidence = {}
            
            # 缓存常用值
            vote_accuracy = player_data.get('vote_accuracy', 0.5)
            logic_score = player_data.get('logic_keyword_count', 5)
            emotion_score = player_data.get('emotion_keyword_count', 5)
            defensive_score = player_data.get('defensive_score', 0.5)
            trust_score = player_data.get('trust_score', 50)
            
            # 投票模式
            if vote_accuracy > 0.6:
                evidence['VotingPattern'] = 0
            elif vote_accuracy < 0.4:
                evidence['VotingPattern'] = 1
            else:
                evidence['VotingPattern'] = 2
            
            # 发言风格
            if logic_score > 10:
                evidence['SpeechStyle'] = 0
            elif emotion_score > 8:
                evidence['SpeechStyle'] = 1
            elif defensive_score > 0.6:
                evidence['SpeechStyle'] = 2
            else:
                # 默认为逻辑型（如果都不满足条件）
                evidence['SpeechStyle'] = 0
            
            # 信任分数
            if trust_score > 60:
                evidence['TrustScore'] = 2
            elif trust_score > 40:
                evidence['TrustScore'] = 1
            else:
                evidence['TrustScore'] = 0
            
            # 注入攻击
            evidence['InjectionAttack'] = 1 if player_data.get('injection_attempts', 0) > 0 else 0
            
            return evidence


class BayesianAnalyzer:
    """贝叶斯分析器（整合推理引擎）"""
    
    def __init__(self):
        self.bayesian_net = WolfInferenceBayesian()
        logger.info("BayesianAnalyzer initialized")
    
    def analyze_player(self, player_data):
        """
        分析玩家，返回狼人概率
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            float: 狼人概率
        """
        evidence = self.bayesian_net.encode_evidence(player_data)
        wolf_prob = self.bayesian_net.infer_wolf_probability(evidence)
        
        logger.debug(f"Bayesian analysis - Evidence: {evidence}, Wolf prob: {wolf_prob:.3f}")
        
        return wolf_prob
    
    def analyze_batch(self, player_data_list):
        """批量分析 - 优化版本，并行编码和推理"""
        if not player_data_list:
            return []
        
        # 批量编码证据（优化：使用列表推导一次性完成）
        evidence_list = [self.bayesian_net.encode_evidence(data) for data in player_data_list]
        
        # 批量推理（优化：使用列表推导）
        results = [self.bayesian_net.infer_wolf_probability(evidence) for evidence in evidence_list]
        
        return results


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    analyzer = BayesianAnalyzer()
    
    # 测试：好人数据
    good_player = {
        'vote_accuracy': 0.8,
        'logic_keyword_count': 15,
        'emotion_keyword_count': 3,
        'defensive_score': 0.3,
        'trust_score': 70,
        'contradiction_count': 1,
        'injection_attempts': 0,
        'night_survival_rate': 0.4
    }
    
    good_prob = analyzer.analyze_player(good_player)
    print(f"Good player - Wolf probability: {good_prob:.3f}")
    
    # 测试：狼人数据
    wolf_player = {
        'vote_accuracy': 0.3,
        'logic_keyword_count': 5,
        'emotion_keyword_count': 12,
        'defensive_score': 0.8,
        'trust_score': 25,
        'contradiction_count': 5,
        'injection_attempts': 2,
        'night_survival_rate': 0.9
    }
    
    wolf_prob = analyzer.analyze_player(wolf_player)
    print(f"Wolf player - Wolf probability: {wolf_prob:.3f}")
