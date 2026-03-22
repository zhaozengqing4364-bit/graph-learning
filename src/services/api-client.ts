import axios from 'axios'
import type { ApiResponse } from '../types'
import { getApiBaseUrl } from '../lib/tauri'

// Reject URLs with path traversal sequences
const _URL_TRAVERSAL_RE = /\.\./

const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — reserved for future auth token injection
apiClient.interceptors.request.use((config) => config)

// Response interceptor — normalize network errors into ApiError
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (!err.response) {
      // No response = network error (server unreachable, timeout, CORS)
      const message = err.code === 'ECONNABORTED'
        ? '请求超时，请检查网络连接后重试'
        : '网络连接失败，请检查后端是否运行'
      throw new ApiError({ code: 'NETWORK_ERROR', message })
    }
    // Server responded with error status — let caller handle via existing logic
    return Promise.reject(err)
  },
)

// Guard: reject URLs containing path traversal sequences
function guardUrl(url: string): void {
  if (_URL_TRAVERSAL_RE.test(url)) {
    throw new ApiError({ code: 'INVALID_URL', message: `请求路径包含非法字符 (${url.slice(0, 80)})` })
  }
}

// Validate and unwrap standard response envelope
function unwrapEnvelope<T>(res: { data: ApiResponse<T> }, url: string): T {
  const body = res.data
  // Guard: response must be a valid envelope object
  if (body === null || typeof body !== 'object' || typeof body.success !== 'boolean') {
    throw new ApiError({ code: 'INVALID_RESPONSE', message: `服务端响应格式异常 (${url})` })
  }
  if (!body.success) {
    const err = body.error ?? { code: 'UNKNOWN_ERROR', message: '未知错误', details: {} }
    throw new ApiError(err)
  }
  return body.data
}

export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  guardUrl(url)
  const res = await apiClient.get<ApiResponse<T>>(url, { params })
  return unwrapEnvelope(res, url)
}

export async function apiPost<T>(url: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  guardUrl(url)
  const res = await apiClient.post<ApiResponse<T>>(url, body, { params })
  return unwrapEnvelope(res, url)
}

export async function apiPatch<T>(url: string, body?: unknown): Promise<T> {
  guardUrl(url)
  const res = await apiClient.patch<ApiResponse<T>>(url, body)
  return unwrapEnvelope(res, url)
}

export async function apiPut<T>(url: string, body?: unknown): Promise<T> {
  guardUrl(url)
  const res = await apiClient.put<ApiResponse<T>>(url, body)
  return unwrapEnvelope(res, url)
}

export async function apiDelete<T>(url: string): Promise<T> {
  guardUrl(url)
  const res = await apiClient.delete<ApiResponse<T>>(url)
  return unwrapEnvelope(res, url)
}

// Extended timeout (120s) for AI-heavy requests (topic creation, node expansion, practice, etc.)
export async function apiPostLong<T>(url: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  guardUrl(url)
  const res = await apiClient.post<ApiResponse<T>>(url, body, { params, timeout: 120_000 })
  return unwrapEnvelope(res, url)
}

export class ApiError extends Error {
  code: string
  details?: Record<string, unknown>

  constructor(err: { code: string; message: string; details?: Record<string, unknown> }) {
    super(err.message)
    this.name = 'ApiError'
    this.code = err.code
    this.details = err.details
  }
}

export default apiClient
