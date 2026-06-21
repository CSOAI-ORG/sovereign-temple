package com.meokclaw

import android.content.Context
import com.google.mediapipe.tasks.genai.llminference.LlmInference
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import java.io.File

/**
 * MEOKCLAW On-Device Inference for Android
 * Uses Google MediaPipe LLM Inference API for production-grade on-device execution.
 * Supports Gemma, Phi, Falcon, StableLM via TensorFlow Lite Flatbuffer.
 */
class MeokClawInference(private val context: Context) {

    private var llmInference: LlmInference? = null
    private val _partialResults = MutableSharedFlow<Pair<String, Boolean>>(extraBufferCapacity = 64)
    val partialResults: Flow<Pair<String, Boolean>> = _partialResults.asSharedFlow()

    private val modelRegistry = mapOf(
        "gemma-2b" to "gemma-2b-it-gpu-int4.bin",
        "gemma-4b" to "gemma-4b-it-gpu-int4.bin",
        "phi-2" to "phi-2-gpu-int4.bin",
    )

    /**
     * Load a model from assets or local storage.
     * @param modelId Key from modelRegistry
     * @param maxTokens Max generation length
     */
    fun loadModel(modelId: String = "gemma-4b", maxTokens: Int = 1024): Result<Unit> {
        return try {
            val modelFileName = modelRegistry[modelId]
                ?: return Result.failure(IllegalArgumentException("Unknown model: $modelId"))

            // Copy from assets to cache if not exists
            val modelPath = copyModelFromAssets(modelFileName)

            val options = LlmInference.LlmInferenceOptions.builder()
                .setModelPath(modelPath)
                .setMaxTokens(maxTokens)
                .setResultListener { partialResult, done ->
                    _partialResults.tryEmit(partialResult to done)
                }
                .build()

            llmInference = LlmInference.createFromOptions(context, options)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Synchronous generation (blocking — use with coroutines).
     */
    fun generate(prompt: String): String {
        val inference = llmInference ?: throw IllegalStateException("Model not loaded")
        return inference.generateResponse(prompt)
    }

    /**
     * Asynchronous generation with Flow streaming.
     */
    fun generateAsync(prompt: String) {
        val inference = llmInference ?: throw IllegalStateException("Model not loaded")
        inference.generateResponseAsync(prompt)
    }

    /**
     * Get token count for a string.
     */
    fun sizeInTokens(text: String): Int {
        return llmInference?.sizeInTokens(text) ?: 0
    }

    /**
     * Unload model to free memory.
     */
    fun unload() {
        llmInference?.close()
        llmInference = null
    }

    private fun copyModelFromAssets(fileName: String): String {
        val cacheFile = File(context.cacheDir, fileName)
        if (cacheFile.exists()) return cacheFile.absolutePath

        context.assets.open(fileName).use { input ->
            cacheFile.outputStream().use { output ->
                input.copyTo(output)
            }
        }
        return cacheFile.absolutePath
    }

    companion object {
        /**
         * Check if device has enough RAM for a model.
         */
        fun checkDeviceCapability(context: Context, modelSizeMB: Int): Boolean {
            val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
            val memoryInfo = android.app.ActivityManager.MemoryInfo()
            activityManager.getMemoryInfo(memoryInfo)
            // Need at least 2x model size in available RAM
            return memoryInfo.availMem > modelSizeMB * 2 * 1024 * 1024
        }
    }
}
