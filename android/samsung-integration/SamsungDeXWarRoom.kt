package com.meokclaw.samsung.dex

import android.app.Activity
import android.content.Context
import android.content.res.Configuration
import android.hardware.display.DisplayManager
import android.os.Bundle
import android.view.Display
import android.widget.FrameLayout
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * MEOKCLAW DeX War Room — Desktop Command Center
 *
 * When Samsung DeX activates, this Activity launches as the primary desktop UI.
 * It transforms the Galaxy phone/tablet into a full MEOKCLAW command center:
 *
 *   - Dual-pane council UI (query + live model responses)
 *   - Cost dashboard with real-time ticker
 *   - S Pen annotation on model responses
 *   - Multi-monitor support (each model gets its own window)
 *   - Korean enterprise keyboard shortcuts (Ctrl+Enter = run council)
 *
 * Why unique: No AI platform has a native DeX desktop app.
 * ChatGPT's Android app is a phone app in a window.
 * MEOKCLAW is a native desktop experience.
 */
class SamsungDeXWarRoom : Activity() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private lateinit var apiClient: MEOKCLAWApiClient
    private val _councilState = MutableStateFlow<CouncilUiState>(CouncilUiState.Idle)
    val councilState: StateFlow<CouncilUiState> = _councilState

    // UI Components
    private lateinit var queryInput: CouncilQueryInput
    private lateinit var modelResponsePanel: ModelResponsePanel
    private lateinit var costDashboard: CostDashboard
    private lateinit var consensusVisualizer: ConsensusVisualizer
    private lateinit var modelOrbDock: ModelOrbDock

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Detect DeX mode and configure layout
        val isDeX = isDeXMode()
        val hasExternalDisplay = hasExternalDisplay()

        if (isDeX) {
            setupDeXLayout()
        } else {
            setupPhoneLayout()
        }

        apiClient = MEOKCLAWApiClient(
            baseUrl = getLocalNodeUrl(),
            apiKey = getApiKeyFromKnox()
        )

        // Register S Pen event listener for annotation
        setupSPenListener()

        // Register keyboard shortcuts
        setupKeyboardShortcuts()
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Layout Setup
    // ─────────────────────────────────────────────────────────────────────────

    private fun setupDeXLayout() {
        // DeX layout: 3-column desktop
        // Left: Query input + model selector
        // Center: Live model response stream
        // Right: Cost dashboard + consensus visualization
        setContentView(R.layout.dex_war_room)

        queryInput = findViewById(R.id.query_input)
        modelResponsePanel = findViewById(R.id.model_response_panel)
        costDashboard = findViewById(R.id.cost_dashboard)
        consensusVisualizer = findViewById(R.id.consensus_visualizer)
        modelOrbDock = findViewById(R.id.model_orb_dock)

        // Multi-monitor: if external display connected, launch model windows
        if (hasExternalDisplay()) {
            launchExternalModelWindows()
        }
    }

    private fun setupPhoneLayout() {
        // Phone layout: single column with bottom sheet for details
        setContentView(R.layout.phone_war_room)
        // ... similar initialization
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Council Execution
    // ─────────────────────────────────────────────────────────────────────────

    fun runCouncil(query: String, selectedModels: List<String>) {
        _councilState.value = CouncilUiState.Deliberating(
            query = query,
            models = selectedModels.map { id ->
                ModelUiState(
                    id = id,
                    name = getModelName(id),
                    color = getModelColor(id),
                    status = ModelStatus.THINKING,
                    response = "",
                    cost = 0.0,
                    latencyMs = 0
                )
            },
            elapsedMs = 0,
            totalCost = 0.0
        )

        scope.launch {
            try {
                val startTime = System.currentTimeMillis()

                // Start progress ticker
                val tickerJob = launch {
                    while (isActive) {
                        delay(100)
                        val elapsed = System.currentTimeMillis() - startTime
                        updateElapsedTime(elapsed)
                    }
                }

                val result = apiClient.council(
                    prompt = query,
                    models = selectedModels
                )

                tickerJob.cancel()

                _councilState.value = CouncilUiState.Consensus(
                    query = query,
                    consensusText = result.consensusText,
                    consensusScore = result.consensusScore,
                    models = result.models.map { m ->
                        ModelUiState(
                            id = m.model,
                            name = getModelName(m.model),
                            color = getModelColor(m.model),
                            status = if (result.disagreeingModels.contains(m.model))
                                ModelStatus.DISSENTING else ModelStatus.DONE,
                            response = m.text,
                            cost = m.cost_usd,
                            latencyMs = m.latency_ms
                        )
                    },
                    totalCost = result.totalCostUSD,
                    totalLatencyMs = result.totalLatencyMs,
                    disagreeingModels = result.disagreeingModels
                )

                // Update cost dashboard
                costDashboard.update(result)
                consensusVisualizer.visualize(result)

            } catch (e: Exception) {
                _councilState.value = CouncilUiState.Error(e.message ?: "Unknown error")
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // S Pen Annotation
    // ─────────────────────────────────────────────────────────────────────────

    private fun setupSPenListener() {
        // S Pen hover detection for quick actions
        // S Pen button click = annotate selected text
        // S Pen double-click = send annotated text to council
        // S Pen air actions = scroll through model responses

        val spenDetector = SPenDetector(this)
        spenDetector.onHover { x, y ->
            val modelView = findModelViewAt(x, y)
            modelView?.highlight()
        }
        spenDetector.onButtonClick { x, y ->
            val selectedText = getSelectedText()
            if (selectedText.isNotBlank()) {
                showAnnotationMenu(selectedText)
            }
        }
    }

    private fun showAnnotationMenu(text: String) {
        // Show floating menu:
        // - "Send to council"
        // - "Guardrails check"
        // - "Translate to English"
        // - "Explain like I'm 5"
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Keyboard Shortcuts (Korean Enterprise)
    // ─────────────────────────────────────────────────────────────────────────

    private fun setupKeyboardShortcuts() {
        // Ctrl+Enter = Run council
        // Ctrl+Shift+C = Copy consensus
        // Ctrl+Shift+D = Show dissenting views
        // Ctrl+Shift+S = Save to Samsung Notes
        // Ctrl+Shift+K = KakaoTalk share
        // F1 = Help (Korean)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Multi-Monitor: Each model gets its own window
    // ─────────────────────────────────────────────────────────────────────────

    private fun launchExternalModelWindows() {
        val displayManager = getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        val displays = displayManager.displays

        if (displays.size > 1) {
            // Launch each model response in its own window on secondary displays
            displays.drop(1).forEachIndexed { index, display ->
                val modelId = DEFAULT_MODELS.getOrNull(index) ?: return@forEachIndexed
                launchModelWindow(display, modelId)
            }
        }
    }

    private fun launchModelWindow(display: Display, modelId: String) {
        val options = Bundle().apply {
            putInt("android.activity.launchDisplayId", display.displayId)
        }
        val intent = Intent(this, ModelResponseWindow::class.java).apply {
            putExtra("model_id", modelId)
        }
        startActivity(intent, options)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    private fun isDeXMode(): Boolean {
        return resources.configuration.uiMode and Configuration.UI_MODE_TYPE_MASK ==
                Configuration.UI_MODE_TYPE_DESK
    }

    private fun hasExternalDisplay(): Boolean {
        val displayManager = getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        return displayManager.displays.size > 1
    }

    private fun getLocalNodeUrl(): String {
        val prefs = getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
        return prefs.getString("local_node", "http://192.168.1.100:3201") ?: "http://192.168.1.100:3201"
    }

    private fun getApiKeyFromKnox(): String? {
        // Retrieve from Samsung Knox Keystore
        return null
    }

    private fun getModelName(id: String): String = MODEL_NAMES[id] ?: id
    private fun getModelColor(id: String): String = MODEL_COLORS[id] ?: "#888888"

    private fun updateElapsedTime(elapsedMs: Long) {
        val current = _councilState.value
        if (current is CouncilUiState.Deliberating) {
            _councilState.value = current.copy(elapsedMs = elapsedMs)
        }
    }

    private fun findModelViewAt(x: Float, y: Float): ModelResponseView? {
        // Hit test for S Pen hover
        return null
    }

    private fun getSelectedText(): String {
        // Get currently selected text from focused view
        return ""
    }

    companion object {
        val DEFAULT_MODELS = listOf(
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "kimi-k2.6"
        )
        val MODEL_NAMES = mapOf(
            "deepseek-v4-flash" to "DeepSeek Flash",
            "deepseek-v4-pro" to "DeepSeek Pro",
            "kimi-k2.6" to "Kimi K2.6",
            "samsung-gauss-v1" to "삼성 가우스"
        )
        val MODEL_COLORS = mapOf(
            "deepseek-v4-flash" to "#3B82F6",
            "deepseek-v4-pro" to "#1D4ED8",
            "kimi-k2.6" to "#EF4444",
            "samsung-gauss-v1" to "#1428A0"
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────
// UI State Models
// ─────────────────────────────────────────────────────────────────────────
sealed class CouncilUiState {
    object Idle : CouncilUiState()
    data class Deliberating(
        val query: String,
        val models: List<ModelUiState>,
        val elapsedMs: Long,
        val totalCost: Double
    ) : CouncilUiState()
    data class Consensus(
        val query: String,
        val consensusText: String,
        val consensusScore: Double,
        val models: List<ModelUiState>,
        val totalCost: Double,
        val totalLatencyMs: Int,
        val disagreeingModels: List<String>
    ) : CouncilUiState()
    data class Error(val message: String) : CouncilUiState()
}

data class ModelUiState(
    val id: String,
    val name: String,
    val color: String,
    val status: ModelStatus,
    val response: String,
    val cost: Double,
    val latencyMs: Int
)

enum class ModelStatus {
    THINKING, DONE, DISSENTING, ERROR
}

// Stub classes for compilation
class CouncilQueryInput
class ModelResponsePanel
class CostDashboard
class ConsensusVisualizer
class ModelOrbDock
class SPenDetector(activity: Activity)
class ModelResponseView
class ModelResponseWindow : Activity()
class MEOKCLAWApiClient(baseUrl: String, apiKey: String?)
