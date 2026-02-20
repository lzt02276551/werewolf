# 实施计划: 角色代理继承重构

## 概述

本实施计划将设计文档中的继承重构方案转化为可执行的编码任务。重构将创建 `BaseGoodAgent` 基类来统一管理好人阵营角色的共享功能，同时保持每个角色的特有能力。

## 任务列表

- [ ] 1. 创建 BaseGoodAgent 基类和配置
  - [ ] 1.1 创建 BaseGoodConfig 配置类
    - 在 `werewolf/core/base_good_config.py` 创建配置类
    - 定义所有共享配置项（检测器、信任分数、ML、发言、决策配置）
    - 使用 dataclass 装饰器
    - _Requirements: 3.1, 4.3_
  
  - [ ] 1.2 创建 BaseGoodAgent 基类骨架
    - 在 `werewolf/core/base_good_agent.py` 创建基类
    - 继承 BasicRoleAgent
    - 定义核心属性（config, detection_client, ml_agent, 各种组件）
    - 实现 __init__ 方法调用各初始化方法
    - _Requirements: 1.1, 3.1_
  
  - [ ] 1.3 实现基类内存变量初始化
    - 实现 _init_memory_variables() 方法
    - 初始化 player_data, game_state, trust_scores, voting_results 等
    - 设计为可被子类覆盖扩展
    - _Requirements: 3.3_
  
  - [ ] 1.4 实现检测客户端初始化
    - 实现 _init_detection_client() 方法
    - 从环境变量读取 DETECTION_MODEL_NAME
    - 创建独立的 OpenAI 客户端用于检测
    - 添加错误处理和降级逻辑
    - _Requirements: 3.5_

  - [ ] 1.5 实现 ML 增强初始化
    - 实现 _init_ml_enhancement() 方法
    - 初始化 LightweightMLAgent
    - 配置增量学习系统
    - 添加错误处理和降级逻辑（ML 失败不影响运行）
    - _Requirements: 3.4_
  
  - [ ] 1.6 实现共享组件初始化
    - 实现 _init_shared_components() 方法
    - 初始化检测器（InjectionDetector, FalseQuoteDetector, MessageParser, SpeechQualityEvaluator）
    - 初始化分析器（TrustScoreManager, TrustScoreCalculator, VotingPatternAnalyzer, GamePhaseAnalyzer）
    - 初始化决策器（VoteDecisionMaker, SheriffElectionDecisionMaker, SheriffVoteDecisionMaker）
    - 每个组件添加错误处理
    - _Requirements: 3.1, 3.5_
  
  - [ ] 1.7 实现钩子方法
    - 实现 _init_specific_components() 空方法（由子类覆盖）
    - 添加文档说明子类如何使用此钩子
    - _Requirements: 3.2_
  
  - [ ]* 1.8 编写 BaseGoodAgent 单元测试
    - 测试配置类创建和验证
    - 测试基类初始化
    - 测试所有组件正确初始化
    - 测试内存变量正确设置
    - _Requirements: 1.1, 3.1_

- [ ] 2. 实现 BaseGoodAgent 共享方法
  - [ ] 2.1 实现消息处理方法
    - 实现 _process_player_message(message, player_name) 方法
    - 集成注入检测逻辑
    - 集成虚假引用检测逻辑
    - 集成消息解析逻辑
    - 更新信任分数
    - 添加错误处理，确保单个检测失败不影响整体
    - _Requirements: 1.2_

  - [ ] 2.2 实现投票决策方法
    - 实现 _make_vote_decision(candidates) 方法
    - 构建决策上下文
    - 调用 vote_decision_maker
    - 添加回退决策机制
    - 添加错误处理
    - _Requirements: 1.2_
  
  - [ ] 2.3 实现上下文构建方法
    - 实现 _build_context() 方法
    - 收集 player_data, game_state, trust_scores, voting_results 等
    - 返回统一的上下文字典
    - _Requirements: 1.2_
  
  - [ ] 2.4 实现工具方法
    - 实现 _truncate_output(text, max_length) 方法
    - 实现 _validate_player_name(output, valid_choices) 方法
    - 实现 _extract_player_names(text) 方法（如果需要）
    - _Requirements: 1.2_
  
  - [ ]* 2.5 编写共享方法单元测试
    - 测试 _process_player_message 正确处理各种消息
    - 测试 _make_vote_decision 返回有效候选人
    - 测试 _build_context 返回完整上下文
    - 测试工具方法的边界情况
    - _Requirements: 1.2_
  
  - [ ]* 2.6 编写属性测试：共享方法可访问性
    - **Property 2: 共享方法可访问性**
    - **Validates: Requirements 1.2**
    - 对所有好人角色，验证共享方法可访问且可调用
    - 使用 hypothesis 生成随机角色
    - _Requirements: 1.2_

- [ ] 3. 检查点 - 基类完成验证
  - 确保所有基类测试通过
  - 确认基类可以独立实例化（作为 Villager）
  - 询问用户是否有问题

- [ ] 4. 重构 VillagerAgent（平民）
  - [ ] 4.1 修改 VillagerAgent 继承关系
    - 修改 `werewolf/villager/villager_agent.py`
    - 将继承从 BasicRoleAgent 改为 BaseGoodAgent
    - 移除所有与基类重复的属性定义
    - 移除所有与基类重复的方法实现
    - 保留 VillagerAgent 特有的逻辑（如果有）
    - _Requirements: 1.2, 1.7_
  
  - [ ] 4.2 简化 VillagerAgent 初始化
    - 简化 __init__ 方法，调用 super().__init__
    - 移除重复的组件初始化代码
    - 实现 _init_specific_components() 为空方法（平民无特有组件）
    - _Requirements: 1.2, 3.2_
  
  - [ ] 4.3 更新 VillagerConfig
    - 修改 VillagerConfig 继承 BaseGoodConfig
    - 移除重复的配置项
    - 保留平民特有配置（如果有）
    - _Requirements: 4.3_
  
  - [ ]* 4.4 运行 VillagerAgent 测试
    - 运行现有的平民测试用例
    - 验证所有测试通过
    - 验证功能完全一致
    - _Requirements: 1.7, 4.1_
  
  - [ ]* 4.5 编写属性测试：平民继承正确性
    - **Property 3: 好人角色继承正确性**
    - **Validates: Requirements 1.2**
    - 验证 VillagerAgent 继承自 BaseGoodAgent
    - 验证可以访问所有共享方法
    - _Requirements: 1.2, 1.7_

- [ ] 5. 重构 SeerAgent（预言家）
  - [ ] 5.1 修改 SeerAgent 继承关系
    - 修改 `werewolf/seer/seer_agent.py`
    - 将继承从 BasicRoleAgent 改为 BaseGoodAgent
    - 移除所有与基类重复的属性和方法
    - 保留预言家特有的验人功能
    - _Requirements: 1.3, 1.7_

  - [ ] 5.2 实现预言家特有组件初始化
    - 覆盖 _init_memory_variables() 添加 checked_players, night_count
    - 实现 _init_specific_components() 初始化预言家组件
    - 初始化 CheckDecisionMaker, CheckPriorityCalculator, WolfProbabilityEstimator
    - _Requirements: 1.3, 3.2_
  
  - [ ] 5.3 保留预言家特有方法
    - 保留 _handle_check() 方法
    - 保留 _handle_skill_result() 方法
    - 确保这些方法使用基类的共享功能
    - _Requirements: 1.3_
  
  - [ ] 5.4 更新 SeerConfig
    - 修改 SeerConfig 继承 BaseGoodConfig
    - 添加预言家特有配置（CHECK_PRIORITY_STRATEGY, REVEAL_IDENTITY_THRESHOLD）
    - _Requirements: 4.3_
  
  - [ ]* 5.5 运行 SeerAgent 测试
    - 运行现有的预言家测试用例
    - 验证验人功能正常
    - 验证所有测试通过
    - _Requirements: 1.3, 1.7, 4.1_
  
  - [ ]* 5.6 编写属性测试：预言家继承和功能
    - **Property 3: 好人角色继承正确性**
    - **Validates: Requirements 1.3**
    - 验证 SeerAgent 继承自 BaseGoodAgent
    - 验证预言家特有方法存在
    - 验证验人功能正常工作
    - _Requirements: 1.3, 1.7_

- [ ] 6. 重构 WitchAgent（女巫）
  - [ ] 6.1 修改 WitchAgent 继承关系
    - 修改 `werewolf/witch/witch_agent.py`
    - 将继承从 BasicRoleAgent 改为 BaseGoodAgent
    - 移除所有与基类重复的属性和方法
    - 保留女巫特有的药水功能
    - _Requirements: 1.4, 1.7_

  - [ ] 6.2 实现女巫特有组件初始化
    - 覆盖 _init_memory_variables() 添加 has_antidote, has_poison, saved_players, poisoned_players
    - 实现 _init_specific_components() 初始化女巫组件
    - 初始化 PotionManager, SaveDecisionMaker, PoisonDecisionMaker
    - _Requirements: 1.4, 3.2_
  
  - [ ] 6.3 保留女巫特有方法
    - 保留 _handle_save() 方法
    - 保留 _handle_poison() 方法
    - 确保这些方法使用基类的共享功能
    - _Requirements: 1.4_
  
  - [ ] 6.4 更新 WitchConfig
    - 修改 WitchConfig 继承 BaseGoodConfig
    - 添加女巫特有配置（SAVE_STRATEGY, POISON_STRATEGY, SAVE_SELF_ALLOWED）
    - _Requirements: 4.3_
  
  - [ ]* 6.5 运行 WitchAgent 测试
    - 运行现有的女巫测试用例
    - 验证药水管理功能正常
    - 验证所有测试通过
    - _Requirements: 1.4, 1.7, 4.1_
  
  - [ ]* 6.6 编写属性测试：女巫继承和功能
    - **Property 3: 好人角色继承正确性**
    - **Validates: Requirements 1.4**
    - 验证 WitchAgent 继承自 BaseGoodAgent
    - 验证女巫特有方法存在
    - 验证药水功能正常工作
    - _Requirements: 1.4, 1.7_

- [ ] 7. 重构 GuardAgent（守卫）
  - [ ] 7.1 修改 GuardAgent 继承关系
    - 修改 `werewolf/guard/guard_agent.py`
    - 将继承从 BasicRoleAgent 改为 BaseGoodAgent
    - 移除所有与基类重复的属性和方法
    - 保留守卫特有的守护功能
    - _Requirements: 1.5, 1.7_

  - [ ] 7.2 实现守卫特有组件初始化
    - 覆盖 _init_memory_variables() 添加 protect_history, last_protected
    - 实现 _init_specific_components() 初始化守卫组件
    - 初始化 ProtectDecisionMaker, ProtectValidator
    - _Requirements: 1.5, 3.2_
  
  - [ ] 7.3 保留守卫特有方法
    - 保留 _handle_protect() 方法
    - 保留 _select_alternative_protect_target() 方法
    - 确保守护规则正确（不能连续守护同一人）
    - _Requirements: 1.5_
  
  - [ ] 7.4 更新 GuardConfig
    - 修改 GuardConfig 继承 BaseGoodConfig
    - 添加守卫特有配置（PROTECT_STRATEGY, PROTECT_SELF_ALLOWED）
    - _Requirements: 4.3_
  
  - [ ]* 7.5 运行 GuardAgent 测试
    - 运行现有的守卫测试用例
    - 验证守护功能正常
    - 验证守护规则正确
    - 验证所有测试通过
    - _Requirements: 1.5, 1.7, 4.1_
  
  - [ ]* 7.6 编写属性测试：守卫继承和功能
    - **Property 3: 好人角色继承正确性**
    - **Validates: Requirements 1.5**
    - 验证 GuardAgent 继承自 BaseGoodAgent
    - 验证守卫特有方法存在
    - 验证守护功能正常工作
    - _Requirements: 1.5, 1.7_

- [ ] 8. 重构 HunterAgent（猎人）
  - [ ] 8.1 修改 HunterAgent 继承关系
    - 修改 `werewolf/hunter/hunter_agent.py`
    - 将继承从 BasicRoleAgent 改为 BaseGoodAgent
    - 移除所有与基类重复的属性和方法
    - 保留猎人特有的开枪功能
    - _Requirements: 1.6, 1.7_

  - [ ] 8.2 实现猎人特有组件初始化
    - 覆盖 _init_memory_variables() 添加 can_shoot, death_cause
    - 实现 _init_specific_components() 初始化猎人组件
    - 初始化 ShootDecisionMaker, ThreatAnalyzer, WolfProbCalculator
    - _Requirements: 1.6, 3.2_
  
  - [ ] 8.3 保留猎人特有方法
    - 保留 _handle_shoot() 方法
    - 保留 _update_death_cause() 方法
    - 确保开枪规则正确（被毒死不能开枪）
    - _Requirements: 1.6_
  
  - [ ] 8.4 更新 HunterConfig
    - 修改 HunterConfig 继承 BaseGoodConfig
    - 添加猎人特有配置（SHOOT_STRATEGY, SHOOT_THRESHOLD）
    - _Requirements: 4.3_
  
  - [ ]* 8.5 运行 HunterAgent 测试
    - 运行现有的猎人测试用例
    - 验证开枪功能正常
    - 验证开枪规则正确
    - 验证所有测试通过
    - _Requirements: 1.6, 1.7, 4.1_
  
  - [ ]* 8.6 编写属性测试：猎人继承和功能
    - **Property 3: 好人角色继承正确性**
    - **Validates: Requirements 1.6**
    - 验证 HunterAgent 继承自 BaseGoodAgent
    - 验证猎人特有方法存在
    - 验证开枪功能正常工作
    - _Requirements: 1.6, 1.7_

- [ ] 9. 检查点 - 所有角色重构完成
  - 确保所有角色测试通过
  - 运行完整的测试套件
  - 询问用户是否有问题

- [ ] 10. 验证狼人阵营继承结构
  - [ ] 10.1 验证 WolfKingAgent 继承关系
    - 检查 WolfKingAgent 正确继承 WolfAgent
    - 验证狼王可以访问狼人的所有方法
    - 验证狼王的开枪功能正常
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 10.2 编写属性测试：狼人继承结构
    - **Property 6: 狼人阵营继承结构**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    - 验证 WolfKingAgent 继承自 WolfAgent
    - 验证所有 WolfAgent 方法可访问
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 11. 编写综合属性测试
  - [ ]* 11.1 编写属性测试：BaseGoodAgent 结构完整性
    - **Property 1: BaseGoodAgent 类结构完整性**
    - **Validates: Requirements 1.1, 3.1**
    - 对所有好人角色，验证所有共享组件已初始化
    - 使用 hypothesis 生成随机角色
    - _Requirements: 1.1, 3.1_
  
  - [ ]* 11.2 编写属性测试：组件初始化一致性
    - **Property 5: 组件初始化模式一致性**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    - 对所有好人角色，验证初始化模式一致
    - 验证共享组件、内存变量、ML、检测器都已初始化
    - 使用 hypothesis 生成随机角色和消息
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ]* 11.3 编写属性测试：角色特有功能隔离性
    - **Property 9: 角色特有功能隔离性**
    - **Validates: Requirements 1.3, 1.4, 1.5, 1.6**
    - 验证角色特有方法只存在于特定角色类
    - 验证 BaseGoodAgent 不包含角色特有方法
    - _Requirements: 1.3, 1.4, 1.5, 1.6_
  
  - [ ]* 11.4 编写属性测试：配置继承正确性
    - **Property 10: 配置继承正确性**
    - **Validates: Requirements 3.1, 4.3**
    - 对所有角色配置类，验证继承自 BaseGoodConfig
    - 验证基础配置值可访问
    - _Requirements: 3.1, 4.3_

- [ ] 12. 集成测试和回归测试
  - [ ]* 12.1 运行完整测试套件
    - **Property 7: 测试套件兼容性**
    - **Validates: Requirements 4.1**
    - 运行所有现有测试用例
    - 验证100%通过率
    - _Requirements: 4.1_

  - [ ]* 12.2 编写集成测试：完整游戏场景
    - **Property 4: 功能保持不变**
    - **Validates: Requirements 1.7, 4.2, 4.3, 4.4**
    - 创建完整游戏场景测试
    - 使用所有重构后的角色
    - 验证游戏可以正常进行
    - 验证所有角色功能正常
    - _Requirements: 1.7, 4.2, 4.3, 4.4_
  
  - [ ]* 12.3 性能基准测试
    - **Property 8: 性能保持稳定**
    - **Validates: Requirements 4.5**
    - 测试各角色初始化时间
    - 测试消息处理时间
    - 测试决策时间
    - 对比重构前后性能，确保变化 < ±5%
    - _Requirements: 4.5_

- [ ] 13. 代码质量和文档
  - [ ] 13.1 代码审查和优化
    - 检查所有代码符合 PEP 8 规范
    - 优化性能瓶颈（如果有）
    - 确保错误处理完善
    - 确保日志记录清晰
    - _Requirements: 1.7, 4.5_
  
  - [ ] 13.2 完善文档字符串
    - 为 BaseGoodAgent 添加详细文档字符串
    - 为所有公共方法添加文档字符串
    - 为钩子方法添加使用说明
    - 为配置类添加说明
    - _Requirements: 1.1, 3.1_
  
  - [ ] 13.3 更新架构文档
    - 更新系统架构文档，说明新的继承结构
    - 更新 API 文档
    - 创建"如何添加新角色"指南
    - _Requirements: 1.1_
  
  - [ ] 13.4 创建示例代码
    - 创建使用 BaseGoodAgent 的示例
    - 创建添加新角色的示例
    - 创建自定义配置的示例
    - _Requirements: 1.1, 3.2_

- [ ] 14. 最终验证和部署准备
  - [ ] 14.1 最终集成测试
    - 在测试环境运行完整游戏
    - 验证所有角色正常工作
    - 验证游戏逻辑完全一致
    - _Requirements: 1.7, 4.4_

  - [ ] 14.2 验证成功指标
    - 验证代码重复率降低 > 50%
    - 验证代码行数减少 > 30%
    - 验证测试覆盖率保持 > 80%
    - 验证所有测试通过率 = 100%
    - 验证性能变化 < ±5%
    - _Requirements: 1.7, 4.1, 4.5_
  
  - [ ] 14.3 准备发布说明
    - 编写重构说明文档
    - 列出主要变更
    - 说明向后兼容性
    - 提供迁移指南（如果需要）
    - _Requirements: 4.2, 4.3_
  
  - [ ] 14.4 团队评审
    - 进行代码评审
    - 进行设计评审
    - 收集团队反馈
    - 解决遗留问题
    - _Requirements: 1.1_

- [ ] 15. 检查点 - 最终验收
  - 确保所有任务完成
  - 确保所有测试通过
  - 确保文档完整
  - 询问用户是否可以合并代码

## 注意事项

- 标记 `*` 的任务是可选的测试任务，可以跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号，便于追溯
- 检查点任务确保增量验证，及时发现问题
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况
- 集成测试验证整体功能

## 预期成果

完成所有任务后，将实现：

1. **BaseGoodAgent 基类**: 包含所有好人角色的共享功能
2. **5个重构后的角色**: Villager, Seer, Witch, Guard, Hunter 都继承基类
3. **代码减少约48%**: 从 ~5300 行减少到 ~2750 行
4. **100%功能保持**: 所有角色功能完全不变
5. **完整测试覆盖**: 单元测试 + 属性测试 + 集成测试
6. **完善文档**: 架构文档、API 文档、使用指南

## 估计时间

- 阶段1（任务1-3）: 创建基类 - 1天
- 阶段2（任务4-8）: 重构子类 - 2天
- 阶段3（任务9-12）: 测试验证 - 1天
- 阶段4（任务13-15）: 文档和发布 - 1天

总计: 5天
