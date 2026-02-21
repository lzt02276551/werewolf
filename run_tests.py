#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Werewolf项目测试运行器

运行所有测试并生成报告
"""

import sys
import os
import time
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_tests(verbose=False):
    """运行所有测试"""
    print("="*70)
    print("Werewolf项目测试套件")
    print("="*70)
    print()
    
    start_time = time.time()
    
    # 运行P0/P1修复测试
    print("运行P0/P1修复测试...")
    print("-"*70)
    
    try:
        from tests.test_p0_p1_fixes import run_tests
        result1 = run_tests()
    except Exception as e:
        print(f"❌ P0/P1测试运行失败: {e}")
        result1 = 1
    
    print()
    
    # 运行原有的修复验证测试
    print("运行原有修复验证测试...")
    print("-"*70)
    
    try:
        import test_fixes
        result2 = test_fixes.main()
    except Exception as e:
        print(f"❌ 修复验证测试运行失败: {e}")
        result2 = 1
    
    print()
    
    # 计算总时间
    elapsed_time = time.time() - start_time
    
    # 打印总结
    print("="*70)
    print("测试总结")
    print("="*70)
    print(f"总耗时: {elapsed_time:.2f}秒")
    print()
    
    if result1 == 0 and result2 == 0:
        print("🎉 所有测试通过！")
        return 0
    else:
        failed_suites = []
        if result1 != 0:
            failed_suites.append("P0/P1修复测试")
        if result2 != 0:
            failed_suites.append("修复验证测试")
        
        print(f"❌ 以下测试套件失败: {', '.join(failed_suites)}")
        return 1


def run_specific_test(test_name):
    """运行特定测试"""
    print(f"运行测试: {test_name}")
    print("-"*70)
    
    import unittest
    
    try:
        # 尝试加载测试
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(test_name)
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return 0 if result.wasSuccessful() else 1
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return 1


def list_tests():
    """列出所有可用的测试"""
    print("可用的测试:")
    print("-"*70)
    
    tests = [
        "tests.test_p0_p1_fixes.TestTask001_MLPredictionErrorHandling",
        "tests.test_p0_p1_fixes.TestTask002_WeightNormalization",
        "tests.test_p0_p1_fixes.TestTask003_MemoryLeakFix",
        "tests.test_p0_p1_fixes.TestTask004_TypeValidation",
        "tests.test_p0_p1_fixes.TestTask005_IncrementalLearningErrorHandling",
        "tests.test_p0_p1_fixes.TestTask006_VoteAccuracyValidation",
        "tests.test_p0_p1_fixes.TestTask008_GameEndHandlerErrorHandling",
        "tests.test_p0_p1_fixes.TestTask010_TrustScoreHistory",
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"{i}. {test}")
    
    print()
    print("运行特定测试:")
    print(f"  python run_tests.py --test <测试名称>")
    print()
    print("示例:")
    print(f"  python run_tests.py --test {tests[0]}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Werewolf项目测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  运行所有测试:
    python run_tests.py
  
  运行特定测试:
    python run_tests.py --test tests.test_p0_p1_fixes.TestTask001_MLPredictionErrorHandling
  
  列出所有测试:
    python run_tests.py --list
  
  详细输出:
    python run_tests.py --verbose
        """
    )
    
    parser.add_argument(
        '--test',
        type=str,
        help='运行特定测试（格式: module.TestClass 或 module.TestClass.test_method）'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有可用的测试'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_tests()
        return 0
    
    if args.test:
        return run_specific_test(args.test)
    
    return run_all_tests(verbose=args.verbose)


if __name__ == '__main__':
    sys.exit(main())
