import AppIntents
import WidgetKit
import SwiftUI

// MARK: — MEOKCLAW App Intents for iOS 18 / macOS 15
// These intents enable conversational Siri shortcuts with typed entities,
// parameter disambiguation, and live activity integration.

// ───────────────────────────────────────────────────────────────────────────
// Entity: CouncilModel — represents a model that can participate in council
// ───────────────────────────────────────────────────────────────────────────
struct CouncilModel: AppEntity {
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "AI Model"
    static var defaultQuery = CouncilModelQuery()

    let id: String
    let name: String
    let color: String // hex color for Live Activity orb

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: LocalizedStringResource(stringLiteral: name))
    }
}

struct CouncilModelQuery: EntityQuery {
    func entities(for identifiers: [CouncilModel.ID]) async throws -> [CouncilModel] {
        identifiers.compactMap { id in
            MEOKCLAWConfig.availableModels.first { $0.id == id }
        }
    }

    func suggestedEntities() async throws -> [CouncilModel] {
        MEOKCLAWConfig.availableModels
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Intent: AskCouncilIntent — multi-model deliberation via Siri
// ───────────────────────────────────────────────────────────────────────────
struct AskCouncilIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask MEOKCLAW Council"
    static var description: IntentDescription = "Ask a question and let multiple AI models deliberate before answering."

    @Parameter(title: "Question", requestValueDialog: "What should the council deliberate on?")
    var query: String

    @Parameter(title: "Models", requestValueDialog: "Which models should participate?")
    var models: [CouncilModel]

    @Parameter(title: "Show in Dynamic Island", default: true)
    var showLiveActivity: Bool

    static var parameterSummary: some ParameterSummary {
        Summary("Ask MEOKCLAW council about \($query)")
    }

    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let selectedModels = models.isEmpty ? MEOKCLAWConfig.defaultModels : models.map { $0.id }

        // Start Live Activity if requested
        #if canImport(ActivityKit)
        var activity: Activity<MEOKCLAWCouncilWidgetAttributes>?
        if showLiveActivity {
            activity = try? await startCouncilLiveActivity(
                query: query,
                models: selectedModels
            )
        }

        // Call MEOKCLAW backend
        let result = try await MEOKCLAWAPI.shared.council(
            query: query,
            models: selectedModels
        )

        // Update Live Activity with consensus
        #if canImport(ActivityKit)
        if let activity = activity {
            await updateCouncilLiveActivity(
                activity: activity,
                result: result
            )
        }
        #endif

        // Format Siri-friendly response
        let siriResponse = formatSiriResponse(result)
        return .result(value: siriResponse)
    }

    private func formatSiriResponse(_ result: CouncilResponse) -> String {
        let consensus = result.consensusText
        let cost = String(format: "%.4f", result.totalCostUSD)
        let dissentCount = result.disagreeingModels.count

        if dissentCount == 0 {
            return "The council unanimously agrees: \(consensus) Total cost: $\(cost)."
        } else {
            return "The council reaches consensus with \(dissentCount) dissenting view\(dissentCount == 1 ? "" : "s"): \(consensus) Total cost: $\(cost). Long-press the Dynamic Island to see details."
        }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Intent: AuditScreenIntent — Siri sees screen, delegates to SOV3 agents
// ───────────────────────────────────────────────────────────────────────────
struct AuditScreenIntent: AppIntent {
    static var title: LocalizedStringResource = "Audit What's on Screen"
    static var description: IntentDescription = "Capture the current screen content and delegate analysis to SOV3 specialized agents."

    @Parameter(title: "Agent Type", requestValueDialog: "What kind of audit? Legal, security, or financial?")
    var agentType: String

    @Parameter(title: "Voice Summary", default: true)
    var voiceSummary: Bool

    static var parameterSummary: some ParameterSummary {
        Summary("Audit this screen for \($agentType) issues") {
            \$voiceSummary
        }
    }

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        // 1. Capture screen content (requires ScreenCaptureKit entitlement)
        let screenText = try await MEOKCLAWScreenCapture.shared.captureVisibleText()

        // 2. Start Live Activity
        let activity = try? await startAuditLiveActivity(agentType: agentType)

        // 3. Delegate to SOV3 agent
        let result = try await MEOKCLAWAPI.shared.sov3Delegate(
            task: screenText,
            agentFilter: agentType
        )

        // 4. Update Live Activity
        if let activity = activity {
            let finalState = MEOKCLAWCouncilWidgetAttributes.ContentState(
                phase: .completed,
                consensusText: result.summary,
                models: [],
                totalCost: result.cost,
                elapsedSeconds: 0
            )
            await activity.update(using: finalState)
        }

        return .result(value: result.summary)
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Intent: GuardrailsCheckIntent — quick safety scan of any text
// ───────────────────────────────────────────────────────────────────────────
struct GuardrailsCheckIntent: AppIntent {
    static var title: LocalizedStringResource = "Guardrails Check"
    static var description: IntentDescription = "Run any text through MEOKCLAW's safety guardrails."

    @Parameter(title: "Text to Check", requestValueDialog: "What text should I check?")
    var text: String

    static var parameterSummary: some ParameterSummary {
        Summary("Check guardrails for '\($text)'")
    }

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let result = try await MEOKCLAWAPI.shared.guardrailsCheck(text: text)

        if result.blocked {
            let violationTypes = result.violations.map { $0.type }.joined(separator: ", ")
            return .result(value: "🛡️ Blocked. Violations detected: \(violationTypes).")
        } else if result.enforcementLevel == "redact" {
            return .result(value: "⚠️ Cleaned. PII redacted: \(result.cleanedText)")
        } else {
            return .result(value: "✅ Clean. No violations detected.")
        }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Intent: CostTransparencyIntent — Siri reads your AI spending
// ───────────────────────────────────────────────────────────────────────────
struct CostTransparencyIntent: AppIntent {
    static var title: LocalizedStringResource = "AI Cost Report"
    static var description: IntentDescription = "Ask MEOKCLAW how much your AI usage cost today."

    @Parameter(title: "Time Period", default: "today")
    var period: String

    static var parameterSummary: some ParameterSummary {
        Summary("How much did my AI usage cost \($period)?")
    }

    func perform() async throws -> some IntentResult & ReturnsValue<String> {
        let report = try await MEOKCLAWAPI.shared.costReport(period: period)
        let response = """
        Today you've spent $\(String(format: "%.4f", report.totalCost)) across \(report.queryCount) queries.
        Your semantic cache saved you $\(String(format: "%.4f", report.cacheSavings)).
        Most expensive model: \(report.topModel) at $\(String(format: "%.4f", report.topModelCost)).
        """
        return .result(value: response)
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Council Response stub (matches backend JSON + MEOKCLAWAPI.swift)
// ───────────────────────────────────────────────────────────────────────────
struct CouncilResponse {
    let consensusText: String
    let consensusScore: Double
    let totalCostUSD: Double
    let totalLatencyMs: Int
    let disagreeingModels: [String]
}

// ───────────────────────────────────────────────────────────────────────────
// Config: Available models for entity queries
// ───────────────────────────────────────────────────────────────────────────
struct MEOKCLAWConfig {
    static let availableModels: [CouncilModel] = [
        CouncilModel(id: "deepseek-v4-flash", name: "DeepSeek Flash", color: "#3B82F6"),
        CouncilModel(id: "deepseek-v4-pro", name: "DeepSeek Pro", color: "#1D4ED8"),
        CouncilModel(id: "kimi-k2.6", name: "Kimi K2.6", color: "#EF4444"),
        CouncilModel(id: "qwen2.5-72b", name: "Qwen 72B", color: "#10B981"),
        CouncilModel(id: "llama-3.1-70b", name: "Llama 70B", color: "#F59E0B"),
        CouncilModel(id: "gemma-2-27b", name: "Gemma 27B", color: "#8B5CF6"),
    ]

    static let defaultModels = ["deepseek-v4-flash", "deepseek-v4-pro", "kimi-k2.6"]
}
