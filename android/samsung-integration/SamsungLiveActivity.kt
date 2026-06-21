package com.meokclaw.samsung.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.widget.RemoteViews
import kotlinx.coroutines.*

/**
 * MEOKCLAW Samsung Live Activity — Android Equivalent of Dynamic Island
 *
 * Samsung devices don't have a Dynamic Island, but they have:
 *   - Edge Panel (swipe from screen edge)
 *   - Always On Display (AOD)
 *   - Lock Screen widgets
 *   - Notification with custom layouts
 *   - Multi-window pop-up view
 *   - Samsung Good Lock modules
 *
 * MEOKCLAW creates a "Council Widget" that appears across ALL these surfaces,
 * showing real-time model deliberation status, cost, and consensus.
 */
class SamsungLiveActivity : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        appWidgetIds.forEach { appWidgetId ->
            updateAppWidget(context, appWidgetManager, appWidgetId)
        }
    }

    companion object {
        fun updateAppWidget(
            context: Context,
            appWidgetManager: AppWidgetManager,
            appWidgetId: Int
        ) {
            val views = RemoteViews(context.packageName, R.layout.samsung_council_widget)

            // Set up click handlers
            views.setOnClickPendingIntent(
                R.id.widget_container,
                openAppPendingIntent(context)
            )

            // Update model orbs
            updateModelOrbs(context, views)

            // Update cost ticker
            updateCostTicker(context, views)

            appWidgetManager.updateAppWidget(appWidgetId, views)
        }

        private fun updateModelOrbs(context: Context, views: RemoteViews) {
            val prefs = context.getSharedPreferences("meokclaw_widget", Context.MODE_PRIVATE)
            val modelCount = prefs.getInt("model_count", 3)
            val statuses = prefs.getStringSet("model_statuses", emptySet()) ?: emptySet()

            // Show colored dots for each model
            val orbColors = listOf(
                R.id.orb_1, R.id.orb_2, R.id.orb_3,
                R.id.orb_4, R.id.orb_5, R.id.orb_6
            )

            orbColors.forEachIndexed { index, orbId ->
                if (index < modelCount) {
                    val status = statuses.elementAtOrNull(index) ?: "thinking"
                    val color = when (status) {
                        "thinking" -> R.drawable.orb_pulsing
                        "done" -> R.drawable.orb_green
                        "dissenting" -> R.drawable.orb_orange
                        "error" -> R.drawable.orb_red
                        else -> R.drawable.orb_pulsing
                    }
                    views.setImageViewResource(orbId, color)
                    views.setViewVisibility(orbId, android.view.View.VISIBLE)
                } else {
                    views.setViewVisibility(orbId, android.view.View.GONE)
                }
            }
        }

        private fun updateCostTicker(context: Context, views: RemoteViews) {
            val prefs = context.getSharedPreferences("meokclaw_widget", Context.MODE_PRIVATE)
            val totalCost = prefs.getFloat("total_cost", 0.0f)
            val elapsedMs = prefs.getLong("elapsed_ms", 0)

            views.setTextViewText(
                R.id.cost_ticker,
                "$${String.format("%.4f", totalCost)} · ${elapsedMs / 1000}s"
            )
        }

        private fun openAppPendingIntent(context: Context): android.app.PendingIntent {
            val intent = android.content.Intent(context, SamsungDeXWarRoom::class.java)
            return android.app.PendingIntent.getActivity(
                context, 0, intent,
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or
                        android.app.PendingIntent.FLAG_IMMUTABLE
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Edge Panel Service — Council quick access
// ─────────────────────────────────────────────────────────────────────────
class CouncilEdgePanel : android.service.quicksettings.TileService() {

    override fun onClick() {
        super.onClick()
        // Launch council quick action
        val intent = android.content.Intent(this, SamsungDeXWarRoom::class.java).apply {
            flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK
            putExtra("quick_council", true)
        }
        startActivityAndCollapse(intent)
    }

    override fun onStartListening() {
        super.onStartListening()
        qsTile?.apply {
            state = android.service.quicksettings.Tile.STATE_ACTIVE
            label = "MEOKCLAW Council"
            contentDescription = "Launch MEOKCLAW Council"
            updateTile()
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Always On Display — Minimal council status
// ─────────────────────────────────────────────────────────────────────────
class CouncilAODService : android.service.dreams.DreamService() {

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        isInteractive = false
        isFullscreen = true

        val views = RemoteViews(packageName, R.layout.samsung_council_aod)
        setContentView(views.apply(this, window.decorView.rootView as android.view.ViewGroup))

        // Show minimal council status on AOD
        updateAODStatus()
    }

    private fun updateAODStatus() {
        // Show: "Council: 2/3 done · $0.0003"
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Notification with custom layout — Real-time updates
// ─────────────────────────────────────────────────────────────────────────
class CouncilNotificationManager(private val context: Context) {

    private val notificationManager = context.getSystemService(android.content.Context.NOTIFICATION_SERVICE)
            as android.app.NotificationManager
    private val channelId = "meokclaw_council"

    init {
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = android.app.NotificationChannel(
                channelId,
                "MEOKCLAW Council",
                android.app.NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Real-time council deliberation updates"
                setShowBadge(true)
            }
            notificationManager.createNotificationChannel(channel)
        }
    }

    fun showCouncilNotification(state: CouncilUiState) {
        val builder = android.app.Notification.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_council_notification)
            .setOngoing(true)
            .setPriority(android.app.Notification.PRIORITY_LOW)

        when (state) {
            is CouncilUiState.Deliberating -> {
                val thinkingCount = state.models.count { it.status == ModelStatus.THINKING }
                builder.setContentTitle("Council Deliberating...")
                    .setContentText("$thinkingCount/${state.models.size} models thinking · $${String.format("%.4f", state.totalCost)}")
                    .setProgress(state.models.size, state.models.size - thinkingCount, false)
            }
            is CouncilUiState.Consensus -> {
                builder.setContentTitle("Consensus Reached")
                    .setContentText("${state.consensusText.take(50)}... · $${String.format("%.4f", state.totalCost)}")
                    .setProgress(0, 0, false)
                    .setOngoing(false)
            }
            is CouncilUiState.Error -> {
                builder.setContentTitle("Council Error")
                    .setContentText(state.message)
                    .setOngoing(false)
            }
            else -> {
                builder.setContentTitle("MEOKCLAW Council")
                    .setContentText("Ready")
            }
        }

        notificationManager.notify(1001, builder.build())
    }

    fun dismissCouncilNotification() {
        notificationManager.cancel(1001)
    }
}

// Stub references
class SamsungDeXWarRoom : android.app.Activity()
class CouncilUiState
enum class ModelStatus { THINKING, DONE, DISSENTING, ERROR }
