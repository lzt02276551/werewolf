#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动清理未使用的导入语句

此脚本会自动删除Python文件中未使用的导入语句
"""

import re
from pathlib import Path
from typing import List, Tuple

class UnusedImportCleaner:
    """未使用导入清理器"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.cleaned_files = []
        self.total_removed = 0
        
        # 需要清理的文件和导入列表
        self.cleanup_targets = {
            "werewolf/ml_agent.py": ["np"],
            "werewolf/game_utils.py": ["Optional"],
            "werewolf/game_end_handler.py": ["Optional"],
            "werewolf/guard/trust_manager.py": ["Tuple", "Optional", "InvalidPlayerError", "GuardMemoryError"],
            "werewolf/guard/decision_makers.py": ["Optional"],
            "werewolf/guard/guard_agent.py": ["Optional"],
            "werewolf/guard/analyzers.py": ["Optional", "List"],
            "werewolf/hunter/hunter_agent.py": ["Optional"],
            "werewolf/hunter/analyzers.py": ["re"],
            "werewolf/hunter/detectors.py": ["Dict", "Any"],
            "werewolf/seer/detectors.py": ["Dict", "Any"],
            "werewolf/seer/analyzers.py": ["List", "Tuple", "Optional"],
            "werewolf/seer/decision_makers.py": ["Optional", "re"],
            "werewolf/seer/seer_agent.py": ["Dict", "List"],
            "werewolf/seer/utils.py": ["Optional", "List"],
            "werewolf/villager/villager_agent.py": ["Optional", "List", "Dict", "Any", "Tuple", "Set"],
            "werewolf/villager/analyzers.py": ["Optional", "List"],
            "werewolf/villager/decision_makers.py": ["Optional"],
            "werewolf/witch/base_components.py": ["Optional"],
            "werewolf/witch/witch_agent.py": ["Optional", "List"],
            "werewolf/wolf/config.py": ["Optional", "List"],
            "werewolf/wolf/wolf_agent.py": ["Optional", "List", "Dict", "Any"],
            "werewolf/wolf_king/wolf_king_agent.py": ["Optional", "List", "Dict"],
            "werewolf/core/config.py": ["Optional", "List"],
            "werewolf/core/game_state.py": ["Optional"],
            "werewolf/core/base_components.py": ["Optional", "List"],
            "werewolf/core/base_agent.py": ["Optional", "List"],
            "werewolf/core/agent_adapter.py": ["Optional", "List"],
            "werewolf/core/llm_detectors.py": ["Optional"],
            "werewolf/core/base_wolf_agent.py": ["Optional", "List"],
            "ml_enhanced/ensemble_detector.py": ["Optional"],
            "ml_enhanced/anomaly_detector.py": ["Optional"],
        }
    
    def remove_from_import_line(self, line: str, names_to_remove: List[str]) -> str:
        """从导入行中移除指定的名称"""
        # 处理 from ... import ... 格式
        if line.strip().startswith("from ") and " import " in line:
            parts = line.split(" import ", 1)
            if len(parts) == 2:
                prefix = parts[0]
                imports_part = parts[1]
                
                # 分割导入的名称
                imports = [i.strip() for i in imports_part.split(",")]
                
                # 移除指定的名称
                remaining = [i for i in imports if i.split(" as ")[0].strip() not in names_to_remove]
                
                if not remaining:
                    # 如果所有导入都被移除，返回空字符串
                    return ""
                elif len(remaining) < len(imports):
                    # 重新组合导入行
                    return f"{prefix} import {', '.join(remaining)}\n"
        
        # 处理 import ... 格式
        elif line.strip().startswith("import "):
            import_name = line.strip().replace("import ", "").split(" as ")[0].strip()
            if import_name in names_to_remove:
                return ""
        
        return line
    
    def clean_file(self, filepath: str, names_to_remove: List[str]) -> bool:
        """清理单个文件中的未使用导入"""
        full_path = self.root_dir / filepath
        
        if not full_path.exists():
            print(f"⚠️  文件不存在: {filepath}")
            return False
        
        try:
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 处理每一行
            new_lines = []
            removed_count = 0
            
            for line in lines:
                new_line = self.remove_from_import_line(line, names_to_remove)
                if new_line != line and new_line == "":
                    removed_count += 1
                if new_line:  # 只保留非空行
                    new_lines.append(new_line)
            
            if removed_count > 0:
                # 写回文件
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                self.cleaned_files.append(filepath)
                self.total_removed += removed_count
                print(f"✅ {filepath}: 移除 {removed_count} 个未使用的导入")
                return True
            else:
                print(f"ℹ️  {filepath}: 未找到需要移除的导入")
                return False
        
        except Exception as e:
            print(f"❌ 清理 {filepath} 失败: {e}")
            return False
    
    def run(self):
        """执行清理"""
        print("=" * 80)
        print("自动清理未使用的导入语句")
        print("=" * 80)
        print()
        
        for filepath, names in self.cleanup_targets.items():
            self.clean_file(filepath, names)
        
        print()
        print("=" * 80)
        print("清理完成")
        print("=" * 80)
        print(f"清理文件数: {len(self.cleaned_files)}")
        print(f"移除导入数: {self.total_removed}")
        
        if self.cleaned_files:
            print("\n已清理的文件:")
            for f in self.cleaned_files:
                print(f"  - {f}")
        
        return len(self.cleaned_files)


if __name__ == "__main__":
    cleaner = UnusedImportCleaner()
    cleaner.run()
