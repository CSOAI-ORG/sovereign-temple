// MEOKCLAW Desktop — Tauri Backend
// Minimal Rust wrapper around the Next.js web UI.
// Provides: native FS access, OS notifications, single-instance guard, auto-updater.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::{Manager, WindowEvent};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, argv, cwd| {
            println!("Single instance triggered: {:?} {:?}", argv, cwd);
            let window = app.get_window("main").unwrap();
            window.set_focus().unwrap();
        }))
        .setup(|app| {
            // Hide dock icon on macOS if desired
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Regular);
            Ok(())
        })
        .on_window_event(|event| match event.event() {
            WindowEvent::CloseRequested { api, .. } => {
                // Hide to tray instead of closing (optional)
                // event.window().hide().unwrap();
                // api.prevent_close();
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_os_info,
            check_local_model
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! MEOKCLAW is ready.", name)
}

#[tauri::command]
fn get_os_info() -> serde_json::Value {
    serde_json::json!({
        "platform": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "family": std::env::consts::FAMILY,
    })
}

#[tauri::command]
fn check_local_model(model_name: &str) -> serde_json::Value {
    // Check if a GGUF model exists in the app data directory
    // Real implementation would scan ~/.meokclaw/models/
    serde_json::json!({
        "model": model_name,
        "exists": false,
        "path": "",
        "size_mb": 0,
    })
}
