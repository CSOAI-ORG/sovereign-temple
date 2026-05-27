# Mobile E2E Integration Guide

> **Version:** 1.0.0 | **Platforms:** iOS 18+, Android 14+ | **Status:** Scaffold → Production

---

## Overview

This guide connects the existing mobile inference scaffolds to the **Mac Mesh Orchestrator**, creating a true end-to-end experience:

```
[iOS/Android App] ──► [Mac Mesh Orchestrator :3202] ──► [M2/M4/Vast inference]
        │                       │
        │                       ▼
        │              [Guardrails + Cache + Audit]
        │                       │
        ▼                       ▼
[On-device fallback]    [SOV3 coordination]
(MLX / MediaPipe)       (Agent swarm)
```

---

## iOS — MLX Path

### Current State
- `mobile/ios/MeokClawMobile/MeokClawInference.swift` uses Apple MLX for on-device inference
- Supports Gemma-3-4B, Qwen2.5-7B, Phi-3-mini
- Runs entirely on-device (no network needed for L1 tasks)

### E2E Integration Steps

**1. Add Mesh API Client to Swift**

Create `MeokClawMeshClient.swift`:

```swift
import Foundation

class MeokClawMeshClient {
    private let orchestratorURL = "http://m4-macbook.local:3202"
    
    func chat(message: String, useLocal: Bool = true) async throws -> MeshResponse {
        // 1. Try on-device first if useLocal and model loaded
        if useLocal, MeokClawInference.shared.modelContainer != nil {
            let localText = try await MeokClawInference.shared.generate(prompt: message)
            return MeshResponse(text: localText, node: "ios-mlx", latencyMs: 0)
        }
        
        // 2. Fallback to mesh orchestrator
        let url = URL(string: "\(orchestratorURL)/v1/chat")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = [
            "message": message,
            "use_speculative": true,
            "require_private": false,
            "stream": false
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(MeshResponse.self, from: data)
    }
}

struct MeshResponse: Codable {
    let text: String
    let node: String
    let model: String?
    let latencyMs: Double
    let speculativeUsed: Bool?
}
```

**2. Siri Integration**

Add to `Info.plist`:
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>MEOKCLAW needs local network access to communicate with your Mac mesh.</string>
<key>NSBonjourServices</key>
<array>
    <string>_http._tcp</string>
</array>
```

**3. App Intents (iOS 18)**

```swift
import AppIntents

struct AskMeokclawIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask MEOKCLAW"
    static var description = IntentDescription("Ask a question to your sovereign AI mesh")
    
    @Parameter(title: "Question")
    var question: String
    
    func perform() async throws -> some IntentResult {
        let client = MeokClawMeshClient()
        let response = try await client.chat(message: question)
        return .result(dialog: "\(response.text)")
    }
}
```

---

## Android — MediaPipe + Mesh Bridge

### Current State
- `mobile/android/app/src/main/java/com/meokclaw/MeokClawInference.kt` uses Google MediaPipe
- Supports Gemma-2B, Gemma-4B, Phi-2 via TensorFlow Lite
- Needs mesh bridge integration

### E2E Integration Steps

**1. Add Mesh API Client to Kotlin**

Create `MeokClawMeshClient.kt`:

```kotlin
package com.meokclaw

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class MeokClawMeshClient(private val orchestratorUrl: String = "http://m4-macbook.local:3202") {
    private val client = OkHttpClient()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    suspend fun chat(message: String, useLocal: Boolean = true): MeshResponse = withContext(Dispatchers.IO) {
        // 1. Try on-device first
        if (useLocal && MeokClawInference.getInstance().isModelLoaded()) {
            val localText = MeokClawInference.getInstance().generate(message)
            return@withContext MeshResponse(text = localText, node = "android-mediapipe", latencyMs = 0)
        }

        // 2. Fallback to mesh
        val body = JSONObject().apply {
            put("message", message)
            put("use_speculative", true)
            put("require_private", false)
            put("stream", false)
        }

        val request = Request.Builder()
            .url("$orchestratorUrl/v1/chat")
            .post(body.toString().toRequestBody(jsonMediaType))
            .build()

        client.newCall(request).execute().use { response ->
            val json = JSONObject(response.body?.string() ?: "{}")
            MeshResponse(
                text = json.optString("text", ""),
                node = json.optString("node", "unknown"),
                model = json.optString("model", null),
                latencyMs = json.optDouble("latency_ms", 0.0),
                speculativeUsed = json.optBoolean("speculative_used", false)
            )
        }
    }
}

data class MeshResponse(
    val text: String,
    val node: String,
    val model: String?,
    val latencyMs: Double,
    val speculativeUsed: Boolean?
)
```

**2. Android Permissions**

Add to `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="android.permission.BATTERY_STATS" />
```

**3. Battery-Aware Routing**

```kotlin
// In your Activity/ViewModel
val batteryManager = getSystemService(Context.BATTERY_SERVICE) as BatteryManager
val batteryPct = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)

// If battery < 20%, force mesh offload (don't run on-device)
val useLocal = batteryPct > 20
val response = meshClient.chat(message, useLocal = useLocal)
```

---

## Cross-Platform API Contract

### Mesh Orchestrator Endpoints (Mobile-Optimized)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat` | POST | Main chat — auto-routes to best node |
| `/v1/chat/direct` | POST | Force specific node (m2/m4/vast) |
| `/v1/route` | GET | Show routing decision without executing |
| `/health` | GET | Mesh status — use for connection check |
| `/siri/chat` | GET | Siri-optimized — returns plain text |

### Request Format (Universal)

```json
{
  "message": "Explain quantum computing",
  "use_speculative": true,
  "require_private": false,
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 2048
}
```

### Response Format (Universal)

```json
{
  "text": "Quantum computing uses quantum bits...",
  "node": "m4+m2",
  "model": "qwen3:8b",
  "latency_ms": 245.0,
  "tokens_in": 12,
  "tokens_out": 156,
  "speculative_used": true,
  "draft_accepted_ratio": 0.72,
  "cost_usd": 0.0
}
```

---

## Testing Checklist

### iOS
- [ ] App builds on Xcode 16+
- [ ] MLX model loads (Gemma-3-4B) on iPhone 15 Pro
- [ ] Local inference works in Airplane Mode
- [ ] Mesh fallback triggers when model not loaded
- [ ] Siri Intent responds correctly
- [ ] Latency < 500ms for local, < 3000ms for mesh

### Android
- [ ] App builds on Android Studio Ladybug
- [ ] MediaPipe model loads (Gemma-4B) on Pixel 9
- [ ] Local inference works offline
- [ ] Mesh fallback triggers correctly
- [ ] Battery-aware routing works (< 20% forces mesh)
- [ ] WebSocket reconnects after network loss

### Cross-Platform
- [ ] Same query returns consistent results on iOS and Android
- [ ] Mesh orchestrator logs show both device types
- [ ] Guardrails block identical harmful queries on both platforms
- [ ] i18n responses match locale settings

---

## Deployment

### iOS TestFlight
```bash
cd mobile/ios/MeokClawMobile
xcodebuild -scheme MeokClawMobile -destination 'generic/platform=iOS' archive
xcrun altool --upload-app --type ios --file MeokClawMobile.xcarchive
```

### Android Google Play (Internal Testing)
```bash
cd mobile/android
./gradlew assembleRelease
# Upload app/build/outputs/apk/release/app-release.apk to Play Console
```

---

*This guide transforms the mobile scaffolds into production-ready E2E integrations. Both platforms respect the "local first, cloud when needed" sovereign principle while delivering seamless user experience.*
