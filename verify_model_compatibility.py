#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证模型与系统的兼容性
"""

import sys
import os

def verify_sklearn_version():
    """验证 scikit-learn 版本"""
    try:
        import sklearn
        version = sklearn.__version__
        print(f"✓ scikit-learn version: {version}")
        
        if version != "1.4.2":
            print(f"⚠ Warning: Expected version 1.4.2, got {version}")
            print("  This may cause compatibility issues with the trained model")
            return False
        return True
    except ImportError:
        print("✗ scikit-learn not installed")
        return False


def verify_model_loading():
    """验证模型加载"""
    try:
        import joblib
        
        model_file = 'ml_models/ensemble.pkl'
        if not os.path.exists(model_file):
            print(f"✗ Model file not found: {model_file}")
            return False
        
        model_data = joblib.load(model_file)
        
        print(f"✓ Model loaded successfully")
        print(f"  Format: WolfDetectionEnsemble")
        print(f"  Models: {[k for k in model_data.keys() if 'model' in k]}")
        print(f"  Is trained: {model_data.get('is_trained', False)}")
        
        # 验证模型可以预测
        import numpy as np
        test_input = np.random.rand(1, 18)
        
        rf_model = model_data['rf_model']
        gb_model = model_data['gb_model']
        
        rf_pred = rf_model.predict(test_input)
        rf_proba = rf_model.predict_proba(test_input)
        print(f"  rf_model: prediction={rf_pred[0]}, probabilities={rf_proba[0]}")
        
        gb_pred = gb_model.predict(test_input)
        gb_proba = gb_model.predict_proba(test_input)
        print(f"  gb_model: prediction={gb_pred[0]}, probabilities={gb_proba[0]}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_ml_agent_integration():
    """验证 ML Agent 集成"""
    try:
        # 尝试导入 ML Agent
        sys.path.insert(0, os.path.dirname(__file__))
        from werewolf.ml_agent import LightweightMLAgent
        
        print("✓ LightweightMLAgent imported successfully")
        
        # 尝试初始化
        ml_agent = LightweightMLAgent(model_dir='./ml_models')
        print(f"✓ ML Agent initialized")
        print(f"  Enabled: {ml_agent.enabled}")
        print(f"  Models loaded: {ml_agent.models is not None}")
        
        return True
        
    except Exception as e:
        print(f"⚠ ML Agent integration check failed: {e}")
        print("  This is expected if dependencies are not fully installed")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Model Compatibility Verification")
    print("=" * 60)
    
    results = []
    
    print("\n1. Checking scikit-learn version...")
    results.append(verify_sklearn_version())
    
    print("\n2. Checking model loading...")
    results.append(verify_model_loading())
    
    print("\n3. Checking ML Agent integration...")
    results.append(verify_ml_agent_integration())
    
    print("\n" + "=" * 60)
    if all(results[:2]):  # 前两个检查必须通过
        print("✓ All critical checks passed!")
        print("  The model is compatible with the system")
    else:
        print("✗ Some checks failed")
        print("  Please review the errors above")
    print("=" * 60)


if __name__ == '__main__':
    main()
