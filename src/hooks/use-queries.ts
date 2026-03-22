import { useQuery } from '@tanstack/react-query'
import {
  getArticleBacklinks,
  getConceptCandidates,
  getConceptNote,
  getTopics,
  getTopic,
  getNodeDetail,
  getGraph,
  getMainline,
  getNeighborhood,
  getEntryNode,
  getSession,
  getExpressionAssets,
  getNodeAbility,
  getAbilityOverview,
  getFrictions,
  getReviews,
  getReviewDetail,
  getSettings,
  getHealth,
  getSystemCapabilities,
  getDeferredNodes,
  getPracticeAttempts,
  getRecommendedPracticeType,
  getGlobalStats,
  getTopicStats,
  getAbilitySnapshots,
  getReadingState,
  getSourceArticle,
  getSourceArticles,
  getWorkspaceBundle,
  searchWorkspace,
} from '../services'
import { queryKeys } from '../lib/query-keys'
import type { CompleteSessionResponse, GraphView, PracticeType, Session } from '../types'

// Shared query presets — AI-backed queries should not retry; data queries use short stale
const _AI_QUERY = { retry: false, staleTime: 0 } as const

// ---- Topics ----
export const useTopicListQuery = (params?: { status?: string; limit?: number; q?: string }) =>
  useQuery({
    queryKey: queryKeys.topics(params),
    queryFn: () => getTopics(params),
  })

export const useTopicQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.topic(topicId),
    queryFn: () => getTopic(topicId),
    enabled: !!topicId,
  })

export const useEntryNodeQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.topicEntryNode(topicId),
    queryFn: () => getEntryNode(topicId),
    enabled: !!topicId,
    ..._AI_QUERY,
  })

export const useWorkspaceBundleQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.topicWorkspace(topicId),
    queryFn: () => getWorkspaceBundle(topicId),
    enabled: !!topicId,
  })

export const useSourceArticlesQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.topicArticles(topicId),
    queryFn: () => getSourceArticles(topicId),
    enabled: !!topicId,
  })

export const useSourceArticleQuery = (topicId: string, articleId: string) =>
  useQuery({
    queryKey: queryKeys.topicArticle(topicId, articleId),
    queryFn: () => getSourceArticle(topicId, articleId),
    enabled: !!topicId && !!articleId,
  })

export const useConceptNoteQuery = (topicId: string, conceptKey: string) =>
  useQuery({
    queryKey: queryKeys.topicConceptNote(topicId, conceptKey),
    queryFn: () => getConceptNote(topicId, conceptKey),
    enabled: !!topicId && !!conceptKey,
  })

export const useReadingStateQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.topicReadingState(topicId),
    queryFn: () => getReadingState(topicId),
    enabled: !!topicId,
  })

export const useConceptCandidatesQuery = (topicId: string, status?: string) =>
  useQuery({
    queryKey: queryKeys.topicConceptCandidates(topicId, status),
    queryFn: () => getConceptCandidates(topicId, status ? { status } : undefined),
    enabled: !!topicId,
  })

export const useWorkspaceSearchQuery = (topicId: string, query: string) =>
  useQuery({
    queryKey: queryKeys.topicWorkspaceSearch(topicId, query),
    queryFn: () => searchWorkspace(topicId, { q: query }),
    enabled: !!topicId && !!query.trim(),
  })

export const useBacklinksQuery = (topicId: string, nodeId: string | null) =>
  useQuery({
    queryKey: queryKeys.nodeBacklinks(topicId, nodeId!),
    queryFn: () => getArticleBacklinks(topicId, nodeId!),
    enabled: !!topicId && !!nodeId,
  })

// ---- Nodes ----
export const useNodeDetailQuery = (topicId: string, nodeId: string) =>
  useQuery({
    queryKey: queryKeys.nodeDetail(topicId, nodeId),
    queryFn: () => getNodeDetail(topicId, nodeId),
    enabled: !!topicId && !!nodeId,
    ..._AI_QUERY,
  })

export const useNodeAbilityQuery = (topicId: string, nodeId: string) =>
  useQuery({
    queryKey: queryKeys.nodeAbility(topicId, nodeId),
    queryFn: () => getNodeAbility(topicId, nodeId),
    enabled: !!topicId && !!nodeId,
  })

// ---- Graph ----
export const useGraphQuery = (topicId: string, params?: { view?: GraphView; max_depth?: number; focus_node_id?: string }) =>
  useQuery({
    queryKey: queryKeys.graph(topicId, params),
    queryFn: () => getGraph(topicId, params),
    enabled: !!topicId,
  })

export const useMainlineQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.graphMainline(topicId),
    queryFn: () => getMainline(topicId),
    enabled: !!topicId,
  })

export const useNeighborhoodQuery = (topicId: string, nodeId: string, params?: { radius?: number; relation_types?: string[] }) =>
  useQuery({
    queryKey: queryKeys.nodeNeighborhood(topicId, nodeId, params),
    queryFn: () => getNeighborhood(topicId, nodeId, params),
    enabled: !!topicId && !!nodeId,
  })

// ---- Sessions ----
export const useSessionQuery = (topicId: string, sessionId: string) =>
  useQuery({
    queryKey: queryKeys.session(topicId, sessionId),
    queryFn: () => getSession(topicId, sessionId),
    enabled: !!topicId && !!sessionId,
  })

// ---- Expression Assets ----
export const useExpressionAssetsQuery = (topicId: string, params?: { node_id?: string; favorited?: boolean; limit?: number; expression_type?: PracticeType }) =>
  useQuery({
    queryKey: queryKeys.expressionAssets(topicId, params),
    queryFn: () => getExpressionAssets(topicId, params),
    enabled: !!topicId,
  })

// ---- Ability / Diagnostics ----
export const useAbilityOverviewQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.abilitiesOverview(topicId),
    queryFn: () => getAbilityOverview(topicId),
    enabled: !!topicId,
    ..._AI_QUERY,
  })

export const useFrictionsQuery = (topicId: string, params?: { node_id?: string; limit?: number }) =>
  useQuery({
    queryKey: queryKeys.frictions(topicId, params),
    queryFn: () => getFrictions(topicId, params),
    enabled: !!topicId,
  })

// ---- Reviews ----
export const useReviewListQuery = (params?: { status?: string; limit?: number; topic_id?: string }) =>
  useQuery({
    queryKey: queryKeys.reviews(params),
    queryFn: () => getReviews(params),
  })

export const useReviewDetailQuery = (reviewId: string) =>
  useQuery({
    queryKey: queryKeys.review(reviewId),
    queryFn: () => getReviewDetail(reviewId),
    enabled: !!reviewId,
  })

// ---- Settings ----
export const useSettingsQuery = () =>
  useQuery({
    queryKey: queryKeys.settings,
    queryFn: getSettings,
    staleTime: 5 * 60_000,
  })

// ---- Health ----
export const useHealthQuery = () =>
  useQuery({
    queryKey: queryKeys.health,
    queryFn: getHealth,
    staleTime: 30_000,
    retry: false,
  })

// ---- System Capabilities ----
export const useSystemCapabilitiesQuery = () =>
  useQuery({
    queryKey: queryKeys.systemCapabilities,
    queryFn: getSystemCapabilities,
    staleTime: 60_000,
    retry: false,
  })


// ---- Deferred Nodes ----
export function useDeferredNodesQuery(topicId: string | null) {
  return useQuery({
    queryKey: queryKeys.deferredNodes(topicId!),
    queryFn: () => getDeferredNodes(topicId!),
    enabled: !!topicId,
    staleTime: 2 * 60_000,
  })
}

// ---- Practice Attempts ----
export function usePracticeAttemptsQuery(topicId: string | null, params?: { node_id?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.practiceAttempts(topicId!, params),
    queryFn: () => getPracticeAttempts(topicId!, params),
    enabled: !!topicId,
    staleTime: 60_000,
  })
}

// ---- Recommended Practice Type ----
export function useRecommendedPracticeQuery(topicId: string | null, nodeId: string | null) {
  return useQuery({
    queryKey: queryKeys.recommendedPractice(topicId!, nodeId!),
    queryFn: () => getRecommendedPracticeType(topicId!, nodeId!),
    enabled: !!topicId && !!nodeId,
    staleTime: 2 * 60_000,
  })
}

// ---- Concept Summary (lightweight, for popup) ----
export function useConceptSummaryQuery(topicId: string | null, nodeId: string | null) {
  return useQuery({
    queryKey: queryKeys.conceptSummary(topicId!, nodeId!),
    queryFn: () => getNodeDetail(topicId!, nodeId!),
    enabled: !!topicId && !!nodeId,
    staleTime: 5 * 60_000,
    select: (data) => ({
      node_id: data.node.node_id,
      name: data.node.name,
      summary: data.node.summary,
    }),
  })
}

// ---- Session Summary (for summary page API fallback) ----
export interface SessionSummaryFallback extends Omit<CompleteSessionResponse, 'synthesis'> {
  synthesis?: Partial<CompleteSessionResponse['synthesis']>
  partial_summary?: boolean
}

export function useSessionSummaryQuery(topicId: string, sessionId: string | null) {
  return useQuery<Session, Error, SessionSummaryFallback>({
    queryKey: queryKeys.sessionSummary(topicId, sessionId!),
    queryFn: () => getSession(topicId, sessionId!),
    enabled: !!topicId && !!sessionId,
    staleTime: 5 * 60_000,
    select: (data) => {
      // If synthesis was already parsed by backend, use it directly
      if (data.synthesis) {
        return {
          ...data,
          session_id: data.session_id,
          topic_id: data.topic_id,
          status: data.status,
          summary: data.summary || '本轮学习已完成',
          partial_summary: false,
          synthesis: data.synthesis,
        }
      }
      // Try parsing synthesis_json from local fallback
      if (data.synthesis_json) {
        try {
          const synthesis = JSON.parse(data.synthesis_json)
          return {
            ...data,
            session_id: data.session_id,
            topic_id: data.topic_id,
            status: data.status,
            summary: data.summary || '本轮学习已完成',
            partial_summary: !synthesis.mainline_summary,
            synthesis,
          }
        } catch {
          // JSON parse failed, show partial
        }
      }
      // No synthesis data at all — show partial fallback
      return {
        ...data,
        session_id: data.session_id,
        topic_id: data.topic_id,
        status: data.status,
        summary: data.summary || '本轮学习已完成',
        partial_summary: true as const,
        synthesis: undefined,
      }
    },
  })
}

// ---- Stats ----
export const useGlobalStatsQuery = () =>
  useQuery({
    queryKey: queryKeys.globalStats,
    queryFn: () => getGlobalStats(),
    staleTime: 30_000,
  })

export const useTopicStatsQuery = (topicId: string) =>
  useQuery({
    queryKey: queryKeys.topicStats(topicId),
    queryFn: () => getTopicStats(topicId),
    enabled: !!topicId,
    staleTime: 30_000,
  })

export const useAbilitySnapshotsQuery = (topicId: string | null) =>
  useQuery({
    queryKey: queryKeys.abilitySnapshots(topicId!),
    queryFn: () => getAbilitySnapshots(topicId!, 50),
    enabled: !!topicId,
    staleTime: 60_000,
  })
