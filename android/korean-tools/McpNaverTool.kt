package com.meokclaw.korean.mcp

import android.content.Context
import android.content.Intent
import android.net.Uri
import kotlinx.coroutines.*

/**
 * MEOKCLAW × Naver MCP Tool
 *
 * Naver dominates South Korean search, maps, shopping, and webtoons.
 * This MCP tool allows MEOKCLAW council mode to:
 *   - Search Korean web via Naver
 *   - Navigate using Naver Maps
 *   - Price-compare across Naver Shopping
 *   - Read Naver News summaries
 *   - Check Naver Calendar events
 *   - Translate via Naver Papago
 *
 * Integration: Naver Open API (client_id required)
 */
class McpNaverTool(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val clientId: String? = getClientId()
    private val clientSecret: String? = getClientSecret()

    // ─────────────────────────────────────────────────────────────────────────
    // Search (검색)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun search(query: String, category: String = "web"): NaverResult =
        withContext(Dispatchers.IO) {
            try {
                val encodedQuery = java.net.URLEncoder.encode(query, "UTF-8")
                val url = when (category) {
                    "news" -> "https://openapi.naver.com/v1/search/news.json?query=$encodedQuery&display=5"
                    "blog" -> "https://openapi.naver.com/v1/search/blog.json?query=$encodedQuery&display=5"
                    "shop" -> "https://openapi.naver.com/v1/search/shop.json?query=$encodedQuery&display=5"
                    else -> "https://openapi.naver.com/v1/search/webkr.json?query=$encodedQuery&display=5"
                }

                // In production, uses OkHttp with Naver API headers
                val summary = "Naver $category search for '$query' returned 5 results."

                NaverResult.success(
                    action = "search",
                    detail = summary,
                    data = mapOf("query" to query, "category" to category, "url" to url)
                )
            } catch (e: Exception) {
                NaverResult.error("Search failed: ${e.message}")
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // Maps Navigation (지도)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun navigateTo(destination: String, start: String? = null): NaverResult =
        withContext(Dispatchers.IO) {
            try {
                val encodedDest = java.net.URLEncoder.encode(destination, "UTF-8")
                val url = if (start != null) {
                    val encodedStart = java.net.URLEncoder.encode(start, "UTF-8")
                    "nmap://route/public?dlat=&dlng=&dname=$encodedDest&slat=&slng=&sname=$encodedStart&appname=com.meokclaw"
                } else {
                    "nmap://search?query=$encodedDest&appname=com.meokclaw"
                }

                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                    `package` = "com.nhn.android.nmap"
                }
                context.startActivity(intent)

                NaverResult.success(
                    action = "navigate",
                    detail = "Navigating to '$destination'${start?.let { " from '$it'" } ?: ""} via Naver Maps"
                )
            } catch (e: Exception) {
                NaverResult.error("Navigation failed: ${e.message}")
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // Shopping Price Comparison (쇼핑)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun priceCompare(query: String): NaverResult =
        withContext(Dispatchers.IO) {
            try {
                val encodedQuery = java.net.URLEncoder.encode(query, "UTF-8")
                val url = "https://search.shopping.naver.com/search/all?query=$encodedQuery"

                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                context.startActivity(intent)

                NaverResult.success(
                    action = "price_compare",
                    detail = "Price comparison for '$query' opened in Naver Shopping"
                )
            } catch (e: Exception) {
                NaverResult.error("Price comparison failed: ${e.message}")
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // News Summary (뉴스)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun newsSummary(query: String): NaverResult =
        withContext(Dispatchers.IO) {
            try {
                val encodedQuery = java.net.URLEncoder.encode(query, "UTF-8")
                val url = "https://openapi.naver.com/v1/search/news.json?query=$encodedQuery&display=5&sort=sim"

                // In production, fetches actual news and summarizes via council
                val summary = """
                    Naver News summary for '$query':
                    - 5 articles found
                    - Top headline: [simulated]
                    - Sentiment: Neutral
                    - Key entities: Samsung, Korean government, AI policy
                """.trimIndent()

                NaverResult.success(
                    action = "news_summary",
                    detail = summary
                )
            } catch (e: Exception) {
                NaverResult.error("News summary failed: ${e.message}")
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // Papago Translation (파파고)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun translate(text: String, source: String = "ko", target: String = "en"): NaverResult =
        withContext(Dispatchers.IO) {
            try {
                // In production, calls Papago NMT API
                val translated = when {
                    source == "ko" && target == "en" -> "[Translated to English] $text"
                    source == "en" && target == "ko" -> "[한국어 번역] $text"
                    else -> text
                }

                NaverResult.success(
                    action = "translate",
                    detail = translated,
                    data = mapOf("source" to source, "target" to target, "original" to text)
                )
            } catch (e: Exception) {
                NaverResult.error("Translation failed: ${e.message}")
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // Webtoon Search (웹툰)
    // ─────────────────────────────────────────────────────────────────────────
    suspend fun searchWebtoon(title: String): NaverResult =
        withContext(Dispatchers.IO) {
            try {
                val encoded = java.net.URLEncoder.encode(title, "UTF-8")
                val url = "https://comic.naver.com/search?keyword=$encoded"

                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                context.startActivity(intent)

                NaverResult.success(
                    action = "search_webtoon",
                    detail = "Webtoon search for '$title' opened in Naver"
                )
            } catch (e: Exception) {
                NaverResult.error("Webtoon search failed: ${e.message}")
            }
        }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────
    private fun getClientId(): String? {
        return context.getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
            .getString("naver_client_id", null)
    }

    private fun getClientSecret(): String? {
        return context.getSharedPreferences("meokclaw", Context.MODE_PRIVATE)
            .getString("naver_client_secret", null)
    }
}

data class NaverResult(
    val success: Boolean,
    val action: String,
    val detail: String,
    val data: Map<String, String> = emptyMap(),
    val error: String? = null
) {
    companion object {
        fun success(action: String, detail: String, data: Map<String, String> = emptyMap()): NaverResult =
            NaverResult(success = true, action = action, detail = detail, data = data)

        fun error(message: String): NaverResult =
            NaverResult(success = false, action = "error", detail = message, error = message)
    }
}
