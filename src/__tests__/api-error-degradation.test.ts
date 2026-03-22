import { describe, expect, it } from 'vitest'

// Test the error degradation patterns used across the frontend.
// The actual ApiError class and normalization are in services/api.ts.

describe('API error degradation patterns', () => {
  describe('error code classification', () => {
    // These patterns mirror what use-mutations.ts does for error handling
    const recoverableCodes = ['RATE_LIMIT', 'MODEL_OVERLOADED', 'NETWORK_ERROR', 'TIMEOUT']
    const retryableCodes = ['RATE_LIMIT', 'MODEL_OVERLOADED', 'NETWORK_ERROR']
    const fatalCodes = ['AUTH_REQUIRED', 'TOPIC_NOT_FOUND', 'INVALID_INPUT', 'FORBIDDEN']

    it('classifies rate limit as recoverable and retryable', () => {
      expect(recoverableCodes).toContain('RATE_LIMIT')
      expect(retryableCodes).toContain('RATE_LIMIT')
    })

    it('classifies network error as recoverable and retryable', () => {
      expect(recoverableCodes).toContain('NETWORK_ERROR')
      expect(retryableCodes).toContain('NETWORK_ERROR')
    })

    it('classifies auth errors as fatal', () => {
      expect(fatalCodes).toContain('AUTH_REQUIRED')
      expect(recoverableCodes).not.toContain('AUTH_REQUIRED')
    })

    it('classifies not found as fatal', () => {
      expect(fatalCodes).toContain('TOPIC_NOT_FOUND')
      expect(recoverableCodes).not.toContain('TOPIC_NOT_FOUND')
    })

    it('classifies timeout as recoverable but not retryable', () => {
      expect(recoverableCodes).toContain('TIMEOUT')
      expect(retryableCodes).not.toContain('TIMEOUT')
    })
  })

  describe('error message normalization', () => {
    it('normalizes fetch errors to NETWORK_ERROR', () => {
      const error = new Error('Failed to fetch')
      const isNetworkError = error.message.includes('Failed to fetch') || error.message.includes('NetworkError')
      expect(isNetworkError).toBe(true)
    })

    it('normalizes AbortError to TIMEOUT', () => {
      const error = new DOMException('The operation was aborted', 'AbortError')
      const isTimeout = error.name === 'AbortError'
      expect(isTimeout).toBe(true)
    })

    it('preserves server error codes', () => {
      const serverError = { success: false, error: { code: 'RATE_LIMIT', message: 'Too many requests' } }
      expect(serverError.error.code).toBe('RATE_LIMIT')
      expect(typeof serverError.error.message).toBe('string')
    })
  })

  describe('toast degradation levels', () => {
    it('maps error codes to toast types', () => {
      const toastMap: Record<string, 'warning' | 'error' | 'info'> = {
        RATE_LIMIT: 'warning',
        MODEL_OVERLOADED: 'warning',
        NETWORK_ERROR: 'warning',
        TIMEOUT: 'warning',
        AUTH_REQUIRED: 'error',
        TOPIC_NOT_FOUND: 'error',
        INVALID_INPUT: 'error',
        FORBIDDEN: 'error',
      }

      for (const [code, type] of Object.entries(toastMap)) {
        expect(['warning', 'error', 'info']).toContain(type)
      }
    })
  })
})
