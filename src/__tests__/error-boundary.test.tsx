import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { ErrorBoundary } from '../components/ui/error-boundary'

describe('ErrorBoundary', () => {
  const originalWarn = console.warn
  beforeEach(() => { console.warn = vi.fn() })
  afterEach(() => { console.warn = originalWarn })

  describe('getDerivedStateFromError', () => {
    it('returns error state', () => {
      const error = new Error('test')
      const state = ErrorBoundary.getDerivedStateFromError(error)
      expect(state).toEqual({ hasError: true, error })
    })
  })

  describe('_isFatal heuristic', () => {
    const eb = new ErrorBoundary({ children: null })

    it('returns false for network errors', () => {
      expect((eb as any)._isFatal(new Error('Failed to fetch data'))).toBe(false)
    })

    it('returns false for NETWORK_ERROR', () => {
      expect((eb as any)._isFatal(new Error('NETWORK_ERROR'))).toBe(false)
    })

    it('returns false for chunk loading errors', () => {
      expect((eb as any)._isFatal(new Error('Loading chunk 123 failed'))).toBe(false)
    })

    it('returns false for timeout errors', () => {
      expect((eb as any)._isFatal(new Error('Request timeout'))).toBe(false)
    })

    it('returns false for errors containing 加载', () => {
      expect((eb as any)._isFatal(new Error('加载失败'))).toBe(false)
    })

    it('returns true for generic render errors', () => {
      expect((eb as any)._isFatal(new Error('Cannot read property of undefined'))).toBe(true)
    })

    it('returns true for null error', () => {
      expect((eb as any)._isFatal(null)).toBe(true)
    })

    it('returns true for TypeError', () => {
      expect((eb as any)._isFatal(new TypeError('undefined is not a function'))).toBe(true)
    })
  })

  describe('rendering', () => {
    it('renders children when no error', () => {
      const html = renderToStaticMarkup(
        createElement(ErrorBoundary, null, createElement('p', null, '正常内容')),
      )
      expect(html).toContain('正常内容')
    })
  })
})
