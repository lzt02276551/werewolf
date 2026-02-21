#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级代码清理脚本 - 第二阶段优化

功能:
1. 检测并清理未使用的导入语句
2. 检测重复代码
3. 检测未使用的方法和变量
4. 生成优化建议报告
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict

class AdvancedCodeCleaner:
    """高级代码清理器"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.issues = defaultdict(list)
        self.stats = {
            'files_checked': 0,
            'unused_imports': 0,
            'duplicate_code': 0,
            'unused_methods': 0
        }
    
    def find_python_files(self):
        """查找所有Python文件"""
        python_files = []
        for py_file in self.root_dir.rglob("*.py"):
            # 跳过__pycache__和虚拟环境
            if '__pycache__' in str(py_file) or 'venv' in str(py_file):
                continue
            python_files.append(py_file)
        return python_files
    
    def check_unused_imports(self, filepath):
        """检查未使用的导入"""
        try:
            content = filepath.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            # 收集所有导入
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imports.append((name, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imports.append((name, node.lineno))
            
            # 检查每个导入是否被使用
            unused = []
            for name, lineno in imports:
                # 简单检查：在导入语句之后的代码中是否出现该名称
                lines = content.split('\n')
                used = False
                for i, line in enumerate(lines[lineno:], start=lineno):
                    # 跳过注释和导入行本身
                    if line.strip().startswith('#') or i == lineno - 1:
                        continue
                    # 检查是否使用了该名称
                    if re.search(r'\b' + re.escape(name) + r'\b', line):
                        used = True
                        break
                
                if not used:
                    unused.append((name, lineno))
            
            return unused
        
        except Exception as e:
            return []
    
    def check_duplicate_methods(self, files):
        """检查重复的方法定义"""
        method_signatures = defaultdict(list)
        
        for filepath in files:
            try:
                content = filepath.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 获取方法签名（名称和参数）
                        params = [arg.arg for arg in node.args.args]
                        signature = f"{node.name}({', '.join(params)})"
                        method_signatures[signature].append(str(filepath))
            
            except Exception:
                continue
        
        # 找出重复的方法
        duplicates = {sig: files for sig, files in method_signatures.items() 
                     if len(files) > 1}
        
        return duplicates
    
    def analyze_code_complexity(self, filepath):
        """分析代码复杂度"""
        try:
            content = filepath.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            complex_functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 计算函数的行数
                    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                        lines = node.end_lineno - node.lineno
                        if lines > 50:  # 超过50行的函数
                            complex_functions.append({
                                'name': node.name,
                                'lines': lines,
                                'start': node.lineno
                            })
            
            return complex_functions
        
        except Exception:
            return []
    
    def run_analysis(self):
        """运行完整分析"""
        print("=" * 80)
        print("高级代码清理分析 - 第二阶段优化")
        print("=" * 80)
        
        python_files = self.find_python_files()
        print(f"\n找到 {len(python_files)} 个Python文件\n")
        
        # 阶段1: 检查未使用的导入
        print("=" * 80)
        print("阶段1: 检查未使用的导入")
        print("=" * 80)
        
        for filepath in python_files:
            self.stats['files_checked'] += 1
            unused = self.check_unused_imports(filepath)
            
            if unused:
                rel_path = filepath.relative_to(self.root_dir)
                self.issues['unused_imports'].append({
                    'file': str(rel_path),
                    'imports': unused
                })
                self.stats['unused_imports'] += len(unused)
                print(f"⚠️  {rel_path}: {len(unused)} 个未使用的导入")
        
        if not self.issues['unused_imports']:
            print("✅ 未发现未使用的导入")
        
        # 阶段2: 检查重复方法
        print("\n" + "=" * 80)
        print("阶段2: 检查重复方法")
        print("=" * 80)
        
        duplicates = self.check_duplicate_methods(python_files)
        
        if duplicates:
            for signature, files in duplicates.items():
                # 只报告在不同文件中的重复
                unique_files = set(files)
                if len(unique_files) > 1:
                    self.issues['duplicate_methods'].append({
                        'signature': signature,
                        'files': list(unique_files)
                    })
                    self.stats['duplicate_code'] += 1
                    print(f"⚠️  重复方法: {signature}")
                    for f in unique_files:
                        print(f"    - {Path(f).relative_to(self.root_dir)}")
        
        if not self.issues['duplicate_methods']:
            print("✅ 未发现明显的重复方法")
        
        # 阶段3: 检查复杂函数
        print("\n" + "=" * 80)
        print("阶段3: 检查复杂函数 (>50行)")
        print("=" * 80)
        
        for filepath in python_files:
            complex_funcs = self.analyze_code_complexity(filepath)
            
            if complex_funcs:
                rel_path = filepath.relative_to(self.root_dir)
                self.issues['complex_functions'].append({
                    'file': str(rel_path),
                    'functions': complex_funcs
                })
                print(f"⚠️  {rel_path}:")
                for func in complex_funcs:
                    print(f"    - {func['name']}: {func['lines']} 行 (第{func['start']}行)")
        
        if not self.issues['complex_functions']:
            print("✅ 未发现过于复杂的函数")
    
    def generate_report(self):
        """生成详细报告"""
        print("\n" + "=" * 80)
        print("分析报告")
        print("=" * 80)
        
        print(f"\n统计信息:")
        print(f"  检查文件数: {self.stats['files_checked']}")
        print(f"  未使用导入: {self.stats['unused_imports']}")
        print(f"  重复方法: {self.stats['duplicate_code']}")
        
        # 生成Markdown报告
        report_lines = []
        report_lines.append("# 代码优化分析报告 - 第二阶段")
        report_lines.append("")
        report_lines.append(f"**分析时间**: {Path(__file__).stat().st_mtime}")
        report_lines.append(f"**检查文件数**: {self.stats['files_checked']}")
        report_lines.append("")
        
        # 未使用的导入
        if self.issues['unused_imports']:
            report_lines.append("## 1. 未使用的导入")
            report_lines.append("")
            report_lines.append(f"发现 {self.stats['unused_imports']} 个未使用的导入语句")
            report_lines.append("")
            
            for issue in self.issues['unused_imports']:
                report_lines.append(f"### {issue['file']}")
                report_lines.append("")
                for name, lineno in issue['imports']:
                    report_lines.append(f"- 第{lineno}行: `{name}` (未使用)")
                report_lines.append("")
        
        # 重复方法
        if self.issues['duplicate_methods']:
            report_lines.append("## 2. 重复方法")
            report_lines.append("")
            report_lines.append(f"发现 {len(self.issues['duplicate_methods'])} 组重复方法")
            report_lines.append("")
            
            for issue in self.issues['duplicate_methods']:
                report_lines.append(f"### `{issue['signature']}`")
                report_lines.append("")
                report_lines.append("出现在:")
                for f in issue['files']:
                    report_lines.append(f"- {Path(f).relative_to(self.root_dir)}")
                report_lines.append("")
                report_lines.append("**建议**: 考虑提取到共享基类或工具模块")
                report_lines.append("")
        
        # 复杂函数
        if self.issues['complex_functions']:
            report_lines.append("## 3. 复杂函数 (建议重构)")
            report_lines.append("")
            
            for issue in self.issues['complex_functions']:
                report_lines.append(f"### {issue['file']}")
                report_lines.append("")
                for func in issue['functions']:
                    report_lines.append(f"- `{func['name']}`: {func['lines']} 行 (第{func['start']}行)")
                report_lines.append("")
                report_lines.append("**建议**: 将长函数拆分为多个小函数")
                report_lines.append("")
        
        # 优化建议
        report_lines.append("## 优化建议")
        report_lines.append("")
        report_lines.append("### 优先级 P1 (高)")
        report_lines.append("")
        if self.stats['unused_imports'] > 0:
            report_lines.append(f"1. 清理 {self.stats['unused_imports']} 个未使用的导入语句")
        if self.stats['duplicate_code'] > 0:
            report_lines.append(f"2. 重构 {self.stats['duplicate_code']} 组重复方法")
        report_lines.append("")
        
        report_lines.append("### 优先级 P2 (中)")
        report_lines.append("")
        if self.issues['complex_functions']:
            report_lines.append("1. 重构复杂函数，提高可读性")
        report_lines.append("2. 添加单元测试覆盖")
        report_lines.append("3. 完善代码注释")
        report_lines.append("")
        
        # 写入报告
        report_path = self.root_dir / "代码优化分析报告_第二阶段.md"
        report_path.write_text("\n".join(report_lines), encoding='utf-8')
        print(f"\n✅ 详细报告已生成: {report_path}")
        
        return report_path
    
    def run(self):
        """执行完整流程"""
        self.run_analysis()
        report_path = self.generate_report()
        
        print("\n" + "=" * 80)
        print("分析完成！")
        print("=" * 80)
        print(f"\n查看详细报告: {report_path}")
        
        return len(self.issues['unused_imports']) + len(self.issues['duplicate_methods'])


if __name__ == "__main__":
    cleaner = AdvancedCodeCleaner()
    issues_count = cleaner.run()
