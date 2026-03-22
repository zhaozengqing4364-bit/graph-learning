import type { CompleteSessionResponse } from '../types'

type ReviewCandidate = CompleteSessionResponse['synthesis']['review_candidates'][number]

export interface SummaryDisplayInput {
  summary?: string
  synthesis?: Partial<CompleteSessionResponse['synthesis']>
  partial_summary?: boolean
}

export interface SummaryDisplay {
  sessionSummary: string
  keyTakeaways: string[]
  nextRecommendations: CompleteSessionResponse['synthesis']['next_recommendations']
  reviewItemsCreated: number | null
  newAssetsCount: number | null
  coveredScope: string | null
  skippableNodes: string[]
  reviewCandidates: Array<{
    node_id: string
    node_name: string
    reason: string
    review_id: string
    status: 'pending'
  }>
  assetHighlights: Array<{
    node_id: string
    practice_type: string
    correctness?: number
  }>
  hasDetailedSynthesis: boolean
}

function normalizeReviewCandidates(
  reviewCandidates: ReviewCandidate[] | undefined,
  fallbackReason: string,
) {
  return (reviewCandidates || []).map((candidate) => ({
    node_id: candidate.node_id || '',
    node_name: candidate.node_name || candidate.name || '',
    reason: candidate.reason || fallbackReason,
    review_id: candidate.review_id || '',
    status: 'pending' as const,
  }))
}

export function buildSummaryPresentation(summary: SummaryDisplayInput): SummaryDisplay {
  const hasDetailedSynthesis = Boolean(summary.synthesis) && !summary.partial_summary
  const synthesis = summary.synthesis || {}
  const sessionSummary = synthesis.mainline_summary || summary.summary || '本轮学习已完成'

  return {
    sessionSummary,
    keyTakeaways: hasDetailedSynthesis ? synthesis.key_takeaways || [] : [],
    nextRecommendations: hasDetailedSynthesis ? synthesis.next_recommendations || [] : [],
    reviewItemsCreated: hasDetailedSynthesis ? (synthesis.review_items_created ?? 0) : null,
    newAssetsCount: hasDetailedSynthesis ? (synthesis.new_assets_count ?? 0) : null,
    coveredScope: hasDetailedSynthesis ? (synthesis.covered_scope || null) : null,
    skippableNodes: hasDetailedSynthesis ? synthesis.skippable_nodes || [] : [],
    reviewCandidates: hasDetailedSynthesis
      ? normalizeReviewCandidates(synthesis.review_candidates, synthesis.mainline_summary ? '系统推荐复习' : '')
      : [],
    assetHighlights: hasDetailedSynthesis ? (synthesis.asset_highlights || []) : [],
    hasDetailedSynthesis,
  }
}
