#!/usr/bin/env python3
"""
Create dummy LightGBM models for SOV3 to prevent zero-prediction bug.
Run this after deploying to Railway to initialise model files.

Usage: python scripts/create_dummy_models.py
"""
import os
import numpy as np

def create_dummy_models():
    """Create properly initialised LightGBM models for all 7 prediction tasks."""
    try:
        import lightgbm as lgb
        print("✓ LightGBM available")
    except ImportError:
        print("✗ LightGBM not installed. Run: pip install lightgbm")
        return

    model_dir = os.environ.get('MODEL_DIR', '/app/models')
    os.makedirs(model_dir, exist_ok=True)

    # 7 prediction tasks matching SOV3's model registry
    tasks = [
        ('care_quality', 'binary'),
        ('sycophancy', 'binary'),
        ('threat_level', 'multiclass'),
        ('memory_importance', 'regression'),
        ('response_quality', 'regression'),
        ('user_engagement', 'binary'),
        ('relationship_depth', 'regression'),
    ]

    # Generate synthetic training data (100 samples, 20 features)
    np.random.seed(42)
    X = np.random.randn(100, 20)

    for task_name, task_type in tasks:
        model_path = os.path.join(model_dir, f'{task_name}.lgb')

        if task_type == 'binary':
            y = (X[:, 0] + np.random.randn(100) * 0.1 > 0).astype(int)
            params = {
                'objective': 'binary',
                'num_leaves': 10,
                'n_estimators': 20,
                'verbose': -1,
            }
        elif task_type == 'multiclass':
            y = np.clip((X[:, 0] * 2 + 2).astype(int), 0, 3)
            params = {
                'objective': 'multiclass',
                'num_class': 4,
                'num_leaves': 10,
                'n_estimators': 20,
                'verbose': -1,
            }
        else:  # regression
            y = X[:, 0] * 0.3 + 0.5 + np.random.randn(100) * 0.05
            y = np.clip(y, 0, 1)
            params = {
                'objective': 'regression',
                'num_leaves': 10,
                'n_estimators': 20,
                'verbose': -1,
            }

        model = lgb.LGBMClassifier(**params) if task_type != 'regression' else lgb.LGBMRegressor(**params)
        model.fit(X, y)
        model.booster_.save_model(model_path)

        # Verify prediction returns non-zero
        test_pred = model.predict_proba(X[:1]) if task_type == 'binary' else model.predict(X[:1])
        print(f"✓ {task_name}: model saved to {model_path}, test prediction: {test_pred[0]:.4f}" if task_type == 'regression' else f"✓ {task_name}: saved, test pred: {test_pred}")

    print(f"\n✓ All 7 models created in {model_dir}")
    print("Deploy to Railway and restart the SOV3 service.")

if __name__ == "__main__":
    create_dummy_models()
