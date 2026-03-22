/**
 * Tauri IPC bridge for AxonClone.
 *
 * Provides typed wrappers around Tauri's invoke() for backend communication
 * via sidecar process. Falls back to HTTP when running in dev mode (browser).
 */

interface TauriInternals {
  invoke: <T = unknown>(cmd: string, args?: Record<string, unknown>) => Promise<T>
}

type TauriWindow = Window & {
  __TAURI_INTERNALS__?: TauriInternals
}

// Tauri invoke is only available in the desktop build, not in dev browser mode
const tauriInvoke = typeof window !== "undefined"
  ? (window as TauriWindow).__TAURI_INTERNALS__?.invoke ?? null
  : null

/** Check if running inside Tauri desktop shell (not browser dev mode) */
export function isTauriDesktop(): boolean {
  return tauriInvoke !== null
}

/** Invoke a Tauri command. Falls back to null in browser dev mode. */
export async function tauriCommand<T = unknown>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T | null> {
  if (!tauriInvoke) return null
  try {
    return await tauriInvoke(cmd, args)
  } catch (e) {
    console.warn(`[Tauri] Command ${cmd} failed:`, e)
    return null
  }
}

/** Start the Python backend sidecar. */
export async function startBackend(): Promise<boolean> {
  const result = await tauriCommand<{ success: boolean }>("start_backend")
  return result?.success ?? false
}

/** Stop the Python backend sidecar. */
export async function stopBackend(): Promise<boolean> {
  const result = await tauriCommand<{ success: boolean }>("stop_backend")
  return result?.success ?? false
}

/** Check if backend is healthy via Tauri command. */
export async function checkBackendHealth(): Promise<boolean> {
  const result = await tauriCommand<{ status: string }>("check_backend_health")
  return result?.status === "ok"
}

/**
 * Get the backend API base URL.
 * In Tauri desktop mode: http://127.0.0.1:8000/api/v1 (sidecar)
 * In browser dev mode: http://localhost:8000/api/v1 (vite proxy)
 */
export function getApiBaseUrl(): string {
  if (isTauriDesktop()) {
    return "http://127.0.0.1:8000/api/v1"
  }
  // In dev mode, Vite proxy forwards /api/* to backend
  return "/api/v1"
}
