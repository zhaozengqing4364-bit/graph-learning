import { describe, expect, it } from 'vitest'

import { buildSummaryPresentation } from '../lib/summary-display'

describe('summary presentation', () => {
  it('treats session-only fallback data as partial and avoids fake precise counts', () => {
    const presentation = buildSummaryPresentation({
      summary: '本轮学习已完成',
      synthesis: undefined,
      partial_summary: true,
    })

    expect(presentation.hasDetailedSynthesis).toBe(false)
    expect(presentation.newAssetsCount).toBeNull()
    expect(presentation.reviewItemsCreated).toBeNull()
    expect(presentation.nextRecommendations).toEqual([])
  })

  it('preserves detailed synthesis when it is truly available', () => {
    const presentation = buildSummaryPresentation({
      summary: '兜底摘要',
      synthesis: {
        mainline_summary: '真实收束总结',
        key_takeaways: ['A'],
        next_recommendations: [{ node_id: 'nd_1', name: '概念 A', summary: '继续学习' }],
        review_items_created: 2,
        new_assets_count: 1,
        covered_scope: '主干链路',
        skippable_nodes: ['支线概念'],
        review_candidates: [{ node_id: 'nd_2', node_name: '概念 B', reason: '系统推荐复习', review_id: 'rv_1' }],
      },
    })

    expect(presentation.hasDetailedSynthesis).toBe(true)
    expect(presentation.sessionSummary).toBe('真实收束总结')
    expect(presentation.newAssetsCount).toBe(1)
    expect(presentation.reviewItemsCreated).toBe(2)
    expect(presentation.reviewCandidates).toHaveLength(1)
  })
})
