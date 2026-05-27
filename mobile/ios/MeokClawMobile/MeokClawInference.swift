import Foundation
import MLX
import MLXLLM
import MLXRandom

/// MEOKCLAW On-Device Inference for iOS/macOS
/// Uses Apple MLX for native Apple Silicon performance.
/// Supports Gemma, Qwen, and other MLX-compatible models.
@MainActor
class MeokClawInference: ObservableObject {
    static let shared = MeokClawInference()

    @Published var isLoading = false
    @Published var isGenerating = false
    @Published var statusMessage = "Ready"

    private var modelContainer: ModelContainer?
    private let modelRegistry: [String: String] = [
        "gemma-4b": "mlx-community/gemma-3-4b-it-4bit",
        "qwen-7b": "mlx-community/Qwen2.5-7B-Instruct-4bit",
        "phi-3": "mlx-community/Phi-3-mini-4k-instruct-4bit",
    ]

    /// Load a model by ID
    func loadModel(modelId: String = "gemma-4b") async throws {
        guard let repoId = modelRegistry[modelId] else {
            throw InferenceError.unknownModel(modelId)
        }

        isLoading = true
        statusMessage = "Downloading \(modelId)..."
        defer { isLoading = false }

        // MLXLLM handles download, quantization, and caching
        modelContainer = try await LLMModelFactory.shared.loadContainer(
            configuration: ModelConfiguration(id: repoId)
        ) { progress in
            self.statusMessage = String(format: "Downloading: %.1f%%", progress.fractionCompleted * 100)
        }

        statusMessage = "\(modelId) ready"
    }

    /// Generate text from prompt
    func generate(
        prompt: String,
        temperature: Float = 0.7,
        maxTokens: Int = 1024
    ) async throws -> String {
        guard let container = modelContainer else {
            throw InferenceError.modelNotLoaded
        }

        isGenerating = true
        defer { isGenerating = false }

        let messages = [
            ["role": "user", "content": prompt]
        ]

        let input = try await container.processor.prepare(input: messages)

        return try await container.generate(
            input: input,
            parameters: GenerateParameters(temperature: temperature),
            maxTokens: maxTokens
        ) { tokens in
            // Streaming callback — could update UI here
            return .more
        }
    }

    /// Stream tokens for real-time UI updates
    func generateStream(
        prompt: String,
        temperature: Float = 0.7,
        maxTokens: Int = 1024
    ) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    guard let container = self.modelContainer else {
                        throw InferenceError.modelNotLoaded
                    }

                    let messages = [["role": "user", "content": prompt]]
                    let input = try await container.processor.prepare(input: messages)

                    var accumulated = ""
                    _ = try await container.generate(
                        input: input,
                        parameters: GenerateParameters(temperature: temperature),
                        maxTokens: maxTokens
                    ) { tokens in
                        let text = container.tokenizer.decode(tokens: tokens)
                        accumulated = text
                        continuation.yield(text)
                        return .more
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    /// Check available memory for model loading
    func checkMemory() -> (totalGB: Double, availableGB: Double) {
        let physicalMemory = ProcessInfo.processInfo.physicalMemory
        // Rough estimate: available ≈ 60% of physical on iOS
        let available = Double(physicalMemory) * 0.6 / 1e9
        return (Double(physicalMemory) / 1e9, available)
    }

    /// Unload model to free memory
    func unload() {
        modelContainer = nil
        statusMessage = "Model unloaded"
    }
}

enum InferenceError: Error {
    case unknownModel(String)
    case modelNotLoaded
    case generationFailed(String)
}
