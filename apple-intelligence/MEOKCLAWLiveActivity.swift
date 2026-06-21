import ActivityKit
import WidgetKit
import SwiftUI

// MARK: — MEOKCLAW Live Activity (Dynamic Island + Lock Screen)
// Visualizes multi-model council deliberation in real time.
// Each model gets a colored orb. Consensus = orbs merge. Disagreement = orbs diverge.

// ───────────────────────────────────────────────────────────────────────────
// Activity Attributes
// ───────────────────────────────────────────────────────────────────────────
struct MEOKCLAWCouncilWidgetAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        enum CouncilPhase: String, Codable {
            case pending = "pending"
            case deliberating = "deliberating"
            case consensusReached = "consensus_reached"
            case disagreement = "disagreement"
            case blocked = "blocked"
            case completed = "completed"
        }

        var phase: CouncilPhase
        var consensusText: String
        var models: [ModelState]
        var totalCost: Double
        var elapsedSeconds: Int
    }

    struct ModelState: Codable, Hashable {
        let id: String
        let name: String
        let colorHex: String
        let confidence: Double // 0.0–1.0
        let status: String // "thinking", "done", "dissenting"
        let latencyMs: Int
    }

    var query: String
    var requestedModels: [String]
}

// ───────────────────────────────────────────────────────────────────────────
// Widget View
// ───────────────────────────────────────────────────────────────────────────
struct MEOKCLAWCouncilWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: MEOKCLAWCouncilWidgetAttributes.self) { context in
            // Lock Screen / Notification Center view
            LockScreenView(context: context)
        } dynamicIsland: { context in
            // Dynamic Island expanded view
            DynamicIslandExpandedView(context: context)
        }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Lock Screen View
// ───────────────────────────────────────────────────────────────────────────
struct LockScreenView: View {
    let context: ActivityViewContext<MEOKCLAWCouncilWidgetAttributes>

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                PhaseIcon(phase: context.state.phase)
                Text(context.attributes.query)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                CostBadge(cost: context.state.totalCost)
            }

            if !context.state.models.isEmpty {
                ModelOrbRow(models: context.state.models)
            }

            if context.state.phase == .consensusReached || context.state.phase == .completed {
                Text(context.state.consensusText)
                    .font(.caption)
                    .lineLimit(2)
                    .foregroundStyle(.secondary)
            }

            HStack {
                Label("\(context.state.elapsedSeconds)s", systemImage: "clock")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Spacer()
                if context.state.phase == .blocked {
                    Label("Guardrails", systemImage: "shield.fill")
                        .font(.caption2)
                        .foregroundStyle(.red)
                }
            }
        }
        .padding(.horizontal)
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Dynamic Island Expanded View
// ───────────────────────────────────────────────────────────────────────────
struct DynamicIslandExpandedView: DynamicIsland {
    var context: ActivityViewContext<MEOKCLAWCouncilWidgetAttributes>

    func expanded(leading: DynamicIslandExpandedContent<some View>,
                  trailing: DynamicIslandExpandedContent<some View>,
                  bottom: DynamicIslandExpandedContent<some View>) -> some DynamicIslandExpandedContent {
        DynamicIslandExpandedContent {
            VStack(spacing: 12) {
                HStack {
                    PhaseIcon(phase: context.state.phase)
                        .font(.title2)
                    VStack(alignment: .leading) {
                        Text("MEOKCLAW Council")
                            .font(.headline)
                        Text(context.attributes.query)
                            .font(.caption)
                            .lineLimit(1)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    CostBadge(cost: context.state.totalCost)
                }
                .padding(.horizontal)

                if !context.state.models.isEmpty {
                    ModelOrbRow(models: context.state.models)
                        .padding(.horizontal)
                }

                if context.state.phase == .consensusReached {
                    ConsensusBanner(text: context.state.consensusText)
                        .padding(.horizontal)
                } else if context.state.phase == .disagreement {
                    DisagreementBanner(models: context.state.models)
                        .padding(.horizontal)
                }

                HStack {
                    Label("\(context.state.elapsedSeconds)s elapsed", systemImage: "clock")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(context.state.models.filter { $0.status == "done" }.count)/\(context.state.models.count) models")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.horizontal)
            }
            .padding(.vertical, 8)
        }
    }

    func compactLeading() -> some View {
        PhaseIcon(phase: context.state.phase)
            .font(.title3)
    }

    func compactTrailing() -> some View {
        CostBadge(cost: context.state.totalCost)
    }

    func minimal() -> some View {
        PhaseIcon(phase: context.state.phase)
            .font(.title3)
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Subviews
// ───────────────────────────────────────────────────────────────────────────
struct PhaseIcon: View {
    let phase: MEOKCLAWCouncilWidgetAttributes.ContentState.CouncilPhase

    var body: some View {
        switch phase {
        case .pending:
            Image(systemName: "ellipsis.circle.fill")
                .foregroundStyle(.gray)
        case .deliberating:
            Image(systemName: "circle.dotted.circle")
                .foregroundStyle(.blue)
                .symbolEffect(.pulse)
        case .consensusReached:
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .disagreement:
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
        case .blocked:
            Image(systemName: "shield.fill")
                .foregroundStyle(.red)
        case .completed:
            Image(systemName: "checkmark.seal.fill")
                .foregroundStyle(.green)
        }
    }
}

struct CostBadge: View {
    let cost: Double

    var body: some View {
        Text("$\(String(format: "%.4f", cost))")
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(Color.green.opacity(0.15))
            .foregroundStyle(.green)
            .clipShape(Capsule())
    }
}

struct ModelOrbRow: View {
    let models: [MEOKCLAWCouncilWidgetAttributes.ModelState]

    var body: some View {
        HStack(spacing: 12) {
            ForEach(models, id: \.id) { model in
                ModelOrb(model: model)
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
    }
}

struct ModelOrb: View {
    let model: MEOKCLAWCouncilWidgetAttributes.ModelState

    var body: some View {
        VStack(spacing: 4) {
            ZStack {
                Circle()
                    .fill(Color(hex: model.colorHex).opacity(0.2))
                    .frame(width: 36, height: 36)
                Circle()
                    .fill(Color(hex: model.colorHex))
                    .frame(width: model.status == "thinking" ? 28 : 24,
                           height: model.status == "thinking" ? 28 : 24)
                    .overlay(
                        Group {
                            if model.status == "thinking" {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                    .scaleEffect(0.6)
                            } else if model.status == "dissenting" {
                                Image(systemName: "xmark")
                                    .font(.caption2)
                                    .foregroundStyle(.white)
                            } else {
                                Image(systemName: "checkmark")
                                    .font(.caption2)
                                    .foregroundStyle(.white)
                            }
                        }
                    )
                    .animation(.spring(duration: 0.3), value: model.status)
            }
            Text(model.name)
                .font(.caption2)
                .lineLimit(1)
                .foregroundStyle(.secondary)
        }
    }
}

struct ConsensusBanner: View {
    let text: String

    var body: some View {
        HStack {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
            Text(text)
                .font(.caption)
                .lineLimit(3)
            Spacer()
        }
        .padding(10)
        .background(Color.green.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct DisagreementBanner: View {
    let models: [MEOKCLAWCouncilWidgetAttributes.ModelState]

    var body: some View {
        let dissenters = models.filter { $0.status == "dissenting" }
        HStack {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text("\(dissenters.count) model\(dissenters.count == 1 ? "" : "s") dissenting. Long-press to review.")
                .font(.caption)
            Spacer()
        }
        .padding(10)
        .background(Color.orange.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Helper: Color from hex
// ───────────────────────────────────────────────────────────────────────────
extension Color {
    init(hex: String) {
        let scanner = Scanner(string: hex)
        _ = scanner.scanString("#")
        var rgb: UInt64 = 0
        scanner.scanHexInt64(&rgb)
        let r = Double((rgb >> 16) & 0xFF) / 255.0
        let g = Double((rgb >> 8) & 0xFF) / 255.0
        let b = Double(rgb & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Live Activity Management Helpers
// ───────────────────────────────────────────────────────────────────────────
func startCouncilLiveActivity(query: String, models: [String]) async throws -> Activity<MEOKCLAWCouncilWidgetAttributes> {
    let attributes = MEOKCLAWCouncilWidgetAttributes(
        query: query,
        requestedModels: models
    )
    let initialState = MEOKCLAWCouncilWidgetAttributes.ContentState(
        phase: .pending,
        consensusText: "",
        models: models.map { id in
            let config = MEOKCLAWConfig.availableModels.first { $0.id == id }
            return MEOKCLAWCouncilWidgetAttributes.ModelState(
                id: id,
                name: config?.name ?? id,
                colorHex: config?.color ?? "#888888",
                confidence: 0.0,
                status: "thinking",
                latencyMs: 0
            )
        },
        totalCost: 0.0,
        elapsedSeconds: 0
    )

    let activity = try Activity.request(
        attributes: attributes,
        contentState: initialState,
        pushType: nil
    )
    return activity
}

func updateCouncilLiveActivity(
    activity: Activity<MEOKCLAWCouncilWidgetAttributes>,
    result: CouncilResult
) async {
    let finalState = MEOKCLAWCouncilWidgetAttributes.ContentState(
        phase: result.disagreeingModels.isEmpty ? .consensusReached : .disagreement,
        consensusText: result.consensusText,
        models: result.models.map { m in
            MEOKCLAWCouncilWidgetAttributes.ModelState(
                id: m.model,
                name: m.model,
                colorHex: MEOKCLAWConfig.availableModels.first { $0.id == m.model }?.color ?? "#888888",
                confidence: result.consensusScore,
                status: result.disagreeingModels.contains(m.model) ? "dissenting" : "done",
                latencyMs: m.latency_ms
            )
        },
        totalCost: result.totalCostUSD,
        elapsedSeconds: result.totalLatencyMs / 1000
    )
    await activity.update(using: finalState)
}

func startAuditLiveActivity(agentType: String) async throws -> Activity<MEOKCLAWCouncilWidgetAttributes> {
    let attributes = MEOKCLAWCouncilWidgetAttributes(
        query: "Auditing screen for \(agentType)...",
        requestedModels: [agentType]
    )
    let initialState = MEOKCLAWCouncilWidgetAttributes.ContentState(
        phase: .deliberating,
        consensusText: "",
        models: [],
        totalCost: 0.0,
        elapsedSeconds: 0
    )
    return try Activity.request(attributes: attributes, contentState: initialState, pushType: nil)
}

// ───────────────────────────────────────────────────────────────────────────
// Stub: CouncilResult (mirrors backend response)
// ───────────────────────────────────────────────────────────────────────────
struct CouncilResult {
    let consensusText: String
    let consensusScore: Double
    let models: [ModelResult]
    let totalCostUSD: Double
    let totalLatencyMs: Int
    let disagreeingModels: [String]
}

struct ModelResult {
    let model: String
    let text: String
    let tokens_in: Int
    let tokens_out: Int
    let cost_usd: Double
    let latency_ms: Int
    let confidence: Double?
}
