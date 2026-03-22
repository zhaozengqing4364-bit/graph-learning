import { describe, expect, it } from 'vitest'
import { AssetsPage } from '../routes/assets-page'

describe('AssetsPage', () => {
  it('practice type labels are complete', () => {
    const labels: Record<string, string> = {
      define: '定义',
      example: '举例',
      contrast: '对比',
      apply: '应用',
      teach_beginner: '教学',
      compress: '压缩',
      explain: '解释',
    }
    expect(Object.keys(labels)).toHaveLength(7)
    for (const [key, label] of Object.entries(labels)) {
      expect(typeof label).toBe('string')
      expect(label.length).toBeGreaterThan(0)
      expect(key).toMatch(/^[a-z_]+$/)
    }
  })

  it('component can be referenced without crash', () => {
    expect(typeof AssetsPage).toBe('function')
  })
})
