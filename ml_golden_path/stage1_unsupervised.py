"""
阶段一：无监督/自监督学习
目标：构建狼人杀专业语言模型（WerewolfLM）
"""

import torch
import torch.nn as nn
from transformers import BertModel, BertTokenizer, BertConfig
from torch.utils.data import Dataset, DataLoader
import logging

logger = logging.getLogger(__name__)


class WerewolfSpeechDataset(Dataset):
    """狼人杀发言数据集（无标签）"""
    
    def __init__(self, speeches, tokenizer, max_length=128):
        self.speeches = speeches
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.speeches)
    
    def __getitem__(self, idx):
        speech = self.speeches[idx]
        
        # Tokenize
        encoding = self.tokenizer(
            speech['text'],
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'round': speech.get('round', 0),
            'phase': speech.get('phase', 'discuss')
        }


class WerewolfLM(nn.Module):
    """狼人杀专业语言模型"""
    
    def __init__(self, pretrained_model='bert-base-chinese'):
        super().__init__()
        
        # 基于BERT
        self.bert = BertModel.from_pretrained(pretrained_model)
        
        # MLM头（掩码语言模型）
        self.mlm_head = nn.Linear(self.bert.config.hidden_size, self.bert.config.vocab_size)
        
        # NSP头（下一句预测）
        self.nsp_head = nn.Linear(self.bert.config.hidden_size, 2)
        
        # 对比学习投影头
        self.projection = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
    
    def forward(self, input_ids, attention_mask, task='mlm'):
        # BERT编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        sequence_output = outputs.last_hidden_state  # [batch, seq_len, hidden]
        pooled_output = outputs.pooler_output  # [batch, hidden]
        
        if task == 'mlm':
            # 掩码语言模型
            mlm_logits = self.mlm_head(sequence_output)
            return mlm_logits
        
        elif task == 'nsp':
            # 下一句预测
            nsp_logits = self.nsp_head(pooled_output)
            return nsp_logits
        
        elif task == 'contrastive':
            # 对比学习
            projection = self.projection(pooled_output)
            # L2归一化
            projection = nn.functional.normalize(projection, dim=-1)
            return projection
        
        else:
            return pooled_output


class Stage1Trainer:
    """阶段一训练器"""
    
    def __init__(self, model, device='cuda', tokenizer=None):
        self.model = model.to(device)
        self.device = device
        self.tokenizer = tokenizer  # 保存tokenizer用于mask_tokens
        
        if self.tokenizer is None:
            logger.warning("Tokenizer not provided, mask_tokens will use default BERT Chinese values")
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=5e-5,
            weight_decay=0.01
        )
        
        # 学习率调度
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=10000
        )
    
    def train_mlm(self, dataloader, epochs=10):
        """训练掩码语言模型（优化：添加早停和梯度累积）"""
        logger.info("=" * 60)
        logger.info("Training Stage 1: Masked Language Model")
        logger.info("=" * 60)
        
        if len(dataloader) == 0:
            logger.warning("Empty dataloader, skipping MLM training")
            return
        
        self.model.train()
        best_loss = float('inf')
        patience = 3
        patience_counter = 0
        
        for epoch in range(epochs):
            total_loss = 0
            batch_count = 0
            
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                
                # 随机掩盖15%的token
                masked_input_ids, labels = self.mask_tokens(input_ids)
                
                # 前向传播
                logits = self.model(
                    masked_input_ids,
                    attention_mask,
                    task='mlm'
                )
                
                # 计算损失
                loss = nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)),
                    labels.view(-1),
                    ignore_index=-100
                )
                
                # 反向传播
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                self.scheduler.step()
                
                total_loss += loss.item()
                batch_count += 1
            
            avg_loss = total_loss / batch_count if batch_count > 0 else 0
            logger.info(f"Epoch {epoch+1}/{epochs}, MLM Loss: {avg_loss:.4f}")
            
            # 早停检查
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        logger.info("✓ MLM training completed")
    
    def train_contrastive(self, dataloader, epochs=5):
        """训练对比学习（优化：添加早停）"""
        logger.info("=" * 60)
        logger.info("Training Stage 1: Contrastive Learning")
        logger.info("=" * 60)
        
        if len(dataloader) == 0:
            logger.warning("Empty dataloader, skipping contrastive training")
            return
        
        self.model.train()
        best_loss = float('inf')
        patience = 2
        patience_counter = 0
        
        for epoch in range(epochs):
            total_loss = 0
            batch_count = 0
            
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                
                # 数据增强：创建正例对
                aug_input_ids, aug_attention_mask = self.augment(input_ids, attention_mask)
                
                # 编码
                z1 = self.model(input_ids, attention_mask, task='contrastive')
                z2 = self.model(aug_input_ids, aug_attention_mask, task='contrastive')
                
                # 对比损失（SimCLR）
                loss = self.contrastive_loss(z1, z2, temperature=0.5)
                
                # 反向传播
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                
                total_loss += loss.item()
                batch_count += 1
            
            avg_loss = total_loss / batch_count if batch_count > 0 else 0
            logger.info(f"Epoch {epoch+1}/{epochs}, Contrastive Loss: {avg_loss:.4f}")
            
            # 早停检查
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        logger.info("✓ Contrastive learning completed")
    
    def mask_tokens(self, input_ids, mask_prob=0.15):
        """随机掩盖token"""
        labels = input_ids.clone()
        
        # 随机选择15%的token
        probability_matrix = torch.full(labels.shape, mask_prob, device=input_ids.device)
        masked_indices = torch.bernoulli(probability_matrix).bool()
        
        # 不掩盖特殊token（[CLS], [SEP], [PAD]）
        if self.tokenizer is not None:
            # 使用tokenizer的特殊token
            special_token_ids = [
                self.tokenizer.pad_token_id,
                self.tokenizer.cls_token_id,
                self.tokenizer.sep_token_id
            ]
            mask_token_id = self.tokenizer.mask_token_id
            vocab_size = self.tokenizer.vocab_size
        else:
            # 回退到BERT中文的默认值
            special_token_ids = [0, 101, 102]
            mask_token_id = 103  # BERT中文默认[MASK] token ID
            vocab_size = 21128  # BERT中文词表大小
        
        for token_id in special_token_ids:
            if token_id is not None:
                masked_indices = masked_indices & (input_ids != token_id)
        
        # 80%替换为[MASK]，10%随机替换，10%保持不变
        indices_replaced = torch.bernoulli(torch.full(labels.shape, 0.8, device=input_ids.device)).bool() & masked_indices
        input_ids[indices_replaced] = mask_token_id
        
        indices_random = torch.bernoulli(torch.full(labels.shape, 0.5, device=input_ids.device)).bool() & masked_indices & ~indices_replaced
        random_words = torch.randint(0, vocab_size, labels.shape, dtype=torch.long, device=input_ids.device)
        input_ids[indices_random] = random_words[indices_random]
        
        # 只计算被掩盖token的损失
        labels[~masked_indices] = -100
        
        return input_ids, labels
    
    def augment(self, input_ids, attention_mask):
        """数据增强 - 使用多种策略（优化：减少重复计算，批量操作）"""
        batch_size = input_ids.size(0)
        device = input_ids.device
        
        # 获取词表大小
        if self.tokenizer is not None:
            vocab_size = self.tokenizer.vocab_size
        else:
            vocab_size = 21128  # BERT中文词表大小
        
        # 预生成随机数（批量操作）
        strategy = torch.randint(0, 3, (batch_size,), device=device)
        
        # 策略1: 随机掩码
        aug_input_ids_1, _ = self.mask_tokens(input_ids.clone(), mask_prob=0.15)
        
        # 策略2: Token替换（批量生成）
        aug_input_ids_2 = input_ids.clone()
        replace_mask = torch.rand(input_ids.shape, device=device) < 0.1
        random_tokens = torch.randint(0, vocab_size, input_ids.shape, dtype=torch.long, device=device)
        aug_input_ids_2[replace_mask] = random_tokens[replace_mask]
        
        # 策略3: Token删除（批量操作）
        aug_input_ids_3 = input_ids.clone()
        delete_mask = torch.rand(input_ids.shape, device=device) < 0.1
        aug_input_ids_3[delete_mask] = 0  # PAD token
        
        # 根据策略选择（向量化操作）
        aug_input_ids = torch.where(
            (strategy == 0).unsqueeze(1).expand_as(input_ids),
            aug_input_ids_1,
            torch.where(
                (strategy == 1).unsqueeze(1).expand_as(input_ids),
                aug_input_ids_2,
                aug_input_ids_3
            )
        )
        
        return aug_input_ids, attention_mask
    
    def contrastive_loss(self, z1, z2, temperature=0.5):
        """对比损失（NT-Xent）- 优化：使用更高效的计算方式"""
        batch_size = z1.size(0)
        
        # 拼接
        z = torch.cat([z1, z2], dim=0)  # [2*batch, dim]
        
        # 计算相似度矩阵（优化：使用矩阵乘法）
        sim_matrix = torch.mm(z, z.t()) / temperature  # [2*batch, 2*batch]
        
        # 掩盖对角线（优化：使用fill_diagonal_避免创建mask）
        sim_matrix.fill_diagonal_(-9e15)
        
        # 正例：(i, i+batch) 和 (i+batch, i)
        pos_sim = torch.cat([
            torch.diag(sim_matrix, batch_size),
            torch.diag(sim_matrix, -batch_size)
        ])
        
        # 计算损失（优化：直接计算，减少中间变量）
        loss = (-pos_sim + torch.logsumexp(sim_matrix, dim=1)).mean()
        
        return loss
    
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


def prepare_unsupervised_data(game_logs):
    """从游戏日志中提取纯文本数据（忽略身份标签）"""
    speeches = []
    
    for game in game_logs:
        for round_data in game['rounds']:
            for speech in round_data['speeches']:
                speeches.append({
                    'text': speech['content'],
                    'round': round_data['round_number'],
                    'phase': round_data['phase'],
                    'context': speech.get('context', '')
                })
    
    logger.info(f"Extracted {len(speeches)} speeches for unsupervised learning")
    return speeches


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 示例：训练WerewolfLM
    logger.info("Stage 1: Unsupervised/Self-supervised Learning")
    logger.info("Building Werewolf Language Model...")
    
    # 初始化
    tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
    model = WerewolfLM('bert-base-chinese')
    trainer = Stage1Trainer(model, device='cpu', tokenizer=tokenizer)  # 修复：传入device和tokenizer参数
    
    # 准备数据（示例）
    # speeches = prepare_unsupervised_data(game_logs)
    # dataset = WerewolfSpeechDataset(speeches, tokenizer)
    # dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    # 训练
    # trainer.train_mlm(dataloader, epochs=10)
    # trainer.train_contrastive(dataloader, epochs=5)
    
    # 保存
    # trainer.save_model('./ml_golden_path/models/werewolf_lm.pt')
    
    logger.info("✓ Stage 1 training pipeline ready")
