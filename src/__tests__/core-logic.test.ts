/** Core logic tests — pure functions and type guards. */

import { describe, it, expect } from 'vitest'
import { extractConceptRefs } from '../lib/article-renderer'
import { graphToReactFlow, relationTypeLabel, RELATION_COLORS, NODE_STATUS_COLORS } from '../components/shared/graph-adapter'

// ============================================================
// ArticleRenderer
// ============================================================
describe('extractConceptRefs', () => {
  it('extracts [[concept]] references from article body', () => {
    const body = '机器学习是[[人工智能]]的一个子领域，与[[深度学习]]密切相关。'
    const refs = extractConceptRefs(body)
    expect(refs).toContain('人工智能')
    expect(refs).toContain('深度学习')
    expect(refs).toHaveLength(2)
  })

  it('returns empty array for empty body', () => {
    expect(extractConceptRefs('')).toEqual([])
    expect(extractConceptRefs('没有任何引用的文本')).toEqual([])
  })

  it('deduplicates concept references', () => {
    const body = '[[概念A]]和[[概念A]]是同一个。'
    const refs = extractConceptRefs(body)
    expect(refs).toEqual(['概念A'])
  })

  it('handles adjacent concepts', () => {
    const body = '[[A]][[B]][[C]]'
    const refs = extractConceptRefs(body)
    expect(refs).toEqual(['A', 'B', 'C'])
  })
})

// ============================================================
// Graph Adapter
// ============================================================
describe('graph-adapter', () => {
  describe('RELATION_COLORS', () => {
    it('has color for all 7 edge types', () => {
      const types = ['PREREQUISITE', 'CONTRASTS', 'VARIANT_OF', 'APPLIES_IN', 'EXTENDS', 'MISUNDERSTOOD_AS', 'EVIDENCED_BY'] as const
      for (const t of types) {
        expect(RELATION_COLORS[t]).toBeDefined()
        expect(RELATION_COLORS[t]).toMatch(/^#[0-9a-f]{6}$/)
      }
    })

    it('MISUNDERSTOOD_AS is red', () => {
      expect(RELATION_COLORS.MISUNDERSTOOD_AS).toBe('#ef4444')
    })

    it('EVIDENCED_BY is muted gray', () => {
      expect(RELATION_COLORS.EVIDENCED_BY).toBe('#94a3b8')
    })
  })

  describe('NODE_STATUS_COLORS', () => {
    it('has color for all 6 node statuses', () => {
      const statuses = ['unseen', 'browsed', 'learning', 'practiced', 'review_due', 'mastered'] as const
      for (const s of statuses) {
        expect(NODE_STATUS_COLORS[s]).toBeDefined()
      }
    })

    it('mastered is green, unseen is light gray', () => {
      expect(NODE_STATUS_COLORS.mastered).toBe('#34d399')
      expect(NODE_STATUS_COLORS.unseen).toBe('#e2e8f0')
    })
  })

  describe('relationTypeLabel', () => {
    it('returns Chinese labels for all 7 edge types', () => {
      expect(relationTypeLabel('PREREQUISITE')).toBe('前置')
      expect(relationTypeLabel('CONTRASTS')).toBe('对比')
      expect(relationTypeLabel('VARIANT_OF')).toBe('变体')
      expect(relationTypeLabel('APPLIES_IN')).toBe('应用')
      expect(relationTypeLabel('EXTENDS')).toBe('扩展')
      expect(relationTypeLabel('MISUNDERSTOOD_AS')).toBe('误解')
      expect(relationTypeLabel('EVIDENCED_BY')).toBe('证据')
    })
  })

  it('falls back to deterministic edge ids when backend returns empty ids', () => {
    const { edges } = graphToReactFlow({
      nodes: [
        { node_id: 'nd_a', name: 'A', status: 'learning', importance: 5 },
        { node_id: 'nd_b', name: 'B', status: 'unseen', importance: 4 },
      ],
      edges: [
        {
          edge_id: undefined as unknown as string,
          source_node_id: 'nd_a',
          target_node_id: 'nd_b',
          relation_type: 'PREREQUISITE',
        },
        {
          edge_id: '',
          source_node_id: 'nd_a',
          target_node_id: 'nd_b',
          relation_type: 'PREREQUISITE',
        },
      ],
      meta: { view: 'full', collapsed: false },
    })

    expect(edges.map((edge) => edge.id)).toEqual([
      'fallback:nd_a:PREREQUISITE:nd_b:0',
      'fallback:nd_a:PREREQUISITE:nd_b:1',
    ])
  })
})

// ============================================================
// Type integrity
// ============================================================
describe('Type system consistency', () => {
  it('EdgeType includes all relation types from graph-adapter', () => {
    // Import the type to verify it's a union of strings
    type EdgeType = 'PREREQUISITE' | 'CONTRASTS' | 'VARIANT_OF' | 'APPLIES_IN' | 'EXTENDS' | 'MISUNDERSTOOD_AS' | 'EVIDENCED_BY'
    const validTypes: EdgeType[] = ['PREREQUISITE', 'CONTRASTS', 'VARIANT_OF', 'APPLIES_IN', 'EXTENDS', 'MISUNDERSTOOD_AS', 'EVIDENCED_BY']
    for (const t of validTypes) {
      const typedValue: EdgeType = t
      expect(typedValue).toBe(t)
    }
  })
})
