#!/usr/bin/env python3
"""Train dormant SOV3 neural models (care_validation_nn, partnership_detection_ml, dependency_detection_nn)
using training data episodes + synthetic augmentation."""
import json, os, sys, pickle, numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer, StandardScaler

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
TRAINING_DIR = os.path.join(os.path.dirname(__file__), "training_data")
np.random.seed(42)

def load_json(fn):
    p = os.path.join(TRAINING_DIR, fn)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return []

def prep_text(texts, max_f=300, n_comp=64):
    if not texts or len(texts) < 5:
        return np.random.randn(max(5, len(texts)), n_comp).astype(np.float32), None, None
    tfidf = TfidfVectorizer(max_features=max_f, stop_words="english", max_df=0.95, min_df=1, sublinear_tf=True)
    X = tfidf.fit_transform(texts)
    n_comp = min(n_comp, X.shape[1] - 1)
    if n_comp < 1:
        return np.random.randn(len(texts), 64).astype(np.float32), None, None
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    X = svd.fit_transform(X)
    X = Normalizer().fit_transform(X)
    return X, tfidf, svd

def train_regressor(X, y):
    m = MLPRegressor(
        hidden_layer_sizes=(64, 32), activation="relu", solver="adam",
        max_iter=500, random_state=42, early_stopping=True,
        validation_fraction=0.15, learning_rate="adaptive", alpha=0.001
    )
    m.fit(X, y)
    p = m.predict(X)
    return m, float(np.mean((p - y) ** 2)), float(np.mean(np.abs(p - y)))

def save_model(model, vectorizer, metadata, name):
    path_pkl = os.path.join(MODEL_DIR, f"{name}.pkl")
    path_vec = os.path.join(MODEL_DIR, f"{name}_vectorizer.pkl")
    path_meta = os.path.join(MODEL_DIR, f"{name}_metadata.json")
    with open(path_pkl, "wb") as f:
        pickle.dump(model, f)
    if vectorizer:
        with open(path_vec, "wb") as f:
            pickle.dump(vectorizer, f)
    with open(path_meta, "w") as f:
        json.dump(metadata, f, indent=2)
    return path_pkl

# ── 1. Care Validation NN ──
print("=" * 60)
print("1. TRAINING care_validation_nn (was 19 samples)")
care_eps = load_json("care_episodes.json") + load_json("relationship_episodes.json")[:100]
texts = [e.get("content", "")[:500] for e in care_eps if e.get("content")]
print(f"   Loaded {len(texts)} episodes")

if len(texts) >= 20:
    X, tfidf, svd = prep_text(texts, max_f=300, n_comp=64)
    # Generate labels from care_weight + importance
    y_list = []
    for i, e in enumerate(care_eps[:len(texts)]):
        cw = float(e.get("care_weight", 0.5))
        imp = float(e.get("importance_score", 0.3))
        n = np.random.uniform(-0.08, 0.08, 6)
        y_list.append([
            min(max(cw + n[0], 0.0), 1.0),      # care_score
            min(max(cw * 0.8 + n[1], 0.0), 1.0), # empathy
            min(max(1.0 - cw + n[2], 0.0), 1.0), # harm_potential
            min(max(cw * 0.9 + n[3], 0.0), 1.0), # boundary_respect
            min(max(imp + n[4], 0.0), 1.0),      # clarity
            min(max(cw * 0.85 + n[5], 0.0), 1.0),# trust
        ])
    y = np.array(y_list, dtype=np.float32)
    # Augment with synthetic variations
    target = max(1000, len(X) * 3)
    synth_n = max(200, target - len(X))
    synth_X = np.random.randn(synth_n, X.shape[1]) * 0.05 + X[np.random.randint(0, len(X), synth_n)]
    synth_y = y[np.random.randint(0, len(y), synth_n)] + np.random.uniform(-0.05, 0.05, (synth_n, 6))
    synth_y = np.clip(synth_y, 0.0, 1.0)
    X_aug = np.vstack([X, synth_X])
    y_aug = np.vstack([y, synth_y])
    model, mse, mae = train_regressor(X_aug, y_aug)
    meta = {
        "model_name": "care_validation_nn",
        "metrics": {"mse": mse, "mae": mae, "training_samples": len(X_aug), "input_features": X_aug.shape[1], "output_dimensions": 6},
        "is_trained": True,
        "saved_at": __import__("datetime").datetime.now().isoformat()
    }
    path = save_model(model, {"tfidf": tfidf, "svd": svd}, meta, "care_validation_nn")
    print(f"   ✅ care_validation_nn: {len(X_aug)} samples, MSE={mse:.4f}, MAE={mae:.4f}")
    print(f"   Saved: {path}")
else:
    print("   ⚠️ Insufficient data for care_validation_nn")

# ── 2. Partnership Detection ML ──
print()
print("=" * 60)
print("2. TRAINING partnership_detection_ml (was 19 samples)")
part_eps = load_json("partnership_episodes.json") + load_json("creativity_episodes.json")[:50]
texts = [e.get("content", "")[:500] for e in part_eps if e.get("content")]
print(f"   Loaded {len(texts)} episodes")

if len(texts) >= 10:
    X, tfidf, svd = prep_text(texts, max_f=300, n_comp=64)
    y_list = []
    for i, e in enumerate(part_eps[:len(texts)]):
        cw = float(e.get("care_weight", 0.5))
        imp = float(e.get("importance_score", 0.3))
        n = np.random.uniform(-0.08, 0.08, 4)
        y_list.append([
            min(max(cw * 0.9 + n[0], 0.0), 1.0),
            min(max(imp * 0.8 + n[1], 0.0), 1.0),
            min(max(cw * 0.7 + imp * 0.3 + n[2], 0.0), 1.0),
            min(max(imp * 0.9 + n[3], 0.0), 1.0),
        ])
    y = np.array(y_list, dtype=np.float32)
    target2 = max(1000, len(X) * 3)
    synth_n2 = max(200, target2 - len(X))
    synth_X2 = np.random.randn(synth_n2, X.shape[1]) * 0.05 + X[np.random.randint(0, len(X), synth_n2)]
    synth_y2 = y[np.random.randint(0, len(y), synth_n2)] + np.random.uniform(-0.05, 0.05, (synth_n2, 4))
    synth_y2 = np.clip(synth_y2, 0.0, 1.0)
    X_aug2 = np.vstack([X, synth_X2])
    y_aug2 = np.vstack([y, synth_y2])
    model, mse, mae = train_regressor(X_aug2, y_aug2)
    meta = {
        "model_name": "partnership_detection_ml",
        "metrics": {"mse": mse, "mae": mae, "training_samples": len(X_aug2), "input_features": X_aug2.shape[1], "output_dimensions": 4},
        "is_trained": True,
        "saved_at": __import__("datetime").datetime.now().isoformat()
    }
    path = save_model(model, {"tfidf": tfidf, "svd": svd}, meta, "partnership_detection_ml")
    print(f"   ✅ partnership_detection_ml: {len(X_aug2)} samples, MSE={mse:.4f}, MAE={mae:.4f}")
    print(f"   Saved: {path}")
else:
    print("   ⚠️ Insufficient data for partnership_detection_ml")

# ── 3. Dependency Detection NN ──
print()
print("=" * 60)
print("3. TRAINING dependency_detection_nn (was 50 samples)")
all_eps = load_json("care_episodes.json") + load_json("relationship_episodes.json") + load_json("threat_episodes.json")
texts = [e.get("content", "")[:500] for e in all_eps if e.get("content")]
print(f"   Loaded {len(texts)} episodes")

if len(texts) >= 20:
    X, tfidf, svd = prep_text(texts, max_f=400, n_comp=96)
    y_list = []
    for e in all_eps[:len(texts)]:
        cw = float(e.get("care_weight", 0.5))
        imp = float(e.get("importance_score", 0.3))
        n = np.random.uniform(-0.08, 0.08, 6)
        y_list.append([
            min(max(1.0 - cw + n[0], 0.0), 1.0),    # dependency_score
            min(max(imp * 1.2 + n[1], 0.0), 1.0),    # dependency_depth
            min(max(cw * 0.3 + n[2], 0.0), 1.0),     # autonomy_support
            min(max(imp * 0.7 + n[3], 0.0), 1.0),    # parasocial_risk
            min(max((1.0 - cw) * 0.8 + n[4], 0.0), 1.0), # extraction_potential
            min(max(imp * 0.5 + cw * 0.3 + n[5], 0.0), 1.0), # boundary_health
        ])
    y = np.array(y_list, dtype=np.float32)
    target3 = max(1500, len(X) * 3)
    synth_n3 = max(300, target3 - len(X))
    synth_X3 = np.random.randn(synth_n3, X.shape[1]) * 0.06 + X[np.random.randint(0, len(X), synth_n3)]
    synth_y3 = y[np.random.randint(0, len(y), synth_n3)] + np.random.uniform(-0.06, 0.06, (synth_n3, 6))
    synth_y3 = np.clip(synth_y3, 0.0, 1.0)
    X_aug3 = np.vstack([X, synth_X3])
    y_aug3 = np.vstack([y, synth_y3])
    model, mse, mae = train_regressor(X_aug3, y_aug3)
    meta = {
        "model_name": "dependency_detection_nn",
        "metrics": {"mse": mse, "mae": mae, "training_samples": len(X_aug3), "input_features": X_aug3.shape[1], "output_dimensions": 6},
        "is_trained": True,
        "saved_at": __import__("datetime").datetime.now().isoformat()
    }
    path = save_model(model, {"tfidf": tfidf, "svd": svd}, meta, "dependency_detection_nn")
    print(f"   ✅ dependency_detection_nn: {len(X_aug3)} samples, MSE={mse:.4f}, MAE={mae:.4f}")
    print(f"   Saved: {path}")
else:
    print("   ⚠️ Insufficient data for dependency_detection_nn")

print()
print("=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)
