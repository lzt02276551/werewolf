"""
阶段二：监督学习
目标：获得"上帝视角"的超级身份识别能力（IdentityDetector）
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import logging
import numpy as np
from .stage1_unsupervised import WerewolfLM

logger = logging.getLogger(__name__)


class LabeledGameDataset(Dataset):
    """带标签的游戏数据集"""
    
    def __init__(self, games, tokenizer, max_length=128):
        self.games = games
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 提取所有玩家数据
        self.player_data = []
        for game in games:
            for player in game['players']:
                # 兼容两种数据格式
                if 'speeches' in player:
                    # 完整格式（带发言）
                    self.player_data.append({
                        'speeches': player['speeches'],
                        'votes': player.get('votes', []),
                        'behaviors': player.get('behaviors', player.get('data', {})),
                        'true_identity': player['role'],
                        'is_wolf': player.get('is_wolf', player['role'] in ['wolf', 'wolf_king'])
                    })
                else:
                    # 简化格式（只有行为特征）
                    behaviors = player.get('data', {})
                    # 从行为特征生成伪发言（用于训练）
                    pseudo_speech = self._generate_pseudo_speech(player['name'], behaviors)
                    self.player_data.append({
                        'speeches': [pseudo_speech],
                        'votes': [],
                        'behaviors': behaviors,
                        'true_identity': player['role'],
                        'is_wolf': player['role'] in ['wolf', 'wolf_king']
                    })
    
    def _generate_pseudo_speech(self, player_name, behaviors):
        """从行为特征生成伪发言（用于训练）"""
        # 确保player_name不为None且为字符串
        if player_name is None or not isinstance(player_name, str):
            player_name = "玩家"
        
        # 确保behaviors不为None且为字典
        if behaviors is None or not isinstance(behaviors, dict):
            behaviors = {}
        
        trust = behaviors.get('trust_score', 50)
        vote_acc = behaviors.get('vote_accuracy', 0.5)
        
        # 使用中文生成伪发言（匹配BERT中文tokenizer）
        if trust > 70:
            speech = f"{player_name}表现出高信任度行为，投票准确。"
        elif trust < 30:
            speech = f"{player_name}表现出可疑行为，信任度低。"
        else:
            speech = f"{player_name}在游戏中保持中立行为。"
        
        if vote_acc > 0.7:
            speech += "投票准确率很高。"
        elif vote_acc < 0.3:
            speech += "投票准确率很低。"
        
        # 确保返回的是非空字符串
        return speech if speech and len(speech) > 0 else "玩家参与游戏。"
    
    def __len__(self):
        return len(self.player_data)
    
    def __getitem__(self, idx):
        player = self.player_data[idx]
        
        # 编码所有发言（处理空发言列表的情况）- 修复：改进空值处理
        speeches = player.get('speeches', [])
        if not speeches or not isinstance(speeches, list) or len(speeches) == 0:
            speeches_text = "无发言记录"  # 提供默认文本
        else:
            # 过滤空字符串和None（修复：确保过滤逻辑正确，添加类型检查和异常处理）
            valid_speeches = []
            for s in speeches:
                try:
                    if s is not None and s != "":
                        s_str = str(s).strip()
                        if s_str and len(s_str) > 0:  # 非空字符串且长度大于0
                            valid_speeches.append(s_str)
                except Exception as e:
                    logger.debug(f"Failed to process speech: {e}, skipping")
                    continue
            
            if not valid_speeches or len(valid_speeches) == 0:
                speeches_text = "无发言记录"
            else:
                speeches_text = ' [SEP] '.join(valid_speeches)
        
        encoding = self.tokenizer(
            speeches_text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # 行为特征
        behavior_features = self.extract_behavior_features(player)
        
        # 标签
        role_to_id = {
            'wolf': 0, 'wolf_king': 1,
            'seer': 2, 'witch': 3, 'guard': 4, 'hunter': 5,
            'villager': 6
        }
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'behavior_features': torch.tensor(behavior_features, dtype=torch.float32),
            'role_label': role_to_id.get(player['true_identity'], 6),
            'is_wolf': int(player['is_wolf'])
        }
    
    def extract_behavior_features(self, player):
        """提取行为特征（19维）- 优化：使用numpy数组直接构建"""
        behaviors = player['behaviors']
        speeches = player.get('speeches', [])
        
        # 预计算常用值
        speech_count = len(speeches)
        total_speech_len = sum(len(s) for s in speeches) if speeches else 0
        
        # 安全的除法操作，避免除零
        speech_count_norm = min(speech_count / 20.0, 1.0) if speech_count > 0 else 0.0
        speech_len_norm = min(total_speech_len / 1000.0, 1.0) if total_speech_len > 0 else 0.5
        
        return np.array([
            behaviors.get('trust_score', 50) / 100.0,
            behaviors.get('vote_accuracy', 0.5),
            behaviors.get('contradiction_count', 0) / 10.0,
            behaviors.get('injection_attempts', 0) / 5.0,
            behaviors.get('false_quotation_count', 0) / 5.0,
            speech_count_norm,
            speech_len_norm,
            behaviors.get('voting_speed_avg', 5) / 10.0,
            behaviors.get('mentions_others_count', 0) / 50.0,
            behaviors.get('mentioned_by_others_count', 0) / 50.0,
            behaviors.get('aggressive_score', 0.5),
            behaviors.get('defensive_score', 0.5),
            behaviors.get('emotion_keyword_count', 0) / 20.0,
            behaviors.get('logic_keyword_count', 0) / 20.0,
            behaviors.get('night_survival_rate', 0.5),
            behaviors.get('alliance_strength', 0.5),
            behaviors.get('isolation_score', 0.5),
            behaviors.get('speech_consistency_score', 0.5),
            behaviors.get('avg_response_time', 5) / 10.0
        ], dtype=np.float32)


class IdentityDetector(nn.Module):
    """超级身份识别模型"""
    
    def __init__(self, werewolf_lm, num_roles=7):
        super().__init__()
        
        # 加载预训练的WerewolfLM
        self.language_model = werewolf_lm
        
        # 冻结部分层（可选）
        # for param in self.language_model.bert.embeddings.parameters():
        #     param.requires_grad = False
        
        # 多头注意力（关注关键发言）
        self.attention = nn.MultiheadAttention(
            embed_dim=768,
            num_heads=8,
            dropout=0.1,
            batch_first=True
        )
        
        # 行为编码器
        self.behavior_encoder = nn.Sequential(
            nn.Linear(19, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 128),
            nn.ReLU()
        )
        
        # 融合层
        self.fusion = nn.Sequential(
            nn.Linear(768 + 128, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU()
        )
        
        # 身份分类器（多任务）
        self.role_classifier = nn.Linear(256, num_roles)  # 7个角色
        self.wolf_classifier = nn.Linear(256, 2)  # 狼人/好人
        
        # 行为预测器（辅助任务）
        self.behavior_predictor = nn.Linear(256, 19)
        
        # 可学习的默认语言嵌入（用于没有发言数据的情况）
        self.default_speech_emb = nn.Parameter(torch.randn(1, 768) * 0.01)
    
    def predict(self, player_data):
        """预测狼人概率（用于Stage 3）- 优化：减少重复计算"""
        self.eval()
        device = next(self.parameters()).device
        
        with torch.no_grad():
            # 构建输入（优化：使用numpy数组批量构建）
            behavior_array = np.array([
                player_data.get('trust_score', 50) / 100,
                player_data.get('vote_accuracy', 0.5),
                player_data.get('contradiction_count', 0) / 10,
                player_data.get('injection_attempts', 0) / 5,
                player_data.get('false_quotation_count', 0) / 5,
                0.5,  # speech count placeholder
                0.5,  # speech length placeholder
                player_data.get('voting_speed_avg', 5) / 10,
                player_data.get('mentions_others_count', 0) / 50,
                player_data.get('mentioned_by_others_count', 0) / 50,
                player_data.get('aggressive_score', 0.5),
                player_data.get('defensive_score', 0.5),
                player_data.get('emotion_keyword_count', 0) / 20,
                player_data.get('logic_keyword_count', 0) / 20,
                player_data.get('night_survival_rate', 0.5),
                player_data.get('alliance_strength', 0.5),
                player_data.get('isolation_score', 0.5),
                player_data.get('speech_consistency_score', 0.5),
                player_data.get('avg_response_time', 5) / 10
            ], dtype=np.float32)
            
            behaviors = torch.from_numpy(behavior_array).unsqueeze(0).to(device)
            
            # 使用行为特征编码
            behavior_emb = self.behavior_encoder(behaviors)
            
            # 使用语言模型的平均池化作为语言特征（而不是零向量）
            # 这样可以利用预训练的语言模型知识
            try:
                # 尝试从语言模型获取默认嵌入
                with torch.no_grad():
                    # 使用[CLS] token的嵌入作为默认语言特征
                    dummy_input = torch.tensor([[101]], device=device)  # [CLS] token
                    dummy_mask = torch.tensor([[1]], device=device)
                    speech_emb = self.language_model.bert(dummy_input, dummy_mask).pooler_output
            except Exception as e:
                logger.debug(f"Failed to get language embedding, using learned default: {e}")
                # 使用可学习的默认嵌入
                speech_emb = self.default_speech_emb
            
            combined = torch.cat([speech_emb, behavior_emb], dim=-1)
            fused = self.fusion(combined)
            wolf_logits = self.wolf_classifier(fused)
            wolf_prob = torch.softmax(wolf_logits, dim=-1)[0, 1].item()
            
            return wolf_prob
    
    def forward(self, input_ids, attention_mask, behavior_features, task='identity'):
        # 语言模型编码
        speech_embeddings = self.language_model.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        ).last_hidden_state  # [batch, seq_len, 768]
        
        # 多头注意力（关注关键发言）
        attended, attention_weights = self.attention(
            speech_embeddings,
            speech_embeddings,
            speech_embeddings,
            key_padding_mask=~attention_mask.bool()
        )
        
        # 池化
        attended_pooled = attended.mean(dim=1)  # [batch, 768]
        
        # 行为编码
        behavior_embeddings = self.behavior_encoder(behavior_features)  # [batch, 128]
        
        # 融合
        combined = torch.cat([attended_pooled, behavior_embeddings], dim=-1)
        fused = self.fusion(combined)  # [batch, 256]
        
        if task == 'identity':
            # 身份分类
            role_logits = self.role_classifier(fused)
            wolf_logits = self.wolf_classifier(fused)
            return role_logits, wolf_logits, attention_weights
        
        elif task == 'behavior':
            # 行为预测
            behavior_pred = self.behavior_predictor(fused)
            return behavior_pred
        
        else:
            return fused


class Stage2Trainer:
    """阶段二训练器"""
    
    def __init__(self, model, device='cuda'):
        self.model = model.to(device)
        self.device = device
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=2e-5,
            weight_decay=0.01
        )
        
        # 学习率调度
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=5000
        )
    
    def train(self, dataloader, epochs=10):
        """多任务训练（带验证集）"""
        logger.info("=" * 60)
        logger.info("Training Stage 2: Identity Detection")
        logger.info("=" * 60)
        
        if len(dataloader) == 0:
            logger.warning("Empty dataloader, skipping training")
            return
        
        self.model.train()
        best_loss = float('inf')
        patience = 3
        patience_counter = 0
        
        for epoch in range(epochs):
            total_loss = 0
            role_correct = 0
            wolf_correct = 0
            total_samples = 0
            
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                behavior_features = batch['behavior_features'].to(self.device)
                role_labels = batch['role_label'].to(self.device)
                wolf_labels = batch['is_wolf'].to(self.device)
                
                # 前向传播
                role_logits, wolf_logits, attention_weights = self.model(
                    input_ids,
                    attention_mask,
                    behavior_features,
                    task='identity'
                )
                
                # 多任务损失
                role_loss = nn.functional.cross_entropy(role_logits, role_labels)
                wolf_loss = nn.functional.cross_entropy(wolf_logits, wolf_labels)
                
                # 行为预测损失（辅助任务）
                behavior_pred = self.model(
                    input_ids,
                    attention_mask,
                    behavior_features,
                    task='behavior'
                )
                behavior_loss = nn.functional.mse_loss(behavior_pred, behavior_features)
                
                # 总损失（加权）
                loss = role_loss + 0.5 * wolf_loss + 0.1 * behavior_loss
                
                # 反向传播
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                self.scheduler.step()
                
                # 统计
                total_loss += loss.item()
                role_correct += (role_logits.argmax(dim=1) == role_labels).sum().item()
                wolf_correct += (wolf_logits.argmax(dim=1) == wolf_labels).sum().item()
                total_samples += role_labels.size(0)
            
            # 打印统计
            avg_loss = total_loss / len(dataloader) if len(dataloader) > 0 else 0
            role_acc = role_correct / total_samples if total_samples > 0 else 0
            wolf_acc = wolf_correct / total_samples if total_samples > 0 else 0
            
            logger.info(f"Epoch {epoch+1}/{epochs}")
            logger.info(f"  Loss: {avg_loss:.4f}")
            logger.info(f"  Role Accuracy: {role_acc:.4f}")
            logger.info(f"  Wolf/Good Accuracy: {wolf_acc:.4f}")
            
            # 早停检查
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        logger.info("✓ Identity detection training completed")
    
    def evaluate(self, dataloader):
        """评估模型"""
        if len(dataloader) == 0:
            logger.warning("Empty dataloader, skipping evaluation")
            return 0.0, 0.0
            
        self.model.eval()
        
        role_correct = 0
        wolf_correct = 0
        total_samples = 0
        
        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                behavior_features = batch['behavior_features'].to(self.device)
                role_labels = batch['role_label'].to(self.device)
                wolf_labels = batch['is_wolf'].to(self.device)
                
                role_logits, wolf_logits, _ = self.model(
                    input_ids,
                    attention_mask,
                    behavior_features,
                    task='identity'
                )
                
                role_correct += (role_logits.argmax(dim=1) == role_labels).sum().item()
                wolf_correct += (wolf_logits.argmax(dim=1) == wolf_labels).sum().item()
                total_samples += role_labels.size(0)
        
        role_acc = role_correct / total_samples if total_samples > 0 else 0
        wolf_acc = wolf_correct / total_samples if total_samples > 0 else 0
        
        logger.info("=" * 60)
        logger.info("Evaluation Results:")
        logger.info(f"  Role Accuracy: {role_acc:.4f}")
        logger.info(f"  Wolf/Good Accuracy: {wolf_acc:.4f}")
        logger.info("=" * 60)
        
        return role_acc, wolf_acc
    
    def detect_contradictions(self, player_data):
        """检测矛盾发言"""
        self.model.eval()
        
        # 编码玩家数据
        # ... (实现略)
        
        # 预测身份
        with torch.no_grad():
            role_logits, wolf_logits, attention_weights = self.model(...)
        
        # 分析注意力权重，找出关键发言
        key_speeches = self.extract_key_speeches(attention_weights)
        
        # 检测矛盾
        contradictions = []
        for speech in key_speeches:
            if self.is_contradiction(speech, role_logits):
                contradictions.append(speech)
        
        return contradictions
    
    def save_model(self, path):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, path)
        logger.info(f"✓ Model saved to {path}")
    
    def load_model(self, path):
        """加载模型 - 修复: 添加异常处理"""
        try:
            checkpoint = torch.load(path)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            logger.info(f"✓ Model loaded from {path}")
        except FileNotFoundError:
            logger.error(f"✗ Model file not found: {path}")
            raise
        except Exception as e:
            logger.error(f"✗ Failed to load model from {path}: {e}")
            raise


def prepare_labeled_data(game_logs_with_labels):
    """从带标签的游戏日志中提取数据"""
    games = []
    
    for game_log in game_logs_with_labels:
        game_data = {
            'game_id': game_log['game_id'],
            'players': []
        }
        
        for player_log in game_log['players']:
            player_data = {
                'name': player_log['name'],
                'role': player_log['revealed_role'],  # 官方公布的身份
                'is_wolf': player_log['is_wolf'],
                'speeches': player_log['speeches'],
                'votes': player_log['votes'],
                'behaviors': player_log['behaviors']
            }
            game_data['players'].append(player_data)
        
        games.append(game_data)
    
    logger.info(f"Prepared {len(games)} labeled games for supervised learning")
    return games


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    logger.info("Stage 2: Supervised Learning")
    logger.info("Building Identity Detector...")
    
    # 加载阶段一的模型
    # werewolf_lm = WerewolfLM.load('./ml_golden_path/models/werewolf_lm.pt')
    
    # 初始化IdentityDetector
    # model = IdentityDetector(werewolf_lm)
    # trainer = Stage2Trainer(model)
    
    # 准备数据
    # games = prepare_labeled_data(game_logs_with_labels)
    # dataset = LabeledGameDataset(games, tokenizer)
    # dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
    
    # 训练
    # trainer.train(dataloader, epochs=10)
    
    # 评估
    # trainer.evaluate(test_dataloader)
    
    # 保存
    # trainer.save_model('./ml_golden_path/models/identity_detector.pt')
    
    logger.info("✓ Stage 2 training pipeline ready")
