#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理人代码清理和修复计划执行脚本

此脚本用于自动化执行代码清理和修复任务
"""

import os
import sys
from pathlib import Path

class CodeCleanupPlan:
    """代码清理计划执行器"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.issues_found = []
        self.fixes_applied = []
        
    def check_file_exists(self, filepath):
        """检查文件是否存在"""
        full_path = self.root_dir / filepath
        return full_path.exists()
    
    def check_file_usage(self, filepath, search_pattern):
        """检查文件是否被使用（通过搜索导入语句）"""
        # 搜索所有Python文件中是否导入了该文件
        import_patterns = [
            f"from {filepath.replace('/', '.').replace('.py', '')} import",
            f"import {filepath.replace('/', '.').replace('.py', '')}"
        ]
        
        for py_file in self.root_dir.rglob("*.py"):
            if py_file.name == filepath.split('/')[-1]:
                continue  # 跳过文件自身
            
            try:
                content = py_file.read_text(encoding='utf-8')
                for pattern in import_patterns:
                    if pattern in content:
                        return True, str(py_file)
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
        
        return False, None
    
    def analyze_dead_code(self):
        """分析死代码"""
        print("=" * 80)
        print("阶段1: 死代码分析")
        print("=" * 80)
        
        # 需要检查的可疑文件列表
        suspicious_files = [
            "werewolf/guard/validators.py",
            "werewolf/guard/exceptions.py",
            "werewolf/hunter/game_state.py",
            "werewolf/seer/ml_integration.py",
            "werewolf/witch/analyzers.py",
            "werewolf/wolf/base_components.py",
            "werewolf/wolf/decision_engine.py",
        ]
        
        for filepath in suspicious_files:
            if not self.check_file_exists(filepath):
                print(f"⚠️  文件不存在: {filepath}")
                continue
            
            is_used, used_in = self.check_file_usage(filepath, "")
            if not is_used:
                self.issues_found.append({
                    'type': 'dead_code',
                    'file': filepath,
                    'severity': 'high',
                    'description': f'文件 {filepath} 未被任何其他文件导入'
                })
                print(f"🔴 死代码: {filepath} (未被导入)")
            else:
                print(f"✅ 使用中: {filepath} (被 {used_in} 使用)")
    
    def analyze_component_usage(self):
        """分析组件使用情况"""
        print("\n" + "=" * 80)
        print("阶段2: 组件使用情况分析")
        print("=" * 80)
        
        # 检查各代理人的组件初始化
        agents = [
            ("werewolf/guard/guard_agent.py", "GuardAgent"),
            ("werewolf/hunter/hunter_agent.py", "HunterAgent"),
            ("werewolf/seer/seer_agent.py", "SeerAgent"),
            ("werewolf/villager/villager_agent.py", "VillagerAgent"),
            ("werewolf/witch/witch_agent.py", "WitchAgent"),
            ("werewolf/wolf/wolf_agent.py", "WolfAgent"),
            ("werewolf/wolf_king/wolf_king_agent.py", "WolfKingAgent"),
        ]
        
        for agent_file, agent_name in agents:
            if not self.check_file_exists(agent_file):
                print(f"⚠️  代理人文件不存在: {agent_file}")
                continue
            
            try:
                content = (self.root_dir / agent_file).read_text(encoding='utf-8')
                
                # 检查是否有_init_specific_components方法
                if "_init_specific_components" in content:
                    print(f"✅ {agent_name}: 有特有组件初始化方法")
                else:
                    print(f"⚠️  {agent_name}: 缺少特有组件初始化方法")
                
                # 检查是否正确继承基类
                if "BaseGoodAgent" in content or "BaseWolfAgent" in content:
                    print(f"✅ {agent_name}: 正确继承基类")
                else:
                    print(f"🔴 {agent_name}: 未正确继承基类")
                    self.issues_found.append({
                        'type': 'inheritance',
                        'file': agent_file,
                        'severity': 'critical',
                        'description': f'{agent_name} 未正确继承基类'
                    })
            
            except Exception as e:
                print(f"❌ 读取 {agent_file} 失败: {e}")
    
    def analyze_prompt_code_consistency(self):
        """分析提示词与代码的一致性"""
        print("\n" + "=" * 80)
        print("阶段3: 提示词与代码一致性分析")
        print("=" * 80)
        
        # 检查每个代理人的提示词文件和代码文件
        agents = [
            ("guard", "守卫"),
            ("hunter", "猎人"),
            ("seer", "预言家"),
            ("villager", "平民"),
            ("witch", "女巫"),
            ("wolf", "狼人"),
            ("wolf_king", "狼王"),
        ]
        
        for agent_dir, agent_name_cn in agents:
            prompt_file = f"werewolf/{agent_dir}/prompt.py"
            agent_file = f"werewolf/{agent_dir}/{agent_dir}_agent.py"
            
            if not self.check_file_exists(prompt_file):
                print(f"⚠️  {agent_name_cn}: 提示词文件不存在")
                continue
            
            if not self.check_file_exists(agent_file):
                print(f"⚠️  {agent_name_cn}: 代理人文件不存在")
                continue
            
            try:
                prompt_content = (self.root_dir / prompt_file).read_text(encoding='utf-8')
                agent_content = (self.root_dir / agent_file).read_text(encoding='utf-8')
                
                # 检查关键功能是否在代码中实现
                key_features = {
                    "guard": ["守护", "guard", "protect", "first_night"],
                    "hunter": ["开枪", "shoot", "hunter", "threat"],
                    "seer": ["验人", "check", "seer", "priority"],
                    "villager": ["投票", "vote", "injection", "trust"],
                    "witch": ["解药", "毒药", "antidote", "poison"],
                    "wolf": ["击杀", "kill", "disguise", "teammate"],
                    "wolf_king": ["开枪", "shoot", "wolf_king", "leadership"],
                }
                
                features = key_features.get(agent_dir, [])
                missing_features = []
                
                for feature in features:
                    if feature in prompt_content.lower() and feature not in agent_content.lower():
                        missing_features.append(feature)
                
                if missing_features:
                    print(f"⚠️  {agent_name_cn}: 提示词中的功能可能未在代码中实现: {missing_features}")
                    self.issues_found.append({
                        'type': 'missing_feature',
                        'file': agent_file,
                        'severity': 'medium',
                        'description': f'{agent_name_cn} 可能缺少功能: {missing_features}'
                    })
                else:
                    print(f"✅ {agent_name_cn}: 提示词与代码基本一致")
            
            except Exception as e:
                print(f"❌ 分析 {agent_name_cn} 失败: {e}")
    
    def generate_cleanup_script(self):
        """生成清理脚本"""
        print("\n" + "=" * 80)
        print("阶段4: 生成清理脚本")
        print("=" * 80)
        
        if not self.issues_found:
            print("✅ 未发现需要清理的问题")
            return
        
        cleanup_script = []
        cleanup_script.append("#!/bin/bash")
        cleanup_script.append("# 自动生成的代码清理脚本")
        cleanup_script.append("# 生成时间: $(date)")
        cleanup_script.append("")
        
        # 按严重程度分组
        critical_issues = [i for i in self.issues_found if i['severity'] == 'critical']
        high_issues = [i for i in self.issues_found if i['severity'] == 'high']
        medium_issues = [i for i in self.issues_found if i['severity'] == 'medium']
        
        if critical_issues:
            cleanup_script.append("# ========== 严重问题 (需要立即修复) ==========")
            for issue in critical_issues:
                cleanup_script.append(f"# {issue['description']}")
                cleanup_script.append(f"# 文件: {issue['file']}")
                cleanup_script.append("")
        
        if high_issues:
            cleanup_script.append("# ========== 高优先级问题 (建议删除死代码) ==========")
            for issue in high_issues:
                if issue['type'] == 'dead_code':
                    cleanup_script.append(f"# 删除死代码: {issue['file']}")
                    cleanup_script.append(f"# rm {issue['file']}")
                    cleanup_script.append(f"# git rm {issue['file']}")
                    cleanup_script.append("")
        
        if medium_issues:
            cleanup_script.append("# ========== 中优先级问题 (需要验证) ==========")
            for issue in medium_issues:
                cleanup_script.append(f"# {issue['description']}")
                cleanup_script.append(f"# 文件: {issue['file']}")
                cleanup_script.append("")
        
        # 写入清理脚本
        script_path = self.root_dir / "auto_cleanup.sh"
        script_path.write_text("\n".join(cleanup_script), encoding='utf-8')
        print(f"✅ 清理脚本已生成: {script_path}")
    
    def generate_report(self):
        """生成详细报告"""
        print("\n" + "=" * 80)
        print("最终报告")
        print("=" * 80)
        
        print(f"\n发现的问题总数: {len(self.issues_found)}")
        
        if self.issues_found:
            print("\n问题详情:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"\n{i}. [{issue['severity'].upper()}] {issue['type']}")
                print(f"   文件: {issue['file']}")
                print(f"   描述: {issue['description']}")
        else:
            print("\n✅ 未发现严重问题，代码质量良好！")
        
        print("\n" + "=" * 80)
        print("建议:")
        print("1. 查看生成的 auto_cleanup.sh 脚本")
        print("2. 手动验证标记为死代码的文件")
        print("3. 执行清理脚本前先备份代码")
        print("4. 运行测试确保清理后功能正常")
        print("=" * 80)
    
    def run(self):
        """执行完整的分析流程"""
        print("开始代码清理和修复计划分析...")
        print()
        
        self.analyze_dead_code()
        self.analyze_component_usage()
        self.analyze_prompt_code_consistency()
        self.generate_cleanup_script()
        self.generate_report()
        
        print("\n分析完成！")
        return len(self.issues_found)


if __name__ == "__main__":
    planner = CodeCleanupPlan()
    issues_count = planner.run()
    sys.exit(0 if issues_count == 0 else 1)
