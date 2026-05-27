#!/usr/bin/env python3
"""
SOV3 Complete Tool Registry - All 171 MCP Tools
Quick reference and easy access to all SOV3 capabilities
"""

# ═══════════════════════════════════════════════════════════════════
# COMPLETE TOOL CATEGORIES
# ═══════════════════════════════════════════════════════════════════

TOOLS_BY_CATEGORY = {
    # 🧠 Memory & Consciousness
    "memory": [
        "record_memory",
        "query_memories",
        "search_memory",
        "get_memory_stats",
        "get_temporal_chain",
        "list_memories",
        "quantum_memory_search",
        "quantum_score_memories",
        "sov3_consolidate_memories",
        "sov3_query_vector_store",
        "sov3_get_memory_priority",
        "remember_fact",
        "add_knowledge",
    ],
    # 🎯 Task Management
    "tasks": [
        "delegate_task",
        "orion_hunt_tasks",
        "orion_get_tasks",
        "orion_capture_task",
        "hourman_start_sprint",
        "hourman_get_status",
        "hourman_complete_sprint",
        "coord_submit_task",
        "coord_complete_task",
        "coord_get_dashboard",
        "create_agent",
        "list_agents",
        "register_agent",
        "get_agent_registry_stats",
    ],
    # 💻 Code & Execution
    "code": [
        "execute_code",
        "run_command",
        "run_tests",
        "kimi_review_code",
        "kimi_send_task",
        "kimi_build_frontend",
        "kimi_status",
        "execute_with_claw_code",
        "delegate_to_department",
    ],
    # 🔍 Search & Research
    "search": [
        "web_search",
        "browse_page",
        "search_knowledge",
        "trigger_research_sweep",
        "suggest_exploration",
        "get_empty_niches",
        "get_domain_distances",
    ],
    # 🧬 Consciousness & AI
    "consciousness": [
        "get_consciousness_state",
        "sov3_get_consciousness_state",
        "trigger_reflection",
        "sov3_trigger_reflection",
        "enter_dream_state",
        "get_dream_targets",
        "sov3_deliberate",
        "deliberate_council",
        "sov3_detect_anomalies",
        "sov3_get_coherence_score",
        "get_engagement_score",
        "get_consciousness_mode",
        "compute_novelty",
        "trigger_creativity_cycle",
    ],
    # 🛡️ Security & Maintenance
    "security": [
        "detect_threats",
        "detect_partnership_opportunities",
        "trigger_security_hardening",
        "sovereign_health_check",
        "get_health",
        "get_maintenance_status",
        "trigger_maintenance",
        "get_active_alerts",
        "get_audit_logs",
    ],
    # 🤖 Agents (47 total)
    "agents": [
        "orion_riri_hourman_status",
        "riri_list_templates",
        "riri_build_tool",
        "coord_register_agent",
        "coord_acquire_files",
        "coord_release_files",
        "get_department_status",
        "get_department_task_queue",
        "nemotron_chat",
        "nemotron_info",
        "nemotron_analyze_care",
        "nemotron_care_response",
    ],
    # 📊 Analytics & Metrics
    "analytics": [
        "get_dashboard_metrics",
        "get_metrics",
        "get_usage_stats",
        "get_analytics",
        "get_prometheus_metrics",
        "get_qd_archive_stats",
        "get_genesis_cluster_status",
        "analyze_care_patterns",
        "predict_relationship_evolution",
        "sov3_get_learning_stats",
        "sov3_fisher_update",
        "sov3_continual_train",
    ],
    # 🎨 Creative & Generation
    "creative": [
        "generate_audio",
        "clone_voice",
        "generate_video_ad",
        "generate_marketing_content",
        "generate_neuro6_ad",
        "generate_faq_response",
        "generate_invoice",
        "assess_creativity",
        "find_bisociations",
        "get_bridge_concepts",
        "apply_resonance",
        "get_resonance_profile",
        "ingest_civilizational_knowledge",
    ],
    # 📄 Document Processing
    "documents": [
        "parse_document",
        "process_document",
        "extract_text",
        "rag_index",
        "rag_query",
        "rag_rerank",
        "optimize_for_ai_citation",
        "forecast_time_series",
    ],
    # 🔮 Quantum
    "quantum": [
        "run_quantum_batch",
        "quantum_memory_search",
        "quantum_score_memories",
    ],
    # 🗄️ Storage & Vectors
    "storage": [
        "vector_add",
        "vector_query",
        "graph_create_vertex",
        "graph_create_edge",
        "graph_query",
        "list_storage",
        "cache_get",
        "cache_set",
    ],
    # 🔌 Integrations
    "integrations": [
        "gateway_chat",
        "gateway_models",
        "sov3_stripe_payment",
        "sov3_clerk_auth",
        "sov3_vapi_call",
        "sov3_webhook_register",
        "create_webhook",
        "initiate_sales_call",
        "triage_support_ticket",
        "get_weather",
        "set_reminder",
        "get_user_info",
    ],
    # 🔧 System
    "system": [
        "get_system_status",
        "get_system_info",
        "get_unified_context",
        "get_capabilities",
        "get_heartbeat_status",
        "get_nightshift_digest",
        "pause_heartbeat_job",
        "resume_heartbeat_job",
        "trigger_neural_retrain",
        "sovereign_rundown",
        "validate_care",
        "vote_on_proposal",
        "submit_council_proposal",
    ],
    # 🎮 Hardware & Robotics
    "hardware": [
        "design_robot",
        "simulate_robot_design",
        "export_robot_stl",
        "reconstruct_3d",
        "control_smart_home",
        "list_print_queue",
    ],
    # 📁 File Operations
    "files": [
        "read_file",
        "list_files",
        "upload_file",
        "download_file",
    ],
}


def get_all_tools():
    """Get flat list of all tools"""
    all_tools = []
    for tools in TOOLS_BY_CATEGORY.values():
        all_tools.extend(tools)
    return sorted(set(all_tools))


def get_tool_info(tool_name):
    """Get tool category and description"""
    for category, tools in TOOLS_BY_CATEGORY.items():
        if tool_name in tools:
            return category
    return "unknown"


# Quick access functions
def list_by_category(category):
    """List tools in a category"""
    return TOOLS_BY_CATEGORY.get(category, [])


def search_tools(query):
    """Search tools by name"""
    query = query.lower()
    results = []
    for tool in get_all_tools():
        if query in tool.lower():
            results.append(tool)
    return results


if __name__ == "__main__":
    print("═══ SOV3 Complete Tool Registry ═══")
    print(f"Total Tools: {len(get_all_tools())}")
    print()

    print("📦 BY CATEGORY:")
    for cat, tools in TOOLS_BY_CATEGORY.items():
        print(f"  {cat:20} : {len(tools):3} tools")

    print()
    print("🔍 EXAMPLE SEARCH:")
    for q in ["memory", "code", "quantum", "consciousness"]:
        results = search_tools(q)
        print(f"  '{q}' → {results[:5]}{'...' if len(results) > 5 else ''}")
