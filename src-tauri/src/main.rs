#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::process::Child;
use std::sync::Mutex;

/// Sidecar process handle (shared across commands)
struct SidecarState {
    process: Option<Child>,
}

impl Default for SidecarState {
    fn default() -> Self {
        Self { process: None }
    }
}

#[derive(Serialize, Deserialize, Clone)]
struct StartResult {
    success: bool,
}

#[derive(Serialize, Deserialize, Clone)]
struct StopResult {
    success: bool,
}

#[derive(Serialize, Deserialize, Clone)]
struct HealthResult {
    status: String,
}

#[tauri::command]
async fn start_backend(state: tauri::State<'_, Mutex<SidecarState>>) -> StartResult {
    let mut guard = state.lock().unwrap();

    // Already running?
    if guard.process.is_some() {
        return StartResult { success: true };
    }

    // Try to spawn the Python backend sidecar
    // In production, the sidecar binary is bundled; in dev, we use uvicorn directly
    #[cfg(target_os = "windows")]
    let cmd = "axon-server.exe";
    #[cfg(not(target_os = "windows"))]
    let cmd = "axon-server";

    use std::process::Command;
    match Command::new(cmd).spawn() {
        Ok(child) => {
            guard.process = Some(child);
            StartResult { success: true }
        }
        Err(e) => {
            eprintln!("[AxonClone] Failed to start backend sidecar: {}", e);
            eprintln!("[AxonClone] Ensure the sidecar binary is bundled or run the backend manually.");
            StartResult { success: false }
        }
    }
}

#[tauri::command]
async fn stop_backend(state: tauri::State<'_, Mutex<SidecarState>>) -> StopResult {
    let mut guard = state.lock().unwrap();

    if let Some(ref mut child) = guard.process {
        let _ = child.kill();
        let _ = child.wait();
        guard.process = None;
    }

    StopResult { success: true }
}

#[tauri::command]
async fn check_backend_health() -> HealthResult {
    // Simple HTTP health check against the local backend
    let url = "http://127.0.0.1:8000/api/v1/health";

    match reqwest::Client::new()
        .get(url)
        .timeout(std::time::Duration::from_secs(3))
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => HealthResult {
            status: "ok".to_string(),
        },
        _ => HealthResult {
            status: "unavailable".to_string(),
        },
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Mutex::new(SidecarState::default()))
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            check_backend_health,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
