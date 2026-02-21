#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析已删除文件的功能和必要性

检查这些文件是否真的无用，或者只是还没来得及集成
"""

import subprocess
import re
from pathlib import Path

class DeletedFileAnalyzer:
    """已删除文件分析器"""
    
    def __init__(self):
        self.deleted_files = [
            "werewolf/guard/validators.py",
            "werewolf/guard/exceptions.py",
            "werewolf/hunter/game_state.py",
            "werewolf/seer/ml_integration.py",
            "werewolf/witch/analyzers.py",
            "werewolf/wolf/base_components.py",
            "werewolf/wolf/decision_engine.py",
        ]
        
        self.analysis_results = {}
    
    def get_file_content(self, filepath, commit="473c9ec^"):
        """从Git历史中获取文件内容"""
        try:
            result = subprocess.run(
                ['git', 'show', f'{commit}:{filepath}'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            print(f"Error getting {filepath}: {e}")
            return None
    
    def analyze_file_purpose(self, filepath, content):
        """分析文件的用途"""
        if not content:
            return {"purpose": "Unknown", "classes": [], "functions": [], "imports": []}
        
        # 提取类定义
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        
        # 提取函数定义
        functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
        
        # 提取导入
        imports = re.findall(r'^(?:from|import)\s+(.+)', content, re.MULTILINE)
        
        # 提取文档字符串
        docstring_match = re.search(r'"""(.+?)"""', content, re.DOTALL)
        purpose = docstring_match.group(1).strip() if docstring_match else "No description"
        
        return {
            "purpose": purpose[:200],  # 限制长度
            "classes": classes,
            "functions": functions,
            "imports": imports[:10],  # 只显示前10个导入
            "lines": len(content.split('\n'))
        }
    
    def check_similar_functionality(self, filepath):
        """检查是否有类似功能的文件"""
        # 获取同目录下的其他文件
        dir_path = Path(filepath).parent
        similar_files = []
        
        if dir_path.exists():
            for file in dir_path.glob("*.py"):
                if file.name != "__init__.py" and file.name != Path(filepath).name:
                    similar_files.append(str(file))
        
        return similar_files
    
    def check_if_functionality_exists_elsewhere(self, filepath, content):
        """检查功能是否在其他地方实现"""
        if not content:
            return []
        
        # 提取主要的类名
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        
        duplicates = []
        for class_name in classes:
            # 在项目中搜索相同的类名
            try:
                result = subprocess.run(
                    ['git', 'grep', '-l', f'class {class_name}'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                if result.returncode == 0:
                    files = result.stdout.strip().split('\n')
                    # 排除已删除的文件
                    files = [f for f in files if f and not any(d in f for d in self.deleted_files)]
                    if files:
                        duplicates.append({
                            'class': class_name,
                            'found_in': files
                        })
            except Exception:
                pass
        
        return duplicates
    
    def analyze_all(self):
        """分析所有已删除的文件"""
        print("=" * 80)
        print("已删除文件功能分析")
        print("=" * 80)
        print()
        
        for filepath in self.deleted_files:
            print(f"\n{'=' * 80}")
            print(f"文件: {filepath}")
            print('=' * 80)
            
            # 获取文件内容
            content = self.get_file_content(filepath)
            
            if not content:
                print("⚠️  无法获取文件内容")
                continue
            
            # 分析文件用途
            analysis = self.analyze_file_purpose(filepath, content)
            
            print(f"\n📝 用途:")
            print(f"   {analysis['purpose']}")
            
            print(f"\n📊 统计:")
            print(f"   代码行数: {analysis['lines']}")
            print(f"   类数量: {len(analysis['classes'])}")
            print(f"   函数数量: {len(analysis['functions'])}")
            
            if analysis['classes']:
                print(f"\n🏗️  定义的类:")
                for cls in analysis['classes'][:10]:  # 只显示前10个
                    print(f"   - {cls}")
            
            if analysis['functions']:
                print(f"\n⚙️  定义的函数:")
                for func in analysis['functions'][:10]:  # 只显示前10个
                    print(f"   - {func}")
            
            # 检查类似功能
            similar = self.check_similar_functionality(filepath)
            if similar:
                print(f"\n📁 同目录下的其他文件:")
                for f in similar[:5]:
                    print(f"   - {f}")
            
            # 检查功能重复
            duplicates = self.check_if_functionality_exists_elsewhere(filepath, content)
            if duplicates:
                print(f"\n🔄 功能可能在其他地方实现:")
                for dup in duplicates:
                    print(f"   - {dup['class']} 在以下文件中:")
                    for f in dup['found_in'][:3]:
                        print(f"     • {f}")
            else:
                print(f"\n✅ 未发现功能重复")
            
            # 保存分析结果
            self.analysis_results[filepath] = {
                'analysis': analysis,
                'similar_files': similar,
                'duplicates': duplicates
            }
        
        # 生成总结
        self.generate_summary()
    
    def generate_summary(self):
        """生成分析总结"""
        print("\n" + "=" * 80)
        print("分析总结")
        print("=" * 80)
        
        print("\n【建议保留的文件】")
        should_keep = []
        
        for filepath, result in self.analysis_results.items():
            analysis = result['analysis']
            duplicates = result['duplicates']
            
            # 判断是否应该保留
            reasons = []
            
            # 1. 如果有很多类和函数，可能是重要功能
            if len(analysis['classes']) > 3 or len(analysis['functions']) > 5:
                reasons.append(f"包含{len(analysis['classes'])}个类和{len(analysis['functions'])}个函数")
            
            # 2. 如果没有功能重复
            if not duplicates:
                reasons.append("功能未在其他地方实现")
            
            # 3. 如果代码量大
            if analysis['lines'] > 200:
                reasons.append(f"代码量较大({analysis['lines']}行)")
            
            if reasons:
                should_keep.append({
                    'file': filepath,
                    'reasons': reasons
                })
        
        if should_keep:
            for item in should_keep:
                print(f"\n⚠️  {item['file']}")
                for reason in item['reasons']:
                    print(f"   - {reason}")
        else:
            print("\n✅ 所有文件都可以安全删除")
        
        print("\n【确认可以删除的文件】")
        can_delete = []
        
        for filepath, result in self.analysis_results.items():
            duplicates = result['duplicates']
            
            if duplicates:
                can_delete.append({
                    'file': filepath,
                    'reason': f"功能在{len(duplicates)}个其他文件中实现"
                })
        
        if can_delete:
            for item in can_delete:
                print(f"\n✅ {item['file']}")
                print(f"   - {item['reason']}")
        
        print("\n" + "=" * 80)
        print("分析完成")
        print("=" * 80)


if __name__ == "__main__":
    analyzer = DeletedFileAnalyzer()
    analyzer.analyze_all()
