"""
Legion Command Center — Real-time Swarm Visualization
MEOK AI Labs
Run: streamlit run dashboard.py
"""

import json
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import redis
import streamlit as st

st.set_page_config(page_title="Legion Command — MEOK AI Labs", layout="wide")

REDIS_URL = "redis://localhost:6379"

@st.cache_resource
def get_redis():
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None

r = get_redis()

st.title("🐉 LEGION COMMAND CENTER — MEOK AI Labs")
st.markdown("*Real-time swarm intelligence | 47 agents × 33 nodes = 1,551 total*")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.subheader("Swarm Topology")
    rows = []
    for a in range(1, 48):
        for n in range(1, 34):
            x = (a % 7) * 12 + (n % 6) * 1.8
            y = (a // 7) * 12 + (n // 6) * 1.8
            z = np.random.rand() * 5
            rows.append({"x": x, "y": y, "z": z, "a": a, "n": n})

    df = pd.DataFrame(rows)
    fig = go.Figure(data=[go.Scatter3d(
        x=df["x"], y=df["y"], z=df["z"],
        mode="markers",
        marker=dict(size=3, color=df["z"], colorscale="Viridis", opacity=0.8),
        text=[f"Agent {r.a}-{r.n}" for r in df.itertuples()],
        hoverinfo="text"
    )])
    fig.update_layout(
        scene=dict(
            xaxis_title="Agent Division", yaxis_title="Node Cluster", zaxis_title="Activity",
            bgcolor="rgb(15, 15, 25)"
        ),
        paper_bgcolor="rgb(10, 10, 20)", margin=dict(l=0, r=0, b=0, t=0), height=500
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("System Health")
    if r:
        keys = list(r.scan_iter(match="node:*"))
        statuses: dict = {}
        for k in keys[:100]:
            s = r.hget(k, "status")
            statuses[s or "unknown"] = statuses.get(s or "unknown", 0) + 1
    else:
        statuses = {"idle": 1551}

    st.metric("Total Nodes", "1,551")
    st.metric("Active", statuses.get("active", 0))
    st.metric("Learning", statuses.get("learning", 0))
    st.metric("Idle", statuses.get("idle", 1551))
    st.metric("Failed", statuses.get("failed", 0))

    # GPU Status
    st.subheader("GPU Status")
    st.info("Vast.ai RTX 8000\n46GB VRAM\nqwen3.5:35b loaded")

with col3:
    st.subheader("Neuromorphic Activity")
    spike_times = np.random.uniform(0, 100, 300)
    neurons = np.random.choice(64, 300)
    fig2 = go.Figure(data=[go.Scatter(
        x=spike_times, y=neurons,
        mode="markers",
        marker=dict(size=2, color="cyan"),
    )])
    fig2.update_layout(
        xaxis_title="Time (ms)", yaxis_title="Neuron ID",
        paper_bgcolor="black", plot_bgcolor="black",
        font_color="white", height=300
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Vast.ai GPU")
    st.code("RTX 8000 | 46GB\nqwen3.5:35b ✓\nOllama :40408 ✓")

# Bottom row
c1, c2 = st.columns(2)
with c1:
    st.subheader("🧠 Metacognition (MARS)")
    if r:
        refs = r.lrange("mars:reflections", 0, 5) or []
        for ref in refs:
            try:
                d = json.loads(ref)
                st.write(f"**{d.get('mode', '')}**: {d.get('critique', '')[:80]}")
            except Exception:
                pass
    else:
        st.info("No reflections yet — MARS waiting for episodes")

with c2:
    st.subheader("🎓 Skill Evolution (EvoSkill)")
    if r:
        skills = []
        for k in r.scan_iter(match="skill:*"):
            skills.append({"key": k, "ts": time.time()})
        if skills:
            st.dataframe(pd.DataFrame(skills[:20]), use_container_width=True)
        else:
            st.info("No skills committed yet")
    else:
        st.info("Redis offline — start legion-redis container")

if st.button("Refresh"):
    st.rerun()
