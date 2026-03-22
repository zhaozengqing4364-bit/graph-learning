import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createTopic,
  createConceptCandidate,
  createSourceArticle,
  updateTopic,
  updateSourceArticle,
  archiveTopic,
  deleteTopic,
  expandNode,
  deferNode,
  updateNodeStatus,
  startSession,
  visitNode,
  completeSession,
  getPracticePrompt,
  submitPractice,
  saveExpressionAsset,
  toggleExpressionFavorite,
  generateReviewQueue,
  submitReview,
  skipReview,
  snoozeReview,
  updateSettings,
  diagnoseNode,
  exportTopic,
  generateArticle,
  ignoreConceptCandidate,
  saveReadingState,
  confirmConceptCandidate,
  upsertConceptNote,
} from '../services'
import type {
  ConceptNoteRecord,
  CreateTopicRequest,
  ExpandNodeRequest,
  DeferNodeRequest,
  NodeStatus,
  StartSessionRequest,
  VisitNodeRequest,
  CompleteSessionRequest,
  PracticeRequest,
  PracticeSubmitRequest,
  SaveExpressionAssetRequest,
  ReviewSubmitRequest,
  UpdateSettingsRequest,
  WorkspaceBundle,
} from '../types'
import { showToast } from '../components/ui/toast'
import { ApiError } from '../services/api-client'
import { queryKeys } from '../lib/query-keys'

// Error codes that should show a warning (recoverable) instead of error (fatal)
const _WARNING_CODES = new Set([
  'RATE_LIMITED', 'AI_UNAVAILABLE', 'TOPIC_CAP_REACHED',
  'EXPORT_EMPTY', 'NODE_NOT_FOUND', 'REVIEW_NOT_FOUND',
])

/** Unified mutation error handler — routes by error code severity. */
function _onError(err: unknown): void {
  if (err instanceof ApiError) {
    const type = _WARNING_CODES.has(err.code) ? 'warning' : 'error'
    showToast(err.message || '操作失败，请重试', type)
    return
  }
  if (err instanceof Error) {
    // Network-level errors already carry a user-friendly message from api-client.ts
    showToast(err.message, 'error')
    return
  }
  showToast('操作失败，请重试', 'error')
}

// ---- Topics ----
export const useCreateTopicMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateTopicRequest) => createTopic(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.topics() }),
    onError: _onError,
  })
}

export const useUpdateTopicMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<CreateTopicRequest & { status: string }>) => updateTopic(topicId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topics() })
      qc.invalidateQueries({ queryKey: queryKeys.topic(topicId) })
    },
    onError: _onError,
  })
}

export const useArchiveTopicMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (topicId: string) => archiveTopic(topicId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topics() })
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
    },
    onError: _onError,
  })
}

export const useDeleteTopicMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (topicId: string) => deleteTopic(topicId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topics() })
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
    },
    onError: _onError,
  })
}

// ---- Article Workspace ----
export const useCreateSourceArticleMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { title: string; body: string }) => createSourceArticle(topicId, body),
    onSuccess: (result) => {
      qc.setQueryData<WorkspaceBundle | undefined>(queryKeys.topicWorkspace(topicId), (current) => (
        current
          ? {
              ...current,
              source_articles: [result.article, ...current.source_articles.filter((item) => item.article_id !== result.article.article_id)],
            }
          : current
      ))
      qc.setQueryData(queryKeys.topicArticles(topicId), (current: Array<{ article_id: string }> | undefined) => (
        current
          ? [result.article, ...current.filter((item) => item.article_id !== result.article.article_id)]
          : [result.article]
      ))
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
    },
    onError: _onError,
  })
}

export const useUpdateSourceArticleMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ articleId, body }: { articleId: string; body: { title?: string; body?: string } }) =>
      updateSourceArticle(topicId, articleId, body),
    onSuccess: (result) => {
      qc.setQueryData<WorkspaceBundle | undefined>(queryKeys.topicWorkspace(topicId), (current) => (
        current
          ? {
              ...current,
              source_articles: current.source_articles.map((item) => (
                item.article_id === result.article.article_id ? result.article : item
              )),
            }
          : current
      ))
      qc.setQueryData(queryKeys.topicArticles(topicId), (current: Array<{ article_id: string }> | undefined) => (
        current?.map((item) => (
          item.article_id === result.article.article_id ? result.article : item
        ))
      ))
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.graph(topicId) })
    },
    onError: _onError,
  })
}

export const useUpsertConceptNoteMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ conceptKey, body }: { conceptKey: string; body: { title: string; body: string } }) =>
      upsertConceptNote(topicId, conceptKey, body),
    onSuccess: (note) => {
      qc.setQueryData<WorkspaceBundle | undefined>(queryKeys.topicWorkspace(topicId), (current) => {
        if (!current) {
          return current
        }

        const others = current.concept_notes.filter((item) => item.concept_key !== note.concept_key)
        return {
          ...current,
          concept_notes: [note, ...others],
        }
      })
      qc.setQueryData<ConceptNoteRecord | null>(queryKeys.topicConceptNote(topicId, note.concept_key), note)
    },
    onError: _onError,
  })
}

export const useSaveReadingStateMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      article_id: string
      scroll_top: number
      trail: Array<{ article_id: string; title: string }>
      completed_article_ids: string[]
    }) => saveReadingState(topicId, body),
    onSuccess: (readingState) => {
      qc.setQueryData(queryKeys.topicReadingState(topicId), readingState)
      qc.setQueryData<WorkspaceBundle | undefined>(queryKeys.topicWorkspace(topicId), (current) => (
        current
          ? {
              ...current,
              reading_state: readingState,
            }
          : current
      ))
    },
    onError: _onError,
  })
}

export const useCreateConceptCandidateMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      concept_text: string
      source_article_id?: string
      paragraph_index?: number
      anchor_id?: string
      origin?: 'manual' | 'article_analysis'
    }) => createConceptCandidate(topicId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.topicConceptCandidates(topicId) })
    },
    onError: _onError,
  })
}

export const useConfirmConceptCandidateMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ candidateId, body }: { candidateId: string; body?: { concept_name?: string } }) =>
      confirmConceptCandidate(topicId, candidateId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.topicConceptCandidates(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.graph(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.graphMainline(topicId) })
    },
    onError: _onError,
  })
}

export const useIgnoreConceptCandidateMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (candidateId: string) => ignoreConceptCandidate(topicId, candidateId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.topicConceptCandidates(topicId) })
    },
    onError: _onError,
  })
}

// ---- Nodes ----
export const useExpandNodeMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ExpandNodeRequest) => expandNode(topicId, nodeId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.graph(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.graphMainline(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.topic(topicId) })
    },
    onError: _onError,
  })
}

export const useDeferNodeMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DeferNodeRequest) => deferNode(topicId, nodeId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topic(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.graph(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.deferredNodes(topicId) })
    },
    onError: _onError,
  })
}

export const useUpdateNodeStatusMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (status: NodeStatus) => updateNodeStatus(topicId, nodeId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.nodeDetail(topicId, nodeId) })
      qc.invalidateQueries({ queryKey: queryKeys.graph(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.abilitiesOverview(topicId) })
    },
    onError: _onError,
  })
}

// ---- Sessions ----
export const useStartSessionMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: StartSessionRequest) => startSession(topicId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topic(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
    },
    onError: _onError,
  })
}

export const useVisitNodeMutation = (topicId: string, sessionId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: VisitNodeRequest) => visitNode(topicId, sessionId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topic(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
    },
    onError: _onError,
  })
}

export const useCompleteSessionMutation = (topicId: string, sessionId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CompleteSessionRequest) => completeSession(topicId, sessionId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topic(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.sessionSummary(topicId, sessionId) })
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
    },
    onError: _onError,
  })
}

// ---- Practice ----
export const useGetPracticePromptMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PracticeRequest) => getPracticePrompt(topicId, nodeId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.recommendedPractice(topicId, nodeId) })
    },
    onError: _onError,
  })
}

export const useSubmitPracticeMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PracticeSubmitRequest) => submitPractice(topicId, nodeId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.nodeDetail(topicId, nodeId) })
      qc.invalidateQueries({ queryKey: queryKeys.nodeAbility(topicId, nodeId) })
      qc.invalidateQueries({ queryKey: queryKeys.abilitiesOverview(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.frictions(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.abilitySnapshots(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
      qc.invalidateQueries({ queryKey: queryKeys.practiceAttempts(topicId) })
    },
    onError: _onError,
  })
}

export const useSaveExpressionAssetMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SaveExpressionAssetRequest) => saveExpressionAsset(topicId, nodeId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.expressionAssets(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
    },
    onError: _onError,
  })
}

export const useToggleFavoriteMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (assetId: string) => toggleExpressionFavorite(assetId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.expressionAssets(topicId) })
    },
    onError: _onError,
  })
}

// ---- Review ----
export const useGenerateReviewQueueMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => generateReviewQueue(topicId),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.reviews() }),
    onError: _onError,
  })
}

export const useSubmitReviewMutation = (reviewId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReviewSubmitRequest) => submitReview(reviewId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
      qc.invalidateQueries({ queryKey: queryKeys.review(reviewId) })
      qc.invalidateQueries({ queryKey: ['topic'] as const })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
    },
    onError: _onError,
  })
}

export const useSkipReviewMutation = (reviewId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => skipReview(reviewId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
      qc.invalidateQueries({ queryKey: queryKeys.review(reviewId) })
      qc.invalidateQueries({ queryKey: ['topic'] as const })
    },
    onError: _onError,
  })
}

export const useSnoozeReviewMutation = (reviewId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => snoozeReview(reviewId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
      qc.invalidateQueries({ queryKey: queryKeys.review(reviewId) })
      qc.invalidateQueries({ queryKey: ['topic'] as const })
    },
    onError: _onError,
  })
}

// ---- Settings ----
export const useUpdateSettingsMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: UpdateSettingsRequest) => updateSettings(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.settings }),
    onError: _onError,
  })
}

// ---- Article Generation ----
export const useGenerateArticleMutation = (topicId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ nodeId, force }: { nodeId: string; force?: boolean }) =>
      generateArticle(topicId, nodeId, { force }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.topicWorkspace(topicId) })
      qc.invalidateQueries({ queryKey: queryKeys.graph(topicId) })
    },
    onError: _onError,
  })
}

// ---- Diagnostics ----
export const useDiagnoseNodeMutation = (topicId: string, nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => diagnoseNode(topicId, nodeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.nodeDetail(topicId, nodeId) })
      qc.invalidateQueries({ queryKey: queryKeys.globalStats })
    },
    onError: _onError,
  })
}

// ---- Export ----
export const useExportTopicMutation = (topicId: string) =>
  useMutation({
    mutationFn: (body: { export_type: 'markdown' | 'json' | 'anki' }) => exportTopic(topicId, body),
    onError: _onError,
  })
