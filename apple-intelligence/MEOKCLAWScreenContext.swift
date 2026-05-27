import Foundation
import Vision
#if canImport(ScreenCaptureKit)
import ScreenCaptureKit
#endif
#if canImport(UIKit)
import UIKit
#endif

// MARK: — MEOKCLAW Screen Context Capture
// Uses iOS 18 Siri On-Screen Awareness + ScreenCaptureKit to extract text
// from the visible screen, then delegates analysis to SOV3 agents.

@available(iOS 18.0, macOS 15.0, *)
final class MEOKCLAWScreenCapture: @unchecked Sendable {
    static let shared = MEOKCLAWScreenCapture()

    private init() {}

    /// Captures visible text from the current screen using OCR.
    /// Requires `com.apple.developer.screen-capture` entitlement.
    func captureVisibleText() async throws -> String {
        #if os(iOS)
        // On iOS, we use the screenshot + Vision OCR pipeline
        guard let screenshot = await captureScreenshot() else {
            throw ScreenCaptureError.noScreenshot
        }
        return try await performOCR(on: screenshot)
        #elseif os(macOS)
        // On macOS, use ScreenCaptureKit to get the active window's text
        let content = try await captureActiveWindowContent()
        return content
        #else
        throw ScreenCaptureError.unsupportedPlatform
        #endif
    }

    /// Captures structured content (text + images + layout) for rich delegation.
    func captureStructuredContent() async throws -> ScreenContent {
        let text = try await captureVisibleText()
        let url = try await extractVisibleURL()
        return ScreenContent(
            plainText: text,
            sourceURL: url,
            timestamp: Date(),
            appBundleId: await frontmostAppBundleId()
        )
    }

    // ───────────────────────────────────────────────────────────────────────
    // iOS: Screenshot + Vision OCR
    // ───────────────────────────────────────────────────────────────────────
    #if os(iOS)
    private func captureScreenshot() async -> UIImage? {
        // In a real app, this uses UIApplication's key window snapshot.
        // For App Intents context, Siri may provide the screen content directly.
        // This is a stub that would integrate with Siri's on-screen awareness API.
        return nil
    }
    #endif

    #if canImport(UIKit)
    private func performOCR(on image: UIImage) async throws -> String {
        guard let cgImage = image.cgImage else {
            throw ScreenCaptureError.imageConversionFailed
        }

        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try handler.perform([request])

        let observations = request.results ?? []
        let text = observations
            .compactMap { $0.topCandidates(1).first?.string }
            .joined(separator: "\n")

        return text
    }
    #endif

    // ───────────────────────────────────────────────────────────────────────
    // macOS: ScreenCaptureKit
    // ───────────────────────────────────────────────────────────────────────
    #if os(macOS)
    private func captureActiveWindowContent() async throws -> String {
        // ScreenCaptureKit allows capturing specific windows without full screen recording
        let config = SCStreamConfiguration()
        // Filter to active application window
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        let filter = SCContentFilter(display: content.displays.first!,
                                      excludingApplications: [],
                                      exceptingWindows: [])

        let stream = SCStream(filter: filter, configuration: config, delegate: nil)
        // Capture single frame and OCR
        // This is simplified; production code uses SCStreamOutput
        return ""
    }
    #endif

    // ───────────────────────────────────────────────────────────────────────
    // URL Extraction (from Safari / active browser)
    // ───────────────────────────────────────────────────────────────────────
    private func extractVisibleURL() async -> String? {
        // Try to get URL from Safari's shared WKWebView state
        // Or use NSWorkspace on macOS to get frontmost browser URL
        #if os(macOS)
        let frontApp = NSWorkspace.shared.frontmostApplication
        if frontApp?.bundleIdentifier == "com.apple.Safari" {
            // AppleScript or accessibility API to get URL
        }
        #endif
        return nil
    }

    // ───────────────────────────────────────────────────────────────────────
    // Frontmost App Detection
    // ───────────────────────────────────────────────────────────────────────
    private func frontmostAppBundleId() async -> String? {
        #if os(iOS)
        return Bundle.main.bundleIdentifier
        #elseif os(macOS)
        return NSWorkspace.shared.frontmostApplication?.bundleIdentifier
        #else
        return nil
        #endif
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Screen Content Model
// ───────────────────────────────────────────────────────────────────────────
struct ScreenContent {
    let plainText: String
    let sourceURL: String?
    let timestamp: Date
    let appBundleId: String?

    /// Converts to JSON payload for MEOKCLAW backend
    func toPayload() -> [String: Any] {
        var payload: [String: Any] = [
            "screen_text": plainText,
            "captured_at": ISO8601DateFormatter().string(from: timestamp)
        ]
        if let url = sourceURL {
            payload["source_url"] = url
        }
        if let bundleId = appBundleId {
            payload["app_bundle_id"] = bundleId
        }
        return payload
    }
}

enum ScreenCaptureError: Error {
    case noScreenshot
    case imageConversionFailed
    case unsupportedPlatform
    case noPermission
}
