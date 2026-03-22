import { describe, expect, it } from 'vitest'

import { resolveReviewNodeTitle } from '../lib/review-display'

describe('review display helpers', () => {
  it('falls back to the queue item node name when review detail has an empty title', () => {
    expect(resolveReviewNodeTitle(
      { review_id: 'rv_1', node_id: 'nd_1', node_name: '', topic_id: 'tp_1' },
      [{ review_id: 'rv_1', node_id: 'nd_1', node_name: '消息传递', topic_id: 'tp_1' }],
    )).toBe('消息传递')
  })

  it('falls back to node id when no title is available anywhere', () => {
    expect(resolveReviewNodeTitle(
      { review_id: 'rv_1', node_id: 'nd_1', node_name: '', topic_id: 'tp_1' },
      [],
    )).toBe('nd_1')
  })
})
