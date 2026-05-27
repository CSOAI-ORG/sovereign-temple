import SwiftUI
import AppIntents
import ActivityKit
import WidgetKit

// MARK: — MEOKCLAW SwiftUI App Scaffold
// Entry point for the iOS / macOS / visionOS app that hosts App Intents,
// Live Activities, and mesh node configuration.

@main
struct MEOKCLAWApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self)
    var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onAppear {
                    // Warm up semantic cache with on-device embeddings
                    MEOKCLAWEmbeddingBridge.shared.warmCache()
                }
        }

        // Register Live Activity widgets
        #if os(iOS)
        .backgroundTask(.appRefresh("meokclaw.mesh.sync")) {
            await MeshNodeSyncTask.run()
        }
        #endif
    }
}

// ───────────────────────────────────────────────────────────────────────────
// App Delegate — Push token registration for Live Activities
// ───────────────────────────────────────────────────────────────────────────
class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Request push notification permissions for Live Activity updates
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { _, _ in }
        application.registerForRemoteNotifications()
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        UserDefaults.standard.set(token, forKey: "meokclaw_push_token")
        // Register with backend
        Task {
            try? await MEOKCLAWAPI.shared.registerLiveActivity(token: token, activityId: "global")
        }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Content View — Main UI
// ───────────────────────────────────────────────────────────────────────────
struct ContentView: View {
    @StateObject private var store = MEOKCLAWStore()

    var body: some View {
        NavigationStack {
            List {
                // Quick Actions
                Section("Ask") {
                    NavigationLink("Council Mode") {
                        CouncilModeView()
                    }
                    NavigationLink("Single Model") {
                        SingleModelView()
                    }
                    NavigationLink("SOV3 Agent Swarm") {
                        SOV3View()
                    }
                }

                // Configuration
                Section("Sovereign Node") {
                    NodeConfigView()
                }

                // Analytics
                Section("Transparency") {
                    CostTransparencyView()
                    GuardrailsLogView()
                }

                // Family Rules
                Section("Household Constitution") {
                    FamilyRulesView()
                }
            }
            .navigationTitle("MEOKCLAW")
        }
        .environmentObject(store)
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Council Mode View
// ───────────────────────────────────────────────────────────────────────────
struct CouncilModeView: View {
    @State private var query = ""
    @State private var selectedModels = Set<String>(["deepseek-v4-flash", "deepseek-v4-pro", "kimi-k2.6"])
    @State private var result: CouncilResult?
    @State private var isLoading = false
    @State private var activity: Activity<MEOKCLAWCouncilWidgetAttributes>?

    var body: some View {
        Form {
            Section("Question") {
                TextField("What should the council deliberate on?", text: $query, axis: .vertical)
                    .lineLimit(3...6)
            }

            Section("Models") {
                ForEach(MEOKCLAWConfig.availableModels, id: \.id) { model in
                    ModelToggleRow(model: model, isOn: Binding(
                        get: { selectedModels.contains(model.id) },
                        set: { isOn in
                            if isOn { selectedModels.insert(model.id) }
                            else { selectedModels.remove(model.id) }
                        }
                    ))
                }
            }

            Section {
                Button(action: runCouncil) {
                    if isLoading {
                        Label("Deliberating...", systemImage: "circle.dotted")
                            .symbolEffect(.pulse)
                    } else {
                        Label("Run Council", systemImage: "person.3.fill")
                    }
                }
                .disabled(query.isEmpty || selectedModels.isEmpty || isLoading)
            }

            if let result = result {
                CouncilResultSection(result: result)
            }
        }
        .navigationTitle("Council Mode")
    }

    private func runCouncil() {
        isLoading = true
        result = nil

        Task {
            do {
                // Start Live Activity
                activity = try? await startCouncilLiveActivity(
                    query: query,
                    models: Array(selectedModels)
                )

                let apiResult = try await MEOKCLAWAPI.shared.council(
                    query: query,
                    models: Array(selectedModels)
                )

                await MainActor.run {
                    self.result = apiResult
                    self.isLoading = false
                }

                // Update Live Activity
                if let activity = activity {
                    await updateCouncilLiveActivity(activity: activity, result: apiResult)
                }
            } catch {
                await MainActor.run {
                    self.isLoading = false
                }
            }
        }
    }
}

struct ModelToggleRow: View {
    let model: CouncilModel
    @Binding var isOn: Bool

    var body: some View {
        Toggle(isOn: $isOn) {
            HStack {
                Circle()
                    .fill(Color(hex: model.color))
                    .frame(width: 12, height: 12)
                Text(model.name)
            }
        }
    }
}

struct CouncilResultSection: View {
    let result: CouncilResult

    var body: some View {
        Section("Consensus") {
            Text(result.consensus_text)
                .font(.body)

            HStack {
                Label("Score: \(Int(result.consensus_score * 100))%", systemImage: "chart.bar.fill")
                Spacer()
                Label("$\(String(format: "%.4f", result.total_cost_usd))", systemImage: "dollarsign.circle.fill")
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if !result.disagreeing_models.isEmpty {
                Label("Dissent: \(result.disagreeing_models.joined(separator: ", "))", systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }

        Section("Individual Responses") {
            ForEach(result.models, id: \.model) { m in
                VStack(alignment: .leading, spacing: 4) {
                    Text(m.model)
                        .font(.caption)
                        .fontWeight(.semibold)
                    Text(m.text)
                        .font(.caption)
                        .lineLimit(3)
                        .foregroundStyle(.secondary)
                    Text("$\(String(format: "%.4f", m.cost_usd)) · \(m.latency_ms)ms")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 2)
            }
        }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Single Model View
// ───────────────────────────────────────────────────────────────────────────
struct SingleModelView: View {
    @State private var message = ""
    @State private var response: String?
    @State private var isLoading = false

    var body: some View {
        Form {
            Section("Message") {
                TextField("Ask anything...", text: $message, axis: .vertical)
                    .lineLimit(3...6)
            }
            Section {
                Button("Send") {
                    Task {
                        isLoading = true
                        defer { isLoading = false }
                        // Uses the /api/dual-brain endpoint
                        let payload: [String: Any] = ["message": message, "mode": "auto"]
                        let data = try? await MEOKCLAWAPI.shared.post(path: "/api/dual-brain", body: payload)
                        if let data = data,
                           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                            response = json["text"] as? String
                        }
                    }
                }
                .disabled(message.isEmpty || isLoading)
            }
            if let response = response {
                Section("Response") {
                    Text(response)
                }
            }
        }
        .navigationTitle("Chat")
    }
}

// ───────────────────────────────────────────────────────────────────────────
// SOV3 Agent Swarm View
// ───────────────────────────────────────────────────────────────────────────
struct SOV3View: View {
    @State private var task = ""
    @State private var agentType = "legal"
    @State private var result = ""
    @State private var isLoading = false

    let agentTypes = ["legal", "security", "finance", "research", "creative"]

    var body: some View {
        Form {
            Section("Task") {
                TextField("What should the agents do?", text: $task, axis: .vertical)
                    .lineLimit(3...6)
            }
            Section("Agent") {
                Picker("Type", selection: $agentType) {
                    ForEach(agentTypes, id: \.self) { type in
                        Text(type.capitalized).tag(type)
                    }
                }
            }
            Section {
                Button("Delegate") {
                    Task {
                        isLoading = true
                        defer { isLoading = false }
                        let res = try? await MEOKCLAWAPI.shared.sov3Delegate(task: task, agentFilter: agentType)
                        result = res?.summary ?? "No response"
                    }
                }
                .disabled(task.isEmpty || isLoading)
            }
            if !result.isEmpty {
                Section("Result") {
                    Text(result)
                }
            }
        }
        .navigationTitle("SOV3 Delegation")
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Node Config View
// ───────────────────────────────────────────────────────────────────────────
struct NodeConfigView: View {
    @AppStorage("meokclaw_local_node") private var localNode = "http://192.168.1.100:3201"
    @AppStorage("meokclaw_mesh_endpoint") private var meshEndpoint = ""
    @AppStorage("meokclaw_api_key") private var apiKey = ""

    var body: some View {
        Form {
            Section("Local Node") {
                TextField("IP:Port", text: $localNode)
                    .keyboardType(.URL)
                    .autocapitalization(.none)
                Text("Apple TV or Mac Mini on your network")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Section("Mesh Endpoint (Optional)") {
                TextField("Tailscale/Headscale URL", text: $meshEndpoint)
                    .keyboardType(.URL)
                    .autocapitalization(.none)
            }
            Section("API Key") {
                SecureField("Key", text: $apiKey)
            }
            Section {
                Button("Test Connection") {
                    Task {
                        _ = try? await MEOKCLAWAPI.shared.get(path: "/health")
                    }
                }
            }
        }
        .navigationTitle("Node Config")
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Cost Transparency View
// ───────────────────────────────────────────────────────────────────────────
struct CostTransparencyView: View {
    @State private var report: CostReport?

    var body: some View {
        Form {
            if let report = report {
                Section("Today") {
                    LabeledContent("Queries", value: "\(report.queryCount)")
                    LabeledContent("Total Cost", value: "$\(String(format: "%.4f", report.totalCost))")
                    LabeledContent("Cache Savings", value: "$\(String(format: "%.4f", report.cacheSavings))")
                    LabeledContent("Top Model", value: report.topModel)
                }
            }
            Section {
                Button("Refresh") {
                    Task {
                        report = try? await MEOKCLAWAPI.shared.costReport(period: "today")
                    }
                }
            }
        }
        .navigationTitle("Cost Report")
        .onAppear {
            Task {
                report = try? await MEOKCLAWAPI.shared.costReport(period: "today")
            }
        }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Guardrails Log View
// ───────────────────────────────────────────────────────────────────────────
struct GuardrailsLogView: View {
    var body: some View {
        List {
            Text("Recent guardrails events synced from node")
                .foregroundStyle(.secondary)
        }
        .navigationTitle("Guardrails Log")
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Family Rules View
// ───────────────────────────────────────────────────────────────────────────
struct FamilyRulesView: View {
    @AppStorage("meokclaw_family_rules") private var rulesJSON = "{}"

    var body: some View {
        Form {
            Section("Constitutional Rules") {
                TextEditor(text: $rulesJSON)
                    .font(.system(.body, design: .monospaced))
                    .frame(minHeight: 200)
            }
            Section {
                Button("Save & Sync to Node") {
                    // POST to /api/auth/rules or similar
                }
            }
        }
        .navigationTitle("Household Constitution")
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Store
// ───────────────────────────────────────────────────────────────────────────
class MEOKCLAWStore: ObservableObject {
    @Published var nodeStatus: String = "unknown"
    @Published var lastSync: Date?
}

// ───────────────────────────────────────────────────────────────────────────
// Background Task
// ───────────────────────────────────────────────────────────────────────────
struct MeshNodeSyncTask {
    static func run() async {
        // Periodic sync with mesh node: cache warming, rule updates, health checks
        _ = try? await MEOKCLAWAPI.shared.get(path: "/health")
    }
}
