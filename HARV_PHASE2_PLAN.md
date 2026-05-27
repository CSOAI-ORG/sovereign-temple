# HARV Phase 2 — Sovereign Local Geospatial Intelligence

**Status:** Planning / pre-deployment
**Farm:** Nick's 6.5-acre UK site
**Zones:** caravan studio · lab · field
**Integration point:** `/harv/camera_event` POST → ContextEnvelope → every SOV chat

---

## Architecture Overview

```
IP Cameras (x3, PoE)
        │ RTSP/ONVIF
        ▼
  Frigate NVR (Docker)
        │ MJPEG / RTSP sub-stream
        ▼
  DeepCamera (Docker, Mac Mini)
   ├─ YOLO26n/s/m detection (2–12ms)
   └─ Qwen2.5-VL-3B / SmolVLM-256M VLMs (80–300ms)
        │ detection JSON
        ▼
  CameraObjectMapper (COM)
   ├─ Raycasting + homography → UTM coords
   └─ Kalman IMU fusion
        │ GeoJSON features
        ▼
  QGIS 3.34+ (farm map)              Guardian ReAct Agent
   ├─ Temporal controller             ├─ Persistent working memory
   ├─ MovingPandas trajectories       ├─ Proactive alert rules
   └─ GeoTIFF farm substrate          └─ POST /harv/camera_event
                                               │
                                      HARV ContextEnvelope
                                       └─ every Sovereign chat
```

---

## Phase 2A — DeepCamera + Frigate NVR on Mac Mini

**Goal:** Live YOLO/VLM inference on 3 farm zones.

- Install Frigate NVR via Docker on Mac Mini; configure 3 RTSP streams
- Deploy DeepCamera Docker container with CoreML acceleration
- Camera placement:
  | Camera | Zone | Coverage |
  |--------|------|----------|
  | cam-01 | caravan studio | desk, door, workspace |
  | cam-02 | lab | bench, entrance, equipment |
  | cam-03 | field | perimeter, dog run, gate |
- Detection targets: dog, person, vehicle, package
- Output: JSON detections → `harv_guardian_bridge.py` → `/harv/camera_event`
- Target latency: <500ms end-to-end (frame → ContextEnvelope)

---

## Phase 2B — CameraObjectMapper + QGIS Farm Map

**Goal:** Georeferenced detections on a real farm map.

- Capture farm GeoTIFF base layer (drone survey or OS MasterMap tile)
- Set up UTM coordinate system for farm extents
- Configure COM homography matrices per camera (GCP correspondences)
- Load QGIS 3.34+ with:
  - Farm base layer (GeoTIFF)
  - Detection point layer (PostGIS or GeoPackage, time-enabled)
  - Dog + person trajectory layer (MovingPandas → GeoPackage)
  - Zone boundary polygons (caravan, lab, field)
- Install Trajectools plugin for stop detection and speed profiling
- Milvus vector DB (local Docker) for FastReID 128-dim embeddings

---

## Phase 2C — Guardian ReAct Agent + SOV Integration

**Goal:** Proactive farm awareness in every Sovereign conversation.

- Implement Guardian using ReAct (Reason + Act) architecture
- Persistent working memory: rolling 1hr detection buffer
- Alert rules (configurable thresholds):
  | Rule | Trigger | Zone |
  |------|---------|------|
  | dog_alert | dog not seen >2hr | field |
  | perimeter_alert | unknown person | field/lab boundary |
  | pc_active | Nick at workstation | caravan |
  | dog_walk | dog+person moving, outdoor corridor | field |
- Guardian POSTs structured events to `/harv/camera_event`
- HARV ContextEnvelope surface in every SOV chat prompt
- `harv_guardian_bridge.py` is the integration shim (Phase 2C bridge)

---

## Phase 2D — Person Re-ID + Dog Walking + PC Monitoring

**Goal:** Behavioural intelligence layer.

- **FastReID** (128-dim embeddings, 94.2% Rank-1 on Market-1501)
  - Enrolment: capture reference crops of Nick + each dog
  - Gallery stored in local Milvus instance
  - Cross-camera identity persistence without cloud
- **Dog walking detection** — SEQUENCE composite event:
  1. dog_detected + person_detected in same zone
  2. movement velocity 0.5–2.5 m/s
  3. outdoor corridor preference (field zone)
  4. duration >5min
- **PC workstation monitoring** via MediaPipe BlazePose pose estimation:
  - Seated posture + hand movement → `pc_activity` event
  - Idle detection → `pc_idle` event → updates HARV `pc_status`
- **Human activity classification** via VLM zero-shot prompts (SmolVLM-256M):
  - Prompt: "What is the person doing? Choose: working, walking, idle, unknown"

---

## Hardware Shopping List

| Item | Spec | Est. Cost |
|------|------|-----------|
| Mac Mini M2 (refurb) | 8GB unified memory, 256GB SSD | ~£500 |
| IP cameras x3 | PoE, 1080p, ONVIF, IR night vision | ~£150 (£50 ea) |
| PoE switch (8-port) | 802.3af/at, unmanaged | ~£40 |
| CAT6 cable + connectors | 50m reel + RJ45 crimps | ~£20 |
| **Total hardware** | | **~£710** |

---

## Software Stack

| Component | Version | Notes |
|-----------|---------|-------|
| DeepCamera | latest (Docker) | YOLO26 + VLMs, CoreML |
| Frigate NVR | 0.14+ | RTSP ingestion, motion zones |
| QGIS | 3.34+ (LTR) | Temporal controller, Trajectools |
| Milvus | 2.4+ (Docker) | FastReID embedding store |
| FastReID | latest | 128-dim person re-ID |
| MovingPandas | 0.18+ | Trajectory analysis |
| PyTorch (MPS) | 2.2+ | Metal acceleration fallback |
| Docker Desktop | 4.x | Container orchestration |

---

## Integration with Existing HARV

```python
# harv_guardian_bridge.py handles the bridge:
bridge = GuardianBridge(base_url="http://localhost:3200")
await bridge.on_detection("dog", 0.92, zone="field")
await bridge.on_activity("dog_walking", person_id="reid_0001", zone="field")

# sovereign-mcp-server.py exposes:
POST /harv/camera_event
→ harv.push_camera_event(event_type, label, confidence, zone, metadata)
→ deque(maxlen=50) buffered in HARVContext
→ get_envelope() surfaces last 5 events in every chat context
```

---

## Timeline (Suggested)

| Phase | Duration | Milestone |
|-------|----------|-----------|
| 2A | 1–2 weeks | Cameras live, detections flowing to /harv/camera_event |
| 2B | 1–2 weeks | QGIS farm map with georeferenced tracks |
| 2C | 1–2 weeks | Guardian alerts appearing in SOV chats |
| 2D | 2–4 weeks | Dog walking + Re-ID + PC monitoring |

---

*Blueprint source: Sovereign Local Geospatial Intelligence System (COMPASS-004)*
*Integration target: HARV Phase 2, Sovereign Temple v3.0*
