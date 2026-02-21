#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查所有已删除的文件

分析所有Git历史中删除的文件，判断是否需要恢复
"""

import subprocess
import re
from pathlib import Path
from collections import defaultdict

class AllDeletedFilesChecker:
    """所有已删除文件检查器"""
    
    def __init__(self):
        self.deleted_files = defaultdict(list)
        self.analysis_results = {}
    
    def find_all_deleted_files(self):
        """查找所有已删除的文件"""
        print("=" * 80)
        print("查找所有已删除的文件")
        print("=" * 80)
        print()
        
        # 获取所有删除文件的提交
        result = subprocess.run(
            ['git', 'log', '--all', '--pretty=format:%H', '--diff-filter=D', '--name-only'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            print("❌ 无法获取Git历史")
            return
        
        lines = result.stdout.strip().split('\n')
        current_commit = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是提交哈希
            if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
                current_commit = line
            elif current_commit and line.endswith('.py'):
                self.deleted_files[current_commit].append(line)
        
        # 去重并按提交分组
        print(f"找到 {len(self.deleted_files)} 个包含删除文件的提交\n")
        
        # 获取每个提交的信息
        for commit, files in self.deleted_files.items():
            result = subprocess.run(
                ['git', 'show', '--no-patch', '--format=%h %s', commit],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                commit_info = result.stdout.strip()
                print(f"📦 {commit_info}")
                print(f"   删除文件数: {len(files)}")
                for f in files[:5]:  # 只显示前5个
                    print(f"   - {f}")
                if len(files) > 5:
                    print(f"   ... 还有 {len(files) - 5} 个文件")
                print()
    
    def check_specific_deleted_files(self):
        """检查特定的已删除文件"""
        print("\n" + "=" * 80)
        print("检查关键已删除文件")
        print("=" * 80)
        print()
        
        # 重点检查的文件
        key_files = [
            ("094bad2", "werewolf/guard/analyzers.py"),
            ("094bad2", "werewolf/guard/detectors.py"),
            ("094bad2", "werewolf/wolf/detectors.py"),
        ]
        
        for commit, filepath in key_files:
            print(f"\n{'=' * 80}")
            print(f"文件: {filepath}")
            print(f"删除于: {commit}")
            print('=' * 80)
            
            # 获取文件内容
            content = self.get_file_content(filepath, f"{commit}^")
            
            if not content:
                print("⚠️  无法获取文件内容")
                continue
            
            # 分析文件
            analysis = self.analyze_file(filepath, content)
            
            print(f"\n📝 用途:")
            print(f"   {analysis['purpose'][:200]}")
            
            print(f"\n📊 统计:")
            print(f"   代码行数: {analysis['lines']}")
            print(f"   类数量: {len(analysis['classes'])}")
            print(f"   函数数量: {len(analysis['functions'])}")
            
            if analysis['classes']:
                print(f"\n🏗️  定义的类:")
                for cls in analysis['classes'][:10]:
                    print(f"   - {cls}")
            
            # 检查当前是否存在
            current_path = Path(filepath)
            if current_path.exists():
                print(f"\n✅ 文件当前存在")
                # 检查是否是同一个文件
                current_content = current_path.read_text(encoding='utf-8', errors='ignore')
                if len(current_content) == len(content):
                    print(f"   文件大小相同，可能已恢复")
                else:
                    print(f"   文件大小不同 (当前: {len(current_content)}, 原始: {len(content)})")
            else:
                print(f"\n❌ 文件当前不存在")
                
                # 检查是否有类似功能
                similar = self.check_similar_files(filepath)
                if similar:
                    print(f"\n📁 同目录下的其他文件:")
                    for f in similar[:5]:
                        print(f"   - {f}")
                
                # 检查功能是否在其他地方实现
                duplicates = self.check_functionality_elsewhere(filepath, content)
                if duplicates:
                    print(f"\n🔄 功能可能在其他地方实现:")
                    for dup in duplicates[:3]:
                        print(f"   - {dup['class']} 在: {dup['found_in'][0]}")
                else:
                    print(f"\n⚠️  功能未在其他地方找到，可能需要恢复")
            
            self.analysis_results[filepath] = analysis
    
    def get_file_content(self, filepath, commit):
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
    
    def analyze_file(self, filepath, content):
        """分析文件内容"""
        if not content:
            return {"purpose": "Unknown", "classes": [], "functions": [], "lines": 0}
        
        # 提取类定义
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        
        # 提取函数定义
        functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
        
        # 提取文档字符串
        docstring_match = re.search(r'"""(.+?)"""', content, re.DOTALL)
        purpose = docstring_match.group(1).strip() if docstring_match else "No description"
        
        return {
            "purpose": purpose,
            "classes": classes,
            "functions": functions,
            "lines": len(content.split('\n'))
        }
    
    def check_similar_files(self, filepath):
        """检查同目录下的其他文件"""
        dir_path = Path(filepath).parent
        similar_files = []
        
        if dir_path.exists():
            for file in dir_path.glob("*.py"):
                if file.name != "__init__.py" and file.name != Path(filepath).name:
                    similar_files.append(str(file))
        
        return similar_files
    
    def check_functionality_elsewhere(self, filepath, content):
        """检查功能是否在其他地方实现"""
        if not content:
            return []
        
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        
        duplicates = []
        for class_name in classes:
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
                    files = [f for f in files if f and f != filepath]
                    if files:
                        duplicates.append({
                            'class': class_name,
                            'found_in': files
                        })
            except Exception:
                pass
        
        return duplicates
    
    def generate_summary(self):
        """生成总结报告"""
        print("\n" + "=" * 80)
        print("总结报告")
        print("=" * 80)
        
        print("\n【需要检查的文件】")
        
        need_check = []
        for filepath, analysis in self.analysis_results.items():
            current_path = Path(filepath)
            if not current_path.exists():
                need_check.append({
                    'file': filepath,
                    'lines': analysis['lines'],
                    'classes': len(analysis['classes']),
                    'functions': len(analysis['functions'])
                })
        
        if need_check:
            for item in need_check:
                print(f"\n⚠️  {item['file']}")
                print(f"   - 代码行数: {item['lines']}")
                print(f"   - 类数量: {item['classes']}")
                print(f"   - 函数数量: {item['functions']}")
        else:
            print("\n✅ 所有关键文件都已存在或已恢复")
        
        print("\n" + "=" * 80)
    
    def run(self):
        """运行完整分析"""
        self.find_all_deleted_files()
        self.check_specific_deleted_files()
        self.generate_summary()


if __name__ == "__main__":
    checker = AllDeletedFilesChecker()
    checker.run()
