import Foundation

// MARK: — MEOKCLAW Swift API Client
// Bridges iOS App Intents / Live Activities to the MEOKCLAW backend.
// Supports: council mode, SOV3 delegation, guardrails checks, cost reports.

final class MEOKCLAWAPI {
    static let shared = MEOKCLAWAPI()

    // Configurable endpoint — defaults to local mesh node, falls back to cloud
    var baseURL: URL {
        // Priority 1: Local mesh node (Apple TV / Mac Mini on LAN)
        if let localURL = UserDefaults.standard.string(forKey: "meokclaw_local_node"),
           let url = URL(string: localURL) {
            return url
        }
        // Priority 2: Tailscale / Headscale mesh
        if let meshURL = UserDefaults.standard.string(forKey: "meokclaw_mesh_endpoint"),
           let url = URL(string: meshURL) {
            return url
        }
        // Priority 3: Default localhost (dev)
        return URL(string: "http://localhost:3201")!
    }

    var apiKey: String? {
        // Read from Secure Enclave via Keychain in production
        UserDefaults.standard.string(forKey: "meokclaw_api_key")
    }

    private let session: URLSession

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 60.0
        config.timeoutIntervalForResource = 120.0
        self.session = URLSession(configuration: config)
    }

    // ───────────────────────────────────────────────────────────────────────
    // Council Mode
    // ───────────────────────────────────────────────────────────────────────
    func council(query: String, models: [String]) async throws -> CouncilResult {
        let payload: [String: Any] = [
            "prompt": query,
            "models": models,
            "consensus_threshold": 0.6
        ]
        let data = try await post(path: "/api/council", body: payload)
        return try JSONDecoder().decode(CouncilResult.self, from: data)
    }

    // ───────────────────────────────────────────────────────────────────────
    // SOV3 Agent Delegation
    // ───────────────────────────────────────────────────────────────────────
    func sov3Delegate(task: String, agentFilter: String?) async throws -> SOV3DelegateResult {
        let payload: [String: Any] = [
            "command": "delegate",
            "task_description": task,
            "agent_filter": agentFilter ?? "auto"
        ]
        let data = try await post(path: "/siri/sov3", body: payload)
        // The /siri/sov3 endpoint returns plain text. We wrap it.
        let text = String(data: data, encoding: .utf8) ?? ""
        return SOV3DelegateResult(summary: text, cost: 0.0)
    }

    // ───────────────────────────────────────────────────────────────────────
    // Guardrails Check
    // ───────────────────────────────────────────────────────────────────────
    func guardrailsCheck(text: String) async throws -> GuardrailsCheckResult {
        let payload: [String: Any] = [
            "text": text,
            "enforce_pii": "redact",
            "enforce_injection": "block",
            "enforce_content": "block"
        ]
        let data = try await post(path: "/api/guardrails/check", body: payload)
        return try JSONDecoder().decode(GuardrailsCheckResult.self, from: data)
    }

    // ───────────────────────────────────────────────────────────────────────
    // Cost Report
    // ───────────────────────────────────────────────────────────────────────
    func costReport(period: String) async throws -> CostReport {
        let data = try await get(path: "/api/cost-savings/summary?period=\(period)")
        return try JSONDecoder().decode(CostReport.self, from: data)
    }

    // ───────────────────────────────────────────────────────────────────────
    // Live Activity Push Token Registration
    // ───────────────────────────────────────────────────────────────────────
    func registerLiveActivity(token: String, activityId: String) async throws {
        let payload: [String: Any] = [
            "push_token": token,
            "activity_id": activityId,
            "device_type": "iOS"
        ]
        _ = try await post(path: "/apple-intelligence/live-activity", body: payload)
    }

    // ───────────────────────────────────────────────────────────────────────
    // On-Device Embedding → Cache Lookup
    // ───────────────────────────────────────────────────────────────────────
    func semanticCacheLookup(embedding: [Double]) async throws -> SemanticCacheResult? {
        let payload: [String: Any] = [
            "embedding": embedding,
            "threshold": 0.92
        ]
        let data = try await post(path: "/apple-intelligence/embedding", body: payload)
        let result = try JSONDecoder().decode(SemanticCacheResult.self, from: data)
        return result.hit ? result : nil
    }

    // ───────────────────────────────────────────────────────────────────────
    // Low-level HTTP
    // ───────────────────────────────────────────────────────────────────────
    func post(path: String, body: [String: Any]) async throws -> Data {
        let url = baseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let key = apiKey {
            request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw MEOKCLAWError.invalidResponse
        }
        if httpResponse.statusCode >= 400 {
            let text = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw MEOKCLAWError.httpError(status: httpResponse.statusCode, message: text)
        }
        return data
    }

    func get(path: String) async throws -> Data {
        let url = baseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        if let key = apiKey {
            request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw MEOKCLAWError.invalidResponse
        }
        if httpResponse.statusCode >= 400 {
            let text = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw MEOKCLAWError.httpError(status: httpResponse.statusCode, message: text)
        }
        return data
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Error Types
// ───────────────────────────────────────────────────────────────────────────
enum MEOKCLAWError: Error {
    case invalidResponse
    case httpError(status: Int, message: String)
    case encodingFailed
}

// ───────────────────────────────────────────────────────────────────────────
// Response Models (Codable)
// ───────────────────────────────────────────────────────────────────────────
struct CouncilResult: Codable {
    let response_id: String
    let prompt: String
    let models: [ModelResult]
    let consensus_text: String
    let consensus_score: Double
    let disagreeing_models: [String]
    let total_cost_usd: Double
    let total_latency_ms: Int
}

struct ModelResult: Codable {
    let model: String
    let text: String
    let tokens_in: Int
    let tokens_out: Int
    let cost_usd: Double
    let latency_ms: Int
    let confidence: Double?
}

struct GuardrailsCheckResult: Codable {
    let blocked: Bool
    let cleaned_text: String
    let violations: [GuardrailViolation]
    let enforcement_level: String
}

struct GuardrailViolation: Codable {
    let type: String
    let severity: String
    let description: String
    let rule_id: String?
}

struct CostReport: Codable {
    let totalCost: Double
    let queryCount: Int
    let cacheSavings: Double
    let topModel: String
    let topModelCost: Double
}

struct SOV3DelegateResult: Codable {
    let summary: String
    let cost: Double
}

struct SemanticCacheResult: Codable {
    let hit: Bool
    let text: String
    let cost_saved: Double
    let latency_ms: Int
}
