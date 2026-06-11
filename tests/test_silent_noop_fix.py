"""
Regression tests for the Silent No-Op bug in ContinualLearningTrainer.

Bug: `_metrics_improved` used `>=` / `<=` for accuracy/MSE/MAE comparison,
which meant identical metrics reported as "improved". The retrain
pipeline could claim "improved_and_saved" 50+ days running with zero
weight changes.

Fix (2026-06-11): strict `>` / `<` so identical metrics return False
(no improvement).

These tests fail if anyone reverts to the loose comparison.
"""
import sys
from pathlib import Path

# Make sovereign_continual_learning importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sovereign_continual_learning import ContinualLearningTrainer


def test_identical_mse_is_not_improvement():
    """Identical MSE used to report as improved due to `>=` / `<=`."""
    result = ContinualLearningTrainer._metrics_improved(
        {"mse": 0.01, "mae": 0.1}, {"mse": 0.01, "mae": 0.1}
    )
    assert result is False, (
        f"Identical metrics must NOT report as improved, got {result}"
    )


def test_identical_accuracy_is_not_improvement():
    """The classic Silent No-Op case."""
    result = ContinualLearningTrainer._metrics_improved(
        {"accuracy": 0.9}, {"accuracy": 0.9}
    )
    assert result is False


def test_mse_decreased_is_improvement():
    """MSE going down means the model is better."""
    result = ContinualLearningTrainer._metrics_improved(
        {"mse": 0.01, "mae": 0.1}, {"mse": 0.005, "mae": 0.05}
    )
    assert result is True


def test_mse_increased_is_not_improvement():
    """MSE going up means the model is worse."""
    result = ContinualLearningTrainer._metrics_improved(
        {"mse": 0.01, "mae": 0.1}, {"mse": 0.02, "mae": 0.2}
    )
    assert result is False


def test_accuracy_increased_is_improvement():
    result = ContinualLearningTrainer._metrics_improved(
        {"accuracy": 0.9}, {"accuracy": 0.92}
    )
    assert result is True


def test_accuracy_decreased_is_not_improvement():
    result = ContinualLearningTrainer._metrics_improved(
        {"accuracy": 0.9}, {"accuracy": 0.88}
    )
    assert result is False


def test_empty_pre_is_first_train():
    """First train (no pre-metrics) is always accepted."""
    result = ContinualLearningTrainer._metrics_improved({}, {"mse": 0.01})
    assert result is True


def test_mae_fallback():
    """MAE-only models use the MAE branch."""
    result = ContinualLearningTrainer._metrics_improved(
        {"mae": 0.1}, {"mae": 0.05}
    )
    assert result is True

    result = ContinualLearningTrainer._metrics_improved(
        {"mae": 0.1}, {"mae": 0.1}
    )
    assert result is False, "Identical MAE must not report as improved"


def test_no_comparable_metrics_is_first_train():
    """Empty post metrics = first train path."""
    result = ContinualLearningTrainer._metrics_improved(
        {"some_other": 1.0}, {"different_key": 2.0}
    )
    assert result is True  # falls through to "accept"


if __name__ == "__main__":
    tests = [
        test_identical_mse_is_not_improvement,
        test_identical_accuracy_is_not_improvement,
        test_mse_decreased_is_improvement,
        test_mse_increased_is_not_improvement,
        test_accuracy_increased_is_improvement,
        test_accuracy_decreased_is_not_improvement,
        test_empty_pre_is_first_train,
        test_mae_fallback,
        test_no_comparable_metrics_is_first_train,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
        except AssertionError as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED")
        sys.exit(1)
    print(f"\n✅ All {len(tests)} tests passed")
