import { describe, expect, it } from 'vitest'
import { queryKeys } from '../lib/query-keys'

describe('Query key factory', () => {
  it('produces unique keys for different topics', () => {
    const k1 = queryKeys.topic('tp_1')
    const k2 = queryKeys.topic('tp_2')
    expect(JSON.stringify(k1)).not.toBe(JSON.stringify(k2))
  })

  it('produces unique keys for different nodes', () => {
    const k1 = queryKeys.nodeDetail('tp_1', 'nd_1')
    const k2 = queryKeys.nodeDetail('tp_1', 'nd_2')
    expect(JSON.stringify(k1)).not.toBe(JSON.stringify(k2))
  })

  it('topics key includes params', () => {
    const k1 = queryKeys.topics({ limit: 10 })
    const k2 = queryKeys.topics({ limit: 20 })
    expect(JSON.stringify(k1)).not.toBe(JSON.stringify(k2))
  })

  it('all key factories return arrays', () => {
    const keys = [
      queryKeys.topics(),
      queryKeys.topic('tp_1'),
      queryKeys.nodeDetail('tp_1', 'nd_1'),
      queryKeys.graph('tp_1'),
      queryKeys.topicWorkspace('tp_1'),
      queryKeys.topicReadingState('tp_1'),
    ]
    for (const key of keys) {
      expect(Array.isArray(key)).toBe(true)
      expect(key.length).toBeGreaterThan(0)
    }
  })

  it('topic key starts with correct prefix', () => {
    expect(queryKeys.topic('tp_1')[0]).toBe('topic')
  })

  it('topics key starts with correct prefix', () => {
    expect(queryKeys.topics()[0]).toBe('topics')
  })

  it('node keys include topic and node id', () => {
    const k = queryKeys.nodeDetail('tp_1', 'nd_1')
    expect(k).toContain('tp_1')
    expect(k).toContain('nd_1')
  })
})
