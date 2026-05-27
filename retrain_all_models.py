#!/usr/bin/env python3
"""
Retrain neural models with real data — properly handles large text corpora.
Uses TruncatedSVD (LSA) to reduce TF-IDF dimensionality and prevent overflow.
"""

import sys
import os
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
TRAINING_DIR = os.path.join(os.path.dirname(__file__), "training_data")


def load_episodes(filename):
    filepath = os.path.join(TRAINING_DIR, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        return json.load(f)


def prepare_features(texts, max_features=500, n_components=128):
    """Convert texts to features using TF-IDF + TruncatedSVD."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import Normalizer

    # TF-IDF with limited vocabulary
    tfidf = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        max_df=0.95,
        min_df=2,
        sublinear_tf=True,  # Apply log normalization
    )
    X_tfidf = tfidf.fit_transform(texts)

    # Reduce dimensionality with SVD
    n_components = min(n_components, X_tfidf.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    X_svd = svd.fit_transform(X_tfidf)

    # Normalize
    X_svd = Normalizer().fit_transform(X_svd)

    return X_svd, tfidf, svd


def train_mlp(X, y, hidden_sizes=(64, 32), max_iter=500):
    """Train MLP with proper scaling."""
    from sklearn.neural_network import MLPRegressor

    model = MLPRegressor(
        hidden_layer_sizes=hidden_sizes,
        activation="relu",
        solver="adam",
        max_iter=max_iter,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        learning_rate="adaptive",
        alpha=0.001,  # L2 regularization
    )

    model.fit(X, y)

    predictions = model.predict(X)
    mse = float(np.mean((predictions - y) ** 2))
    mae = float(np.mean(np.abs(predictions - y)))

    return model, mse, mae


def retrain_care_validation():
    """Retrain care_validation_nn with real interaction data."""
    from neural_core.care_validation_nn import CareValidationNN
    import pickle

    print("\n🧠 Retraining care_validation_nn...")

    care_episodes = load_episodes("care_episodes.json")
    relationship_episodes = load_episodes("relationship_episodes.json")
    all_episodes = care_episodes + relationship_episodes

    if len(all_episodes) < 10:
        print(f"  ⚠️  Only {len(all_episodes)} episodes, skipping")
        return False

    texts = [ep.get("content", "")[:500] for ep in all_episodes if ep.get("content")]
    if len(texts) < 10:
        print("  ⚠️  Not enough valid text, skipping")
        return False

    # Prepare features
    X, tfidf, svd = prepare_features(texts, max_features=500, n_components=128)

    # Generate labels from care_weight
    labels = []
    for ep in all_episodes[: len(texts)]:
        care_wt = float(ep.get("care_weight", 0.5))
        importance = float(ep.get("importance_score", 0.2))
        noise = np.random.uniform(-0.05, 0.05, 6)
        labels.append(
            [
                min(care_wt * 1.1 + noise[0], 1.0),
                min(care_wt * 1.0 + noise[1], 1.0),
                min(care_wt * 0.9 + importance * 0.1 + noise[2], 1.0),
                min(care_wt * 0.85 + noise[3], 1.0),
                min(care_wt * 1.05 + noise[4], 1.0),
                min(care_wt * 0.95 + noise[5], 1.0),
            ]
        )
    y = np.array(labels, dtype=np.float32)

    model, mse, mae = train_mlp(X, y, hidden_sizes=(64, 32), max_iter=500)

    # Save model + vectorizer + svd
    nn_model = CareValidationNN(model_dir=MODEL_DIR)
    nn_model.model = model
    nn_model.vectorizer = tfidf
    nn_model.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn_model.is_trained = True

    # Save model
    nn_model.save_model()

    # Save SVD separately
    svd_path = os.path.join(MODEL_DIR, "care_validation_nn_svd.pkl")
    with open(svd_path, "wb") as f:
        pickle.dump(svd, f)

    print(
        f"  ✅ care_validation_nn: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
    return True


def retrain_threat_detection():
    """Retrain threat_detection_nn with security data."""
    from neural_core.threat_detection_nn import ThreatDetectionNN
    import pickle

    print("\n🧠 Retraining threat_detection_nn...")

    threat_episodes = load_episodes("threat_episodes.json")
    care_episodes = load_episodes("care_episodes.json")
    all_episodes = threat_episodes + care_episodes[:200]

    if len(all_episodes) < 10:
        print(f"  ⚠️  Only {len(all_episodes)} episodes, skipping")
        return False

    texts = [ep.get("content", "")[:500] for ep in all_episodes if ep.get("content")]
    if len(texts) < 10:
        print("  ⚠️  Not enough valid text, skipping")
        return False

    X, tfidf, svd = prepare_features(texts, max_features=300, n_components=64)

    labels = []
    for ep in all_episodes[: len(texts)]:
        tags = ep.get("tags", [])
        is_threat = any(t in tags for t in ["security", "threat", "alert", "critical"])
        care_wt = float(ep.get("care_weight", 0.5))

        if is_threat:
            labels.append([0.9, 0.8, 0.7, 0.85])
        elif care_wt < 0.3:
            labels.append([0.4, 0.5, 0.6, 0.3])
        else:
            labels.append([0.1, 0.15, 0.1, 0.05])
    y = np.array(labels, dtype=np.float32)

    model, mse, mae = train_mlp(X, y, hidden_sizes=(64, 32), max_iter=500)

    nn_model = ThreatDetectionNN(model_dir=MODEL_DIR)
    nn_model.model = model
    nn_model.vectorizer = tfidf
    nn_model.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn_model.is_trained = True
    nn_model.save_model()

    svd_path = os.path.join(MODEL_DIR, "threat_detection_nn_svd.pkl")
    with open(svd_path, "wb") as f:
        pickle.dump(svd, f)

    print(
        f"  ✅ threat_detection_nn: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
    return True


def retrain_partnership_detection():
    """Retrain partnership_detection_ml."""
    from neural_core.partnership_detection_ml import PartnershipDetectionML
    import pickle

    print("\n🧠 Retraining partnership_detection_ml...")

    partnership_episodes = load_episodes("partnership_episodes.json")
    care_episodes = load_episodes("care_episodes.json")
    all_episodes = partnership_episodes + care_episodes[:100]

    if len(all_episodes) < 10:
        print(f"  ⚠️  Only {len(all_episodes)} episodes, skipping")
        return False

    texts = [ep.get("content", "")[:500] for ep in all_episodes if ep.get("content")]
    if len(texts) < 10:
        print("  ⚠️  Not enough valid text, skipping")
        return False

    X, tfidf, svd = prepare_features(texts, max_features=300, n_components=64)

    labels = []
    for ep in all_episodes[: len(texts)]:
        tags = ep.get("tags", [])
        is_partnership = any(t in tags for t in ["partnership", "collaboration"])
        care_wt = float(ep.get("care_weight", 0.5))

        if is_partnership:
            labels.append([0.9, 0.85, 0.8, 0.9, 0.85, 0.8, 0.75, 0.85])
        elif care_wt > 0.7:
            labels.append([0.6, 0.55, 0.5, 0.6, 0.55, 0.5, 0.45, 0.55])
        else:
            labels.append([0.2, 0.25, 0.15, 0.2, 0.25, 0.2, 0.15, 0.2])
    y = np.array(labels, dtype=np.float32)

    model, mse, mae = train_mlp(X, y, hidden_sizes=(64, 32), max_iter=500)

    nn_model = PartnershipDetectionML(model_dir=MODEL_DIR)
    nn_model.model = model
    nn_model.vectorizer = tfidf
    nn_model.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn_model.is_trained = True
    nn_model.save_model()

    svd_path = os.path.join(MODEL_DIR, "partnership_detection_ml_svd.pkl")
    with open(svd_path, "wb") as f:
        pickle.dump(svd, f)

    print(
        f"  ✅ partnership_detection_ml: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
    return True


def retrain_creativity_assessment():
    """Retrain creativity_assessment_nn."""
    print("\n🧠 Retraining creativity_assessment_nn...")

    creativity_episodes = load_episodes("creativity_episodes.json")
    if len(creativity_episodes) < 10:
        print(f"  ⚠️  Only {len(creativity_episodes)} episodes, skipping")
        return False

    texts = [
        ep.get("content", "")[:500]
        for ep in creativity_episodes[:200]
        if ep.get("content")
    ]
    if len(texts) < 10:
        print("  ⚠️  Not enough valid text, skipping")
        return False

    X, tfidf, svd = prepare_features(texts, max_features=300, n_components=64)

    labels = []
    for ep in creativity_episodes[: len(texts)]:
        importance = float(ep.get("importance_score", 0.2))
        care_wt = float(ep.get("care_weight", 0.5))
        noise = np.random.uniform(-0.1, 0.1, 4)
        labels.append(
            [
                min(importance * 1.5 + noise[0], 1.0),
                min(care_wt * 0.8 + noise[1], 1.0),
                min(importance * 1.2 + care_wt * 0.3 + noise[2], 1.0),
                min(care_wt * 0.7 + noise[3], 1.0),
            ]
        )
    y = np.array(labels, dtype=np.float32)

    model, mse, mae = train_mlp(X, y, hidden_sizes=(64, 32), max_iter=500)

    # Save with creativity model
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "creativity_engine"))
    from creativity_nn import CreativityAssessmentNN
    import pickle

    nn_model = CreativityAssessmentNN(model_dir=MODEL_DIR)
    nn_model.model = model
    nn_model.vectorizer = tfidf
    nn_model.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn_model.is_trained = True
    nn_model.save_model()

    svd_path = os.path.join(MODEL_DIR, "creativity_assessment_nn_svd.pkl")
    with open(svd_path, "wb") as f:
        pickle.dump(svd, f)

    print(
        f"  ✅ creativity_assessment_nn: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
    return True


def retrain_relationship_evolution():
    """Retrain relationship_evolution_nn."""
    print("\n🧠 Retraining relationship_evolution_nn...")

    relationship_episodes = load_episodes("relationship_episodes.json")
    if len(relationship_episodes) < 10:
        print(f"  ⚠️  Only {len(relationship_episodes)} episodes, skipping")
        return False

    texts = [
        ep.get("content", "")[:500]
        for ep in relationship_episodes[:300]
        if ep.get("content")
    ]
    if len(texts) < 10:
        print("  ⚠️  Not enough valid text, skipping")
        return False

    X, tfidf, svd = prepare_features(texts, max_features=300, n_components=64)

    labels = []
    for ep in relationship_episodes[: len(texts)]:
        care_wt = float(ep.get("care_weight", 0.5))
        importance = float(ep.get("importance_score", 0.2))
        noise = np.random.uniform(-0.05, 0.05, 3)
        labels.append(
            [
                min(care_wt * 1.2 + noise[0], 1.0),
                min(importance * 2.0 + noise[1], 1.0),
                min(care_wt * 1.1 + noise[2], 1.0),
            ]
        )
    y = np.array(labels, dtype=np.float32)

    model, mse, mae = train_mlp(X, y, hidden_sizes=(32, 16), max_iter=500)

    from neural_core.relationship_evolution_nn import RelationshipEvolutionNN
    import pickle

    nn_model = RelationshipEvolutionNN(model_dir=MODEL_DIR)
    nn_model.model = model
    nn_model.vectorizer = tfidf
    nn_model.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn_model.is_trained = True
    nn_model.save_model()

    svd_path = os.path.join(MODEL_DIR, "relationship_evolution_nn_svd.pkl")
    with open(svd_path, "wb") as f:
        pickle.dump(svd, f)

    print(
        f"  ✅ relationship_evolution_nn: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🧠 NEURAL MODEL RETRAINING WITH REAL DATA")
    print("=" * 60)

    results = {}
    results["care_validation"] = retrain_care_validation()
    results["threat_detection"] = retrain_threat_detection()
    results["partnership_detection"] = retrain_partnership_detection()
    results["creativity_assessment"] = retrain_creativity_assessment()
    results["relationship_evolution"] = retrain_relationship_evolution()

    print("\n" + "=" * 60)
    print("📊 RETRAINING SUMMARY")
    print("=" * 60)

    for name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    success_count = sum(1 for v in results.values() if v)
    print(f"\n{success_count}/{len(results)} models retrained successfully")
