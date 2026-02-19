"""
阶段三：强化学习/模仿学习
目标：学习"玩家视角"的最优博弈策略
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
import numpy as np
import logging
from collections import deque
from .stage2_supervised import IdentityDetector

logger = logging.getLogger(__name__)


class WerewolfEnv:
    """狼人杀游戏环境"""
    
    def __init__(self, identity_detector, num_players=12):
        self.identity_detector = identity_detector
        self.num_players = num_players
        
        # 游戏状态
        self.alive_players = []
        self.dead_players = []
        self.roles = {}
        self.current_round = 0
        self.current_phase = 'night'
        
        # 历史记录
        self.speech_history = []
        self.vote_history = []
        
    def reset(self):
        """重置游戏"""
        # 随机分配身份
        roles = ['wolf'] * 4 + ['seer', 'witch', 'guard', 'hunter'] + ['villager'] * 4
        np.random.shuffle(roles)
        
        self.alive_players = list(range(self.num_players))
        self.dead_players = []
        self.roles = {i: roles[i] for i in range(self.num_players)}
        self.current_round = 0
        self.current_phase = 'night'
        
        self.speech_history = []
        self.vote_history = []
        
        return self.get_state(player_id=0)
    
    def get_state(self, player_id):
        """获取玩家视角的状态"""
        state = {
            'player_id': player_id,
            'my_role': self.roles[player_id],
            'alive_players': self.alive_players.copy(),
            'dead_players': self.dead_players.copy(),
            'current_round': self.current_round,
            'current_phase': self.current_phase,
            'speech_history': self.speech_history[-20:],  # 最近20条发言
            'vote_history': self.vote_history[-10:],  # 最近10次投票
            
            # 使用IdentityDetector评估其他玩家
            'identity_estimates': self.estimate_identities(player_id)
        }
        
        return state
    
    def estimate_identities(self, player_id):
        """使用IdentityDetector评估其他玩家身份"""
        estimates = {}
        
        for other_id in self.alive_players:
            if other_id == player_id:
                continue
            
            # 提取该玩家的行为数据
            player_data = self.extract_player_data(other_id)
            
            # 使用IdentityDetector预测
            with torch.no_grad():
                wolf_prob = self.identity_detector.predict(player_data)
            
            estimates[other_id] = {
                'wolf_probability': wolf_prob,
                'trust_score': 1 - wolf_prob
            }
        
        return estimates
    
    def step(self, player_id, action):
        """执行动作"""
        # 解析动作
        action_type = action['type']  # 'speech', 'vote', 'skill'
        action_target = action.get('target', None)
        action_content = action.get('content', '')
        
        # 执行动作
        if action_type == 'speech':
            self.speech_history.append({
                'player_id': player_id,
                'content': action_content,
                'round': self.current_round
            })
        
        elif action_type == 'vote':
            self.vote_history.append({
                'voter': player_id,
                'target': action_target,
                'round': self.current_round
            })
        
        elif action_type == 'skill':
            self.execute_skill(player_id, action_target)
        
        # 推进游戏
        done, winner = self.check_game_end()
        
        # 计算奖励
        reward = self.calculate_reward(player_id, done, winner)
        
        # 获取新状态
        next_state = self.get_state(player_id)
        
        return next_state, reward, done, {'winner': winner}
    
    def calculate_reward(self, player_id, done, winner):
        """计算奖励（优化：缓存角色查询，使用集合加速查找）"""
        player_role = self.roles[player_id]
        wolf_roles = {'wolf', 'wolf_king'}
        is_wolf = player_role in wolf_roles
        
        if not done:
            # 中间奖励（可选）
            reward = 0
            
            # 成功骗过IdentityDetector
            if is_wolf:
                identity_estimates = self.estimate_identities(player_id)
                if identity_estimates.get(player_id, {}).get('wolf_probability', 0.5) < 0.3:
                    reward += 5  # 伪装成功
            
            # 成功识别狼人
            if not is_wolf:
                # 检查最近的投票是否投中狼人（优化：只检查最后一次投票）
                if self.vote_history:
                    last_vote = self.vote_history[-1]
                    if last_vote.get('voter') == player_id:
                        target = last_vote.get('target')
                        if target is not None and self.roles.get(target) in wolf_roles:
                            reward += 10  # 投中狼人
            
            return reward
        
        else:
            # 终局奖励
            player_faction = 'wolf' if is_wolf else 'good'
            
            if winner == player_faction:
                return 100  # 胜利
            else:
                return -100  # 失败
    
    def check_game_end(self):
        """检查游戏是否结束（优化：使用集合加速角色查找）"""
        wolf_roles = {'wolf', 'wolf_king'}
        wolves_alive = sum(1 for p in self.alive_players if self.roles[p] in wolf_roles)
        goods_alive = len(self.alive_players) - wolves_alive
        
        if wolves_alive == 0:
            return True, 'good'
        elif wolves_alive >= goods_alive:
            return True, 'wolf'
        else:
            return False, None
    
    def extract_player_data(self, player_id):
        """提取该玩家的行为数据（优化：减少重复过滤，使用集合加速查找）"""
        # 从历史记录中提取真实数据（一次遍历完成）
        player_speeches = []
        player_votes = []
        wolf_roles = {'wolf', 'wolf_king'}
        
        for s in self.speech_history:
            if s.get('player_id', -1) == player_id:
                player_speeches.append(s)
        
        for v in self.vote_history:
            if v.get('voter', -1) == player_id:
                player_votes.append(v)
        
        # 计算统计特征
        speech_count = len(player_speeches)
        vote_count = len(player_votes)
        
        # 计算投票准确度（简化版）
        vote_accuracy = 0.5  # 默认值
        if vote_count > 0:
            # 检查投票目标是否为狼人（优化：使用集合，并检查None）
            correct_votes = 0
            for v in player_votes:
                target = v.get('target')
                if target is not None and self.roles.get(target) in wolf_roles:
                    correct_votes += 1
            # 安全的除法，vote_count已经检查过 > 0
            vote_accuracy = float(correct_votes) / float(vote_count)
        
        # 计算夜间存活率
        night_survival_rate = 1.0 if player_id in self.alive_players else 0.0
        
        # 确保speech_lengths不为空（修复：提供合理的默认值）
        if speech_count > 0:
            # 使用实际发言内容长度
            speech_lengths = [len(str(s.get('content', ''))) for s in player_speeches]
            # 如果所有发言都是空的，提供默认值
            if not speech_lengths or all(l == 0 for l in speech_lengths):
                speech_lengths = [100]
        else:
            speech_lengths = [100]
        
        # 提取投票目标（优化：列表推导）
        vote_targets = [v.get('target', -1) for v in player_votes]
        
        # 计算被提及次数（优化：使用str转换一次）
        player_id_str = str(player_id)
        mentioned_count = sum(1 for s in self.speech_history 
                            if player_id_str in str(s.get('content', '')))
        
        return {
            'trust_score': 50 + (vote_accuracy - 0.5) * 40,  # 基于投票准确度
            'vote_accuracy': vote_accuracy,
            'contradiction_count': max(0, 3 - speech_count),  # 发言少可能矛盾多
            'injection_attempts': 0,
            'false_quotation_count': 0,
            'speech_lengths': speech_lengths,
            'voting_speed_avg': 5.0,
            'vote_targets': vote_targets,
            'mentions_others_count': speech_count * 2,
            'mentioned_by_others_count': mentioned_count,
            'aggressive_score': 0.5,
            'defensive_score': 0.5,
            'emotion_keyword_count': speech_count,
            'logic_keyword_count': speech_count * 2,
            'night_survival_rate': night_survival_rate,
            'alliance_strength': 0.5,
            'isolation_score': 0.5,
            'speech_consistency_score': 0.7 if speech_count > 2 else 0.5,
            'avg_response_time': 5.0
        }
    
    def execute_skill(self, player_id, target):
        """执行技能"""
        # 实现略
        pass


class PolicyNetwork(nn.Module):
    """策略网络（Actor）"""
    
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super().__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )
    
    def forward(self, state):
        logits = self.network(state)
        return F.softmax(logits, dim=-1)


class ValueNetwork(nn.Module):
    """价值网络（Critic）"""
    
    def __init__(self, state_dim, hidden_dim=256):
        super().__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, state):
        return self.network(state)


class RLAgent(nn.Module):
    """强化学习智能体"""
    
    def __init__(self, state_dim, action_dim):
        super().__init__()
        
        # 策略网络
        self.policy_net = PolicyNetwork(state_dim, action_dim)
        
        # 价值网络
        self.value_net = ValueNetwork(state_dim)
        
        # 优化器
        self.policy_optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=3e-4)
        self.value_optimizer = torch.optim.Adam(self.value_net.parameters(), lr=1e-3)
    
    def get_action(self, state):
        """选择动作（带探索机制）"""
        state_tensor = self.encode_state(state)
        
        # 策略网络输出动作概率
        action_probs = self.policy_net(state_tensor)
        
        # 使用Categorical分布统一处理（包括探索）
        dist = Categorical(action_probs)
        
        # Epsilon-greedy探索
        epsilon = 0.1  # 10%的探索率
        if np.random.random() < epsilon:
            # 随机探索：使用均匀分布
            uniform_probs = torch.ones_like(action_probs) / action_probs.size(-1)
            explore_dist = Categorical(uniform_probs)
            action = explore_dist.sample()
            # 使用原始策略分布计算log_prob（用于PPO更新）
            log_prob = dist.log_prob(action)
        else:
            # 根据策略采样
            action = dist.sample()
            log_prob = dist.log_prob(action)
        
        return action.item(), log_prob
    
    def get_value(self, state):
        """评估状态价值"""
        state_tensor = self.encode_state(state)
        # 确保state_tensor是正确的形状
        if state_tensor.dim() == 1:
            state_tensor = state_tensor.unsqueeze(0)
        value = self.value_net(state_tensor)
        return value.squeeze()
    
    def encode_state(self, state):
        """编码状态为向量（优化：使用numpy批量构建，减少append操作）"""
        # 预分配数组（25维）
        features = np.zeros(25, dtype=np.float32)
        
        try:
            # 基础信息 (3维) - 使用安全的归一化
            features[0] = min(state.get('player_id', 0) / 12.0, 1.0)
            features[1] = min(state.get('current_round', 0) / 10.0, 1.0)
            alive_count = len(state.get('alive_players', []))
            features[2] = alive_count / 12.0 if alive_count > 0 else 0.0
            
            # 身份估计 (12维) - 向量化操作
            identity_estimates = state.get('identity_estimates', {})
            for i in range(12):
                features[3 + i] = identity_estimates.get(i, {}).get('wolf_probability', 0.5)
            
            # 历史信息 (2维) - 限制最大值避免超出范围
            speech_hist_len = len(state.get('speech_history', []))
            vote_hist_len = len(state.get('vote_history', []))
            features[15] = min(speech_hist_len / 100.0, 1.0)
            features[16] = min(vote_hist_len / 50.0, 1.0)
            
            # 我的角色信息 (7维 - one-hot编码)
            role_map = {'wolf': 0, 'wolf_king': 1, 'seer': 2, 'witch': 3, 'guard': 4, 'hunter': 5, 'villager': 6}
            my_role = state.get('my_role', 'villager')
            my_role_idx = role_map.get(my_role, 6)  # 默认为villager
            
            # 安全的one-hot编码（确保索引有效）
            role_start_idx = 17
            if 0 <= my_role_idx < 7:
                target_idx = role_start_idx + my_role_idx
                if target_idx < len(features):
                    features[target_idx] = 1.0
                else:
                    # 索引越界保护（理论上不应该发生）
                    logger.error(f"Role encoding index out of bounds: {target_idx}, using default")
                    features[role_start_idx + 6] = 1.0  # 默认villager
            else:
                # 无效角色索引保护
                logger.warning(f"Invalid role: {my_role}, using default villager")
                features[role_start_idx + 6] = 1.0
            
            # 游戏阶段 (1维)
            phase_map = {'night': 0.0, 'day': 0.5, 'vote': 1.0}
            features[24] = phase_map.get(state.get('current_phase', 'day'), 0.5)
        except Exception as e:
            logger.error(f"Error encoding state: {e}")
            # 返回默认特征向量
            features = np.zeros(25, dtype=np.float32)
            features[17] = 1.0  # 默认villager
            features[24] = 0.5  # 默认day
        
        # 总共25维 - 直接从numpy转换为tensor
        return torch.from_numpy(features)


class PPOTrainer:
    """PPO训练器"""
    
    def __init__(self, agent, env, device='cuda'):
        self.agent = agent.to(device)
        self.env = env
        self.device = device
        
        # PPO超参数
        self.gamma = 0.99  # 折扣因子
        self.lambda_gae = 0.95  # GAE参数
        self.epsilon = 0.2  # PPO裁剪参数
        self.ppo_epochs = 4  # PPO更新次数
        self.batch_size = 64
    
    def train(self, num_episodes=100000):
        """训练循环"""
        logger.info("=" * 60)
        logger.info("Training Stage 3: Reinforcement Learning (PPO)")
        logger.info("=" * 60)
        
        for episode in range(num_episodes):
            # 收集轨迹
            trajectory = self.collect_trajectory()
            
            if len(trajectory) == 0:
                logger.warning(f"Episode {episode}: Empty trajectory, skipping")
                continue
            
            # 计算优势函数
            advantages = self.compute_advantages(trajectory)
            
            if advantages.numel() == 0:
                logger.warning(f"Episode {episode}: Empty advantages, skipping")
                continue
            
            # PPO更新
            self.update_ppo(trajectory, advantages)
            
            # 记录
            if episode % 100 == 0:
                # 修复: 添加空列表检查
                if trajectory and len(trajectory) > 0:
                    avg_reward = np.mean([t['reward'] for t in trajectory])
                    logger.info(f"Episode {episode}, Avg Reward: {avg_reward:.2f}, Trajectory Length: {len(trajectory)}")
                else:
                    logger.info(f"Episode {episode}, Empty trajectory")
        
        logger.info("✓ RL training completed")
    
    def collect_trajectory(self, max_steps=200):
        """收集一条轨迹
        
        Args:
            max_steps: 最大步数，防止无限循环（默认200步，约等于一局游戏的合理长度）
        """
        trajectory = []
        
        try:
            state = self.env.reset()
        except Exception as e:
            logger.error(f"Failed to reset environment: {e}")
            return []
        
        done = False
        steps = 0
        
        while not done and steps < max_steps:
            try:
                # 智能体选择动作
                action, log_prob = self.agent.get_action(state)
                value = self.agent.get_value(state)
                
                # 执行动作
                next_state, reward, done, info = self.env.step(0, self.decode_action(action))
                
                # 记录
                trajectory.append({
                    'state': state,
                    'action': action,
                    'log_prob': log_prob,
                    'value': value,
                    'reward': reward,
                    'done': done
                })
                
                state = next_state
                steps += 1
            except Exception as e:
                logger.error(f"Error during trajectory collection at step {steps}: {e}")
                break
        
        if steps >= max_steps:
            logger.warning(f"Trajectory collection reached max steps ({max_steps})")
        
        return trajectory
    
    def compute_advantages(self, trajectory):
        """计算GAE优势函数"""
        if not trajectory or len(trajectory) == 0:
            logger.warning("Empty trajectory in compute_advantages")
            return torch.tensor([], dtype=torch.float32, device=self.device)
        
        try:
            advantages = []
            gae = 0
            
            for t in reversed(range(len(trajectory))):
                if t == len(trajectory) - 1:
                    # 如果是真正的终止状态，next_value为0；否则使用当前value作为估计
                    if trajectory[t]['done']:
                        next_value = 0
                    else:
                        # 轨迹被截断（达到max_steps），使用当前value作为bootstrap
                        next_value = trajectory[t]['value'].item() if torch.is_tensor(trajectory[t]['value']) else trajectory[t]['value']
                else:
                    next_value = trajectory[t + 1]['value'].item() if torch.is_tensor(trajectory[t + 1]['value']) else trajectory[t + 1]['value']
                
                current_value = trajectory[t]['value'].item() if torch.is_tensor(trajectory[t]['value']) else trajectory[t]['value']
                delta = trajectory[t]['reward'] + self.gamma * next_value - current_value
                gae = delta + self.gamma * self.lambda_gae * gae
                advantages.insert(0, gae)
            
            return torch.tensor(advantages, dtype=torch.float32, device=self.device)
        except Exception as e:
            logger.error(f"Error computing advantages: {e}")
            return torch.tensor([], dtype=torch.float32, device=self.device)
    
    def update_ppo(self, trajectory, advantages):
        """PPO更新（优化：批量编码状态，减少重复计算）"""
        if len(trajectory) == 0 or advantages.numel() == 0:
            logger.warning("Empty trajectory or advantages, skipping PPO update")
            return
            
        states = [t['state'] for t in trajectory]
        actions = torch.tensor([t['action'] for t in trajectory], dtype=torch.long, device=self.device)
        
        if len(states) == 0 or len(actions) == 0:
            logger.warning("No states or actions in trajectory, skipping PPO update")
            return
        
        # 确保advantages在正确的设备上
        advantages = advantages.to(self.device)
        
        old_log_probs = torch.stack([t['log_prob'] for t in trajectory])
        values_list = [t['value'].item() if torch.is_tensor(t['value']) else t['value'] for t in trajectory]
        returns = advantages + torch.tensor(values_list, dtype=torch.float32)
        
        # 标准化优势
        if advantages.numel() > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # 批量编码所有状态（避免在每个epoch重复编码）
        state_tensors = torch.stack([self.agent.encode_state(state) for state in states])
        
        # PPO更新多次
        for _ in range(self.ppo_epochs):
            # 批量计算动作概率和价值（优化：一次前向传播）
            action_probs = self.agent.policy_net(state_tensors)
            values = self.agent.value_net(state_tensors).squeeze()
            
            # 计算log概率
            dist = Categorical(action_probs)
            new_log_probs = dist.log_prob(actions)
            
            # 重要性采样比率
            ratio = torch.exp(new_log_probs - old_log_probs)
            
            # PPO裁剪目标
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.epsilon, 1 + self.epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # 价值函数损失
            value_loss = F.mse_loss(values, returns)
            
            # 更新策略网络
            self.agent.policy_optimizer.zero_grad()
            policy_loss.backward(retain_graph=True)  # 保留计算图，因为values也需要梯度
            torch.nn.utils.clip_grad_norm_(self.agent.policy_net.parameters(), 0.5)
            self.agent.policy_optimizer.step()
            
            # 更新价值网络（需要重新计算values以避免计算图问题）
            self.agent.value_optimizer.zero_grad()
            # 重新前向传播获取values（避免使用已经backward过的tensor）
            values_fresh = self.agent.value_net(state_tensors).squeeze()
            value_loss_fresh = F.mse_loss(values_fresh, returns)
            value_loss_fresh.backward()
            torch.nn.utils.clip_grad_norm_(self.agent.value_net.parameters(), 0.5)
            self.agent.value_optimizer.step()
    
    def decode_action(self, action_id):
        """解码动作"""
        # 简化实现
        return {
            'type': 'vote',
            'target': action_id % 12
        }
    
    def save_model(self, path):
        """保存模型"""
        torch.save({
            'policy_state_dict': self.agent.policy_net.state_dict(),
            'value_state_dict': self.agent.value_net.state_dict(),
        }, path)
        logger.info(f"✓ Model saved to {path}")


class ImitationLearner:
    """模仿学习"""
    
    def __init__(self, agent, device='cuda'):
        self.agent = agent.to(device)
        self.device = device
        
        self.optimizer = torch.optim.Adam(self.agent.policy_net.parameters(), lr=1e-4)
    
    def train(self, expert_trajectories, epochs=10):
        """从高手对局中学习"""
        logger.info("=" * 60)
        logger.info("Training Stage 3: Imitation Learning")
        logger.info("=" * 60)
        
        if not expert_trajectories:
            logger.warning("No expert trajectories provided, skipping imitation learning")
            return
        
        for epoch in range(epochs):
            total_loss = 0
            batch_count = 0
            
            for trajectory in expert_trajectories:
                states = trajectory.get('states', [])
                actions = trajectory.get('actions', [])
                
                if not states or not actions or len(states) != len(actions):
                    logger.warning("Invalid trajectory format, skipping")
                    continue
                
                for state, expert_action in zip(states, actions):
                    # 预测动作
                    state_tensor = self.agent.encode_state(state)
                    if state_tensor.dim() == 1:
                        state_tensor = state_tensor.unsqueeze(0)
                    action_probs = self.agent.policy_net(state_tensor)
                    
                    # 交叉熵损失
                    expert_action_tensor = torch.tensor([expert_action], dtype=torch.long, device=self.device)
                    loss = F.cross_entropy(action_probs, expert_action_tensor)
                    
                    # 反向传播
                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()
                    
                    total_loss += loss.item()
                    batch_count += 1
            
            avg_loss = total_loss / batch_count if batch_count > 0 else 0
            logger.info(f"Epoch {epoch+1}/{epochs}, Imitation Loss: {avg_loss:.4f}")
        
        logger.info("✓ Imitation learning completed")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    logger.info("Stage 3: Reinforcement Learning / Imitation Learning")
    logger.info("Building Werewolf Agent...")
    
    # 加载IdentityDetector
    # identity_detector = IdentityDetector.load('./ml_golden_path/models/identity_detector.pt')
    
    # 创建环境
    # env = WerewolfEnv(identity_detector)
    
    # 创建智能体
    # agent = RLAgent(state_dim=25, action_dim=100)
    
    # 方法A：模仿学习
    # imitation_learner = ImitationLearner(agent)
    # imitation_learner.train(expert_trajectories, epochs=10)
    
    # 方法B：强化学习
    # ppo_trainer = PPOTrainer(agent, env)
    # ppo_trainer.train(num_episodes=100000)
    
    # 保存
    # ppo_trainer.save_model('./ml_golden_path/models/werewolf_agent.pt')
    
    logger.info("✓ Stage 3 training pipeline ready")
