#!/usr/bin/env python3
"""Finish retraining the last 2 neural models."""

import sys, os, json, pickle, numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "neural_core"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "creativity_engine"))

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
TRAINING_DIR = os.path.join(os.path.dirname(__file__), "training_data")


def load_episodes(fn):
    fp = os.path.join(TRAINING_DIR, fn)
    if not os.path.exists(fp):
        return []
    with open(fp) as f:
        return json.load(f)


def prep(texts, max_f=300, n_comp=64):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import Normalizer

    tfidf = TfidfVectorizer(
        max_features=max_f,
        stop_words="english",
        max_df=0.95,
        min_df=2,
        sublinear_tf=True,
    )
    X = tfidf.fit_transform(texts)
    n_comp = min(n_comp, X.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    X = svd.fit_transform(X)
    X = Normalizer().fit_transform(X)
    return X, tfidf, svd


def train(X, y):
    from sklearn.neural_network import MLPRegressor

    m = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        solver="adam",
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        learning_rate="adaptive",
        alpha=0.001,
    )
    m.fit(X, y)
    p = m.predict(X)
    return m, float(np.mean((p - y) ** 2)), float(np.mean(np.abs(p - y)))


# ── Creativity Assessment ──
print("🧠 Retraining creativity_assessment_nn...")
eps = load_episodes("creativity_episodes.json")[:200]
texts = [e.get("content", "")[:500] for e in eps if e.get("content")]
if len(texts) >= 10:
    X, tfidf, svd = prep(texts)
    labels = []
    for e in eps[: len(texts)]:
        imp = float(e.get("importance_score", 0.2))
        cw = float(e.get("care_weight", 0.5))
        n = np.random.uniform(-0.1, 0.1, 4)
        labels.append(
            [
                min(imp * 1.5 + n[0], 1.0),
                min(cw * 0.8 + n[1], 1.0),
                min(imp * 1.2 + cw * 0.3 + n[2], 1.0),
                min(cw * 0.7 + n[3], 1.0),
            ]
        )
    y = np.array(labels, dtype=np.float32)
    model, mse, mae = train(X, y)

    from creativity_nn import CreativityAssessmentNN

    nn = CreativityAssessmentNN(model_dir=MODEL_DIR)
    nn.model = model
    nn.vectorizer = tfidf
    nn.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn.is_trained = True
    nn.save_model()
    with open(os.path.join(MODEL_DIR, "creativity_assessment_nn_svd.pkl"), "wb") as f:
        pickle.dump(svd, f)
    print(
        f"  ✅ creativity_assessment_nn: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
else:
    print("  ⚠️  Not enough data for creativity_assessment_nn")

# ── Relationship Evolution ──
print("🧠 Retraining relationship_evolution_nn...")
from relationship_evolution_nn import RelationshipEvolutionNN

eps = load_episodes("relationship_episodes.json")[:300]
texts = [e.get("content", "")[:500] for e in eps if e.get("content")]
if len(texts) >= 10:
    X, tfidf, svd = prep(texts)
    labels = []
    for e in eps[: len(texts)]:
        cw = float(e.get("care_weight", 0.5))
        imp = float(e.get("importance_score", 0.2))
        n = np.random.uniform(-0.05, 0.05, 3)
        labels.append(
            [
                min(cw * 1.2 + n[0], 1.0),
                min(imp * 2.0 + n[1], 1.0),
                min(cw * 1.1 + n[2], 1.0),
            ]
        )
    y = np.array(labels, dtype=np.float32)
    model, mse, mae = train(X, y)

    nn = RelationshipEvolutionNN(model_dir=MODEL_DIR)
    nn.model = model
    nn.vectorizer = tfidf
    nn.metrics = {
        "mse": mse,
        "mae": mae,
        "training_samples": len(texts),
        "input_features": X.shape[1],
        "output_dimensions": y.shape[1],
    }
    nn.is_trained = True
    nn.save_model()
    with open(os.path.join(MODEL_DIR, "relationship_evolution_nn_svd.pkl"), "wb") as f:
        pickle.dump(svd, f)
    print(
        f"  ✅ relationship_evolution_nn: {len(texts)} episodes, MSE={mse:.4f}, MAE={mae:.4f}"
    )
else:
    print("  ⚠️  Not enough data for relationship_evolution_nn")

print("\n✅ All models retrained!")
