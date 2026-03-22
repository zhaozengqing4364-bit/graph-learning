import { apiDelete, apiGet, apiPatch, apiPost, apiPostLong, apiPut } from './api-client'
import type {
  ConceptCandidateOrigin,
  ConceptCandidateRecord,
  ConceptNoteRecord,
  Topic,
  CreateTopicRequest,
  CreateTopicResponse,
  NodeDetail,
  ExpandNodeRequest,
  ExpandNodeResponse,
  DeferNodeRequest,
  EntryNode,
  NodeStatus,
  StartSessionRequest,
  StartSessionResponse,
  Session,
  VisitNodeRequest,
  CompleteSessionRequest,
  CompleteSessionResponse,
  PracticeRequest,
  PracticePrompt,
  PracticeSubmitRequest,
  PracticeFeedback,
  SaveExpressionAssetRequest,
  ExpressionAsset,
  AbilityRecord,
  AbilityOverview,
  AbilitySnapshot,
  FrictionRecord,
  ReviewItem,
  ReviewSubmitRequest,
  ReviewSubmitResponse,
  GraphData,
  GraphView,
  Settings,
  UpdateSettingsRequest,
  HealthStatus,
  SystemCapabilities,
  DiagnoseResponse,
  PracticeType,
  ReadingStateRecord,
  SourceArticleMutationResult,
  SourceArticleRecord,
  WorkspaceBacklink,
  WorkspaceBundle,
  WorkspaceSearchResult,
} from '../types'

// ---- Health ----
export const getHealth = () => apiGet<HealthStatus>('/system/health')

// ---- System Capabilities ----
export const getSystemCapabilities = () => apiGet<SystemCapabilities>('/system/capabilities')

// ---- Topics ----
export const getTopics = (params?: { status?: string; limit?: number; offset?: number; q?: string }) =>
  apiGet<Topic[]>('/topics', params as Record<string, unknown>)

export const getTopic = (topicId: string) => apiGet<Topic>(`/topics/${topicId}`)

export const createTopic = (body: CreateTopicRequest) => apiPostLong<CreateTopicResponse>('/topics', body)

export const updateTopic = (topicId: string, body: Partial<CreateTopicRequest & { status: string }>) =>
  apiPatch<Topic>(`/topics/${topicId}`, body)

export const archiveTopic = (topicId: string) => apiPost<void>(`/topics/${topicId}/archive`)

export const deleteTopic = (topicId: string) => apiDelete<void>(`/topics/${topicId}`)

export const getEntryNode = (topicId: string) => apiGet<EntryNode>(`/topics/${topicId}/entry-node`)

export const getDeferredNodes = (topicId: string) =>
  apiGet<Array<{ topic_id: string; node_id: string; node_name?: string; reason: string }>>(`/topics/${topicId}/deferred`)

export const getPracticeAttempts = (topicId: string, params?: { node_id?: string; limit?: number }) =>
  apiGet<Array<{ attempt_id: string; practice_type: PracticeType; node_id: string; node_name?: string; user_answer?: string; created_at: string }>>(`/topics/${topicId}/practice-attempts`, params as Record<string, unknown>)

export const getRecommendedPracticeType = (topicId: string, nodeId: string) =>
  apiGet<{ recommended_type: PracticeType; reason: string }>(`/topics/${topicId}/nodes/${nodeId}/recommended-practice`)

// ---- Article Workspace ----
export const getWorkspaceBundle = (topicId: string) =>
  apiGet<WorkspaceBundle>(`/topics/${topicId}/workspace`)

export const getSourceArticles = (topicId: string) =>
  apiGet<SourceArticleRecord[]>(`/topics/${topicId}/articles`)

export const getSourceArticle = (topicId: string, articleId: string) =>
  apiGet<SourceArticleRecord>(`/topics/${topicId}/articles/${articleId}`)

export const createSourceArticle = (topicId: string, body: { title: string; body: string }) =>
  apiPost<SourceArticleMutationResult>(`/topics/${topicId}/articles`, body)

export const updateSourceArticle = (topicId: string, articleId: string, body: { title?: string; body?: string }) =>
  apiPatch<SourceArticleMutationResult>(`/topics/${topicId}/articles/${articleId}`, body)

export const getConceptNote = (topicId: string, conceptKey: string) =>
  apiGet<ConceptNoteRecord | null>(`/topics/${topicId}/concept-notes/${conceptKey}`)

export const upsertConceptNote = (topicId: string, conceptKey: string, body: { title: string; body: string }) =>
  apiPut<ConceptNoteRecord>(`/topics/${topicId}/concept-notes/${conceptKey}`, body)

export const getReadingState = (topicId: string) =>
  apiGet<ReadingStateRecord | null>(`/topics/${topicId}/reading-state`)

export const saveReadingState = (topicId: string, body: {
  article_id: string
  scroll_top: number
  trail: Array<{ article_id: string; title: string }>
  completed_article_ids: string[]
}) => apiPut<ReadingStateRecord>(`/topics/${topicId}/reading-state`, body)

export const getConceptCandidates = (topicId: string, params?: { status?: string }) =>
  apiGet<ConceptCandidateRecord[]>(`/topics/${topicId}/concept-candidates`, params as Record<string, unknown>)

export const createConceptCandidate = (topicId: string, body: {
  concept_text: string
  source_article_id?: string
  paragraph_index?: number
  anchor_id?: string
  origin?: ConceptCandidateOrigin
}) => apiPost<ConceptCandidateRecord>(`/topics/${topicId}/concept-candidates`, body)

export const confirmConceptCandidate = (topicId: string, candidateId: string, body?: { concept_name?: string }) =>
  apiPost<ConceptCandidateRecord>(`/topics/${topicId}/concept-candidates/${candidateId}/confirm`, body || {})

export const ignoreConceptCandidate = (topicId: string, candidateId: string) =>
  apiPost<ConceptCandidateRecord>(`/topics/${topicId}/concept-candidates/${candidateId}/ignore`, {})

export const searchWorkspace = (topicId: string, params: { q: string }) =>
  apiGet<WorkspaceSearchResult>(`/topics/${topicId}/workspace-search`, params as Record<string, unknown>)

export const getArticleBacklinks = (topicId: string, nodeId: string) =>
  apiGet<WorkspaceBacklink[]>(`/topics/${topicId}/nodes/${nodeId}/backlinks`)

// ---- Nodes ----
export const getNodeDetail = (topicId: string, nodeId: string) => apiGet<NodeDetail>(`/topics/${topicId}/nodes/${nodeId}`)

export const expandNode = (topicId: string, nodeId: string, body: ExpandNodeRequest) =>
  apiPostLong<ExpandNodeResponse>(`/topics/${topicId}/nodes/${nodeId}/expand`, body)

export const deferNode = (topicId: string, nodeId: string, body: DeferNodeRequest) =>
  apiPost<void>(`/topics/${topicId}/nodes/${nodeId}/defer`, body)

export const updateNodeStatus = (topicId: string, nodeId: string, status: NodeStatus) =>
  apiPatch<void>(`/topics/${topicId}/nodes/${nodeId}/status`, { status })

export const generateArticle = (topicId: string, nodeId: string, params?: { force?: boolean }) =>
  apiPost<{ article_body: string; concept_refs: string[] }>(
    `/topics/${topicId}/nodes/${nodeId}/generate-article`,
    undefined,
    params as Record<string, unknown> | undefined,
  )

// ---- Graph ----
export const getGraph = (topicId: string, params?: { view?: GraphView; max_depth?: number; focus_node_id?: string; collapsed?: boolean }) =>
  apiGet<GraphData>(`/topics/${topicId}/graph`, params as Record<string, unknown>)

export const getMainline = (topicId: string) => apiGet<GraphData>(`/topics/${topicId}/graph/mainline`)

export const getNeighborhood = (topicId: string, nodeId: string, params?: { radius?: number; relation_types?: string[] }) =>
  apiGet<GraphData>(`/topics/${topicId}/graph/neighborhood/${nodeId}`, params as Record<string, unknown>)

// ---- Sessions ----
export const startSession = (topicId: string, body: StartSessionRequest) =>
  apiPost<StartSessionResponse>(`/topics/${topicId}/sessions`, body)

export const getSession = (topicId: string, sessionId: string) => apiGet<Session>(`/topics/${topicId}/sessions/${sessionId}`)

export const visitNode = (topicId: string, sessionId: string, body: VisitNodeRequest) =>
  apiPost<void>(`/topics/${topicId}/sessions/${sessionId}/visit`, body)

export const completeSession = (topicId: string, sessionId: string, body: CompleteSessionRequest) =>
  apiPost<CompleteSessionResponse>(`/topics/${topicId}/sessions/${sessionId}/complete`, body)

// ---- Practice ----
export const getPracticePrompt = (topicId: string, nodeId: string, body: PracticeRequest) =>
  apiPostLong<PracticePrompt>(`/topics/${topicId}/nodes/${nodeId}/practice`, body)

export const submitPractice = (topicId: string, nodeId: string, body: PracticeSubmitRequest) =>
  apiPostLong<PracticeFeedback>(`/topics/${topicId}/nodes/${nodeId}/practice/submit`, body)

export const saveExpressionAsset = (topicId: string, nodeId: string, body: SaveExpressionAssetRequest) =>
  apiPost<ExpressionAsset>(`/topics/${topicId}/nodes/${nodeId}/expression-assets`, body)

export const getExpressionAssets = (topicId: string, params?: { node_id?: string; expression_type?: PracticeType; favorited?: boolean; limit?: number }) =>
  apiGet<ExpressionAsset[]>(`/topics/${topicId}/expression-assets`, params as Record<string, unknown>)

export const toggleExpressionFavorite = (assetId: string) =>
  apiPost<ExpressionAsset>(`/expression-assets/${assetId}/toggle-favorite`)

// ---- Ability / Diagnostics ----
export const getNodeAbility = (topicId: string, nodeId: string) =>
  apiGet<AbilityRecord>(`/topics/${topicId}/nodes/${nodeId}/ability`)

export const getAbilityOverview = (topicId: string) =>
  apiGet<AbilityOverview>(`/topics/${topicId}/abilities/overview`)

export const getFrictions = (topicId: string, params?: { node_id?: string; friction_type?: string; limit?: number }) =>
  apiGet<FrictionRecord[]>(`/topics/${topicId}/frictions`, params as Record<string, unknown>)

export const getAbilitySnapshots = (topicId: string, limit: number = 50) =>
  apiGet<AbilitySnapshot[]>(`/topics/${topicId}/abilities/snapshots`, { limit })

export const diagnoseNode = (topicId: string, nodeId: string, body?: { practice_type?: string; user_answer?: string }) =>
  apiPostLong<DiagnoseResponse>(`/topics/${topicId}/nodes/${nodeId}/diagnose`, body || { practice_type: 'explain', user_answer: '' })

// ---- Review ----
export const getReviews = (params?: { status?: string; limit?: number; topic_id?: string; due_before?: string }) =>
  apiGet<ReviewItem[]>('/reviews', params as Record<string, unknown>)

export const getReviewDetail = (reviewId: string) =>
  apiGet<ReviewItem>(`/reviews/${reviewId}`)

export const submitReview = (reviewId: string, body: ReviewSubmitRequest) =>
  apiPost<ReviewSubmitResponse>(`/reviews/${reviewId}/submit`, body)

export const skipReview = (reviewId: string) =>
  apiPost<void>(`/reviews/${reviewId}/skip`)

export const snoozeReview = (reviewId: string) =>
  apiPost<void>(`/reviews/${reviewId}/snooze`)

export const generateReviewQueue = (topicId: string) =>
  apiPostLong<void>(`/topics/${topicId}/reviews/generate`)

// ---- Export ----
export interface ExportRequest {
  export_type: 'markdown' | 'json' | 'anki'
}

export interface ExportResponse {
  content: string
  format: string
  filename: string
}

export const exportTopic = (topicId: string, body: ExportRequest) =>
  apiPost<ExportResponse>(`/topics/${topicId}/export`, body)

export const exportData = (topicId: string, format: ExportRequest['export_type'] = 'markdown') =>
  exportTopic(topicId, { export_type: format })

// ---- Settings ----
export const getSettings = () => apiGet<Settings>('/settings')

export const updateSettings = (body: UpdateSettingsRequest) => apiPatch<Settings>('/settings', body)

// ---- Stats ----
export const getGlobalStats = () => apiGet<Record<string, number>>('/stats')

export const getTopicStats = (topicId: string) => apiGet(`/stats/topics/${topicId}`)
