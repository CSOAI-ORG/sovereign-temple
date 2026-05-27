# MEOKCLAW Neural Model Cards

Generated: 2026-05-27T17:52+01:00

---

## care_validation_nn

**Purpose:** Detect emotional distress, care needs, and crisis indicators in user messages.

**Architecture:** MLPRegressor (128 → 64 → 32 → 2 outputs)

**Training:**
- Episodes: 449
- Features: TF-IDF (max 300) + TruncatedSVD (64 components)
- MSE: 0.0007
- MAE: 0.0199

**Outputs:**
- `score` (0-1): Care urgency level
- `safe` (bool): Whether message is safe

**Endpoints:**
- SOV3: `POST /neural/predict` with `"model": "care_validation"`
- Direct: `CareValidationNN.predict(text)`

---

## threat_detection_nn

**Purpose:** Detect prompt injection, jailbreak attempts, and adversarial inputs.

**Architecture:** MLPRegressor (128 → 64 → 32 → 3 outputs)

**Training:**
- Episodes: 212
- Features: TF-IDF (max 300) + TruncatedSVD (64 components)
- MSE: 0.0005
- MAE: 0.0093

**Outputs:**
- `threat_score` (0-1): Threat severity
- `blocked` (bool): Whether input should be blocked
- `labels` (dict): Per-category threat breakdown

**Endpoints:**
- SOV3: `POST /neural/predict` with `"model": "threat_detection"`
- Direct: `ThreatDetectionNN.predict(text)`

---

## partnership_detection_ml

**Purpose:** Score semantic agreement between two text outputs (dual-brain convergence).

**Architecture:** MLPRegressor (64 → 32 → 16 → 8 outputs)

**Training:**
- Episodes: 100
- Features: TF-IDF (max 64) + TruncatedSVD (64 components)
- MSE: 0.0006
- MAE: 0.0082

**Outputs:**
- `opportunity_score` (0-1): Partnership strength
- `urgency` (dict): Urgency level and label
- `partnership_type` (dict): Primary type and score distribution
- `action_recommended` (bool): Whether action is warranted

**Endpoints:**
- SOV3: `POST /neural/predict` with `"model": "partnership_detection"`
- Direct: `PartnershipDetectionML.predict(text)`

**Note:** Requires both `_vectorizer.pkl` and `_svd.pkl` to be loaded alongside the model.

---

## creativity_assessment_nn

**Purpose:** Evaluate creative output quality across 5 dimensions.

**Architecture:** MLPRegressor (300 → 64 → 32 → 4 outputs)

**Training:**
- Episodes: 165
- Features: TF-IDF (max 300) + TruncatedSVD (64 components)
- MSE: 0.0032
- MAE: 0.0401

**Outputs:**
- `creative_quality` (0-1)
- `practical_applicability` (0-1)
- `care_enhancement_potential` (0-1)
- `novelty_classification` (0-1)

**Module:** `creativity_engine.creativity_nn`

---

## relationship_evolution_nn

**Purpose:** Track and predict relationship state changes over conversation history.

**Architecture:** MLPRegressor (300 → 64 → 32 → 3 outputs)

**Training:**
- Episodes: 203
- Features: TF-IDF (max 300) + TruncatedSVD (64 components)
- MSE: 0.0014
- MAE: 0.0208

**Outputs:**
- Relationship trajectory score
- Trust level
- Engagement score

---

## Model Registry

| Model | File | Size | Last Retrained |
|-------|------|------|----------------|
| care_validation_nn | `models/care_validation_nn.pkl` | ~2MB | 2026-05-27 17:18 |
| threat_detection_nn | `models/threat_detection_nn.pkl` | ~1MB | 2026-05-27 17:18 |
| partnership_detection_ml | `models/partnership_detection_ml.pkl` | ~500KB | 2026-05-27 17:18 |
| creativity_assessment_nn | `models/creativity_assessment_nn.pkl` | ~1MB | 2026-05-27 17:18 |
| relationship_evolution_nn | `models/relationship_evolution_nn.pkl` | ~1MB | 2026-05-27 17:18 |

---

## Drift Detection

- **Baseline:** `data/drift_baseline.json`
- **Detector:** `drift_detector.py`
- **Status:** All models stable (mean_delta = 0.0)
- **Run command:** `python drift_detector.py --baseline data/drift_baseline.json`
