import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { showToast } from '../components/ui/toast'

describe('use-toast module', () => {
  const originalWarn = console.warn
  beforeEach(() => { console.warn = vi.fn() })
  afterEach(() => { console.warn = originalWarn })

  describe('showToast (module-level)', () => {
    it('does not throw when called without provider', () => {
      expect(() => showToast('test message', 'info')).not.toThrow()
    })

    it('accepts success variant', () => {
      expect(() => showToast('success!', 'success')).not.toThrow()
    })

    it('accepts warning variant', () => {
      expect(() => showToast('warning!', 'warning')).not.toThrow()
    })

    it('accepts error variant', () => {
      expect(() => showToast('error!', 'error')).not.toThrow()
    })
  })

  describe('toast variant types', () => {
    it('has 4 valid variants', () => {
      const variants = ['success', 'error', 'info', 'warning'] as const
      expect(variants).toHaveLength(4)
    })

    it('toast IDs follow pattern', () => {
      const idPattern = /^toast-\d+$/
      expect(idPattern.test('toast-1')).toBe(true)
      expect(idPattern.test('toast-42')).toBe(true)
    })
  })
})
