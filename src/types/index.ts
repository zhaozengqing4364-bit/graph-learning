// ========================
// AxonClone unified type definitions
// All snake_case, aligned with backend Pydantic models
// ========================

// --- Common ---
export interface ApiResponse<T> {
  success: boolean
  data: T
  meta: ApiMeta
  error: ApiError | null
}

export interface ApiMeta {
  request_id?: string
  timestamp?: string
  version?: string
  fallback_used?: boolean
  partial?: boolean
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}

// --- Enums ---
export type SourceType = 'concept' | 'question' | 'article' | 'notes' | 'mixed'
export type LearningIntent = 'build_system' | 'fix_gap' | 'solve_task' | 'prepare_expression' | 'prepare_interview'
export type TopicMode = 'shortest_path' | 'full_system'
export type TopicStatus = 'active' | 'archived' | 'completed'
export type NodeStatus = 'unseen' | 'browsed' | 'learning' | 'practiced' | 'review_due' | 'mastered'
export type EdgeType = 'PREREQUISITE' | 'CONTRASTS' | 'VARIANT_OF' | 'APPLIES_IN' | 'EXTENDS' | 'MISUNDERSTOOD_AS' | 'EVIDENCED_BY'
export type SessionStatus = 'active' | 'completed' | 'abandoned'
export type PracticeType = 'define' | 'example' | 'contrast' | 'apply' | 'teach_beginner' | 'compress'
export type ReviewStatus = 'pending' | 'completed' | 'overdue' | 'due' | 'skipped' | 'failed' | 'snoozed' | 'cancelled'
export type GraphView = 'mainline' | 'full' | 'prerequisite' | 'misconception'
export type ExpandStrategy = 'mainline_first' | 'balanced' | 'deep_dive'
export type FeedbackLevel = 'good' | 'medium' | 'weak'

// --- Topic ---
export interface Topic {
  topic_id: string
  title: string
  source_type: SourceType
  source_content?: string
  learning_intent: LearningIntent
  mode: TopicMode
  status: TopicStatus
  current_node_id?: string
  entry_node_id?: string
  last_session_id?: string
  total_nodes: number
  learned_nodes: number
  due_review_count: number
  deferred_count: number
  created_at: string
  updated_at: string
}

export interface TopicOutline {
  mainline: string[]
  suggested_nodes: number
}

export interface CreateTopicRequest {
  title: string
  source_type: SourceType
  source_content: string
  learning_intent: LearningIntent
  mode: TopicMode
}

export interface CreateTopicResponse {
  topic_id: string
  title: string
  entry_node_id: string
  total_nodes: number
  fallback_used: boolean
  [key: string]: unknown
}

export interface EntryNode {
  node_id: string
  name: string
  summary: string
}

// --- Article Workspace ---
export type ConceptCandidateStatus = 'candidate' | 'confirmed' | 'ignored'
export type ConceptCandidateOrigin = 'manual' | 'article_analysis'

export interface SourceArticleRecord {
  article_id: string
  topic_id: string
  title: string
  body: string
  article_kind?: 'source'
  source_label?: string
  is_editable?: boolean
  created_at: string
  updated_at: string
}

export interface SourceArticleMutationResult {
  article: SourceArticleRecord
  analysis: {
    mention_count: number
    candidate_count: number
    candidate_ids: string[]
    valid_links: string[]
    invalid_links: string[]
    added_mentions: number
    removed_mentions: number
  }
}

export interface ConceptNoteRecord {
  note_id: string
  topic_id: string
  concept_key: string
  title: string
  body: string
  updated_at: string
}

export interface ReadingTrailEntry {
  article_id: string
  title: string
}

export interface ReadingStateRecord {
  topic_id?: string
  article_id: string
  scroll_top: number
  trail: ReadingTrailEntry[]
  updated_at: string
  completed_article_ids?: string[]
}

export interface ConceptCandidateRecord {
  candidate_id: string
  topic_id: string
  concept_text: string
  normalized_text: string
  status: ConceptCandidateStatus
  matched_node_id?: string | null
  matched_concept_name: string
  source_article_id?: string | null
  paragraph_index?: number | null
  anchor_id: string
  origin: ConceptCandidateOrigin
  confidence: number
  created_at: string
  updated_at: string
}

export interface WorkspaceBundle {
  source_articles: SourceArticleRecord[]
  concept_notes: ConceptNoteRecord[]
  reading_state: ReadingStateRecord | null
  concept_candidates: ConceptCandidateRecord[]
}

export interface WorkspaceSearchResult {
  articles: Array<Pick<SourceArticleRecord, 'article_id' | 'title' | 'body' | 'updated_at'>>
  concepts: RelatedNode[]
  notes: Array<Pick<ConceptNoteRecord, 'concept_key' | 'title' | 'body' | 'updated_at'>>
}

export interface WorkspaceBacklink {
  article_id: string
  title: string
  anchor_id: string
  snippet: string
  updated_at?: string
}

// --- Node ---
export interface Node {
  node_id: string
  name: string
  summary: string
  why_it_matters?: string
  article_body?: string
  importance: number
  status: NodeStatus
  topic_id: string
  confidence?: number
  depth?: number
  is_mainline?: boolean
  created_at: string
  updated_at: string
}

export interface DynamicMisconception {
  description: string
  correction: string
  severity: number
}

export interface NodeDetail {
  node: Node
  examples: string[]
  misconceptions: string[]
  dynamic_misconceptions?: DynamicMisconception[]
  concept_refs?: string[]
  prerequisites: RelatedNode[]
  contrasts: RelatedNode[]
  applications: RelatedNode[]
  misunderstandings: RelatedNode[]
  related: RelatedNode[]
  ability: AbilityRecord
  why_now?: string
}

export interface RelatedNode {
  node_id: string
  name: string
  summary?: string
}

export interface ExpandNodeRequest {
  depth_limit?: number
  intent?: LearningIntent
  strategy?: ExpandStrategy
}

export interface ExpandNodeResponse {
  new_nodes: Node[]
  new_edges: Edge[]
  suggested_next_nodes: EntryNode[]
  summary_delta?: string
}

export interface DeferNodeRequest {
  source_node_id: string
  reason: string
}

// --- Edge ---
export interface Edge {
  edge_id: string
  source_node_id: string
  target_node_id: string
  relation_type: EdgeType
  topic_id: string
}

// --- Ability ---
export interface AbilityRecord {
  understand: number
  example: number
  contrast: number
  apply: number
  explain: number
  recall: number
  transfer: number
  teach: number
}

export type AbilityDimension = keyof AbilityRecord

export const ABILITY_DIMENSIONS: { key: AbilityDimension; label: string }[] = [
  { key: 'understand', label: '理解' },
  { key: 'example', label: '举例' },
  { key: 'contrast', label: '对比' },
  { key: 'apply', label: '应用' },
  { key: 'explain', label: '解释' },
  { key: 'recall', label: '回忆' },
  { key: 'transfer', label: '迁移' },
  { key: 'teach', label: '教学' },
]

export const ABILITY_AVG = (a: AbilityRecord | null) =>
  a ? ABILITY_DIMENSIONS.reduce((sum, d) => sum + (a[d.key] || 0), 0) / ABILITY_DIMENSIONS.length : 0

// --- Ability Snapshot ---
export interface AbilitySnapshot {
  id: number
  topic_id: string
  node_id: string | null
  session_id: string | null
  understand: number
  example: number
  contrast: number
  apply: number
  explain: number
  recall: number
  transfer: number
  teach: number
  source: string
  created_at: string
}

// --- Session ---
export interface Session {
  session_id: string
  topic_id: string
  entry_node_id: string
  status: SessionStatus
  visited_node_ids: string[]
  practice_count: number
  summary?: string
  synthesis_json?: string
  synthesis?: CompleteSessionResponse['synthesis']
  started_at: string
  completed_at?: string
  restored?: boolean
  created_at: string
  updated_at: string
}

export interface StartSessionRequest {
  entry_node_id: string
}

export interface StartSessionResponse {
  session_id: string
  topic_id: string
  entry_node_id: string
  status: string
  restored: boolean
  [key: string]: unknown
}

export interface VisitNodeRequest {
  node_id: string
  action_type: string
}

export interface CompleteSessionRequest {
  generate_summary?: boolean
  generate_review_items?: boolean
}

export interface CompleteSessionResponse {
  session_id: string
  topic_id: string
  status: string
  summary: string
  synthesis: {
    mainline_summary: string
    key_takeaways: string[]
    next_recommendations: { node_id: string; name: string; summary: string }[]
    review_items_created: number
    new_assets_count: number
    covered_scope: string
    skippable_nodes: string[]
    review_candidates: { node_id?: string; node_name?: string; name?: string; summary?: string; reason?: string; review_id?: string }[]
    asset_highlights: { node_id: string; practice_type: string; correctness: number }[]
  }
}

// --- Practice ---
export interface PracticeRequest {
  practice_type: PracticeType
  difficulty?: string
  regenerate?: boolean
}

export interface PracticePrompt {
  practice_type: PracticeType
  prompt_text: string
  minimum_answer_hint: string
  evaluation_dimensions: string[]
  cached?: boolean
}

export interface PracticeSubmitRequest {
  session_id?: string
  practice_type: PracticeType
  prompt_text: string
  user_answer: string
}

export interface PracticeFeedback {
  attempt_id: string
  feedback: FeedbackDetail
  recommended_answer: string
  expression_skeleton: string
  ability_update: Partial<AbilityRecord>
  friction_tags: string[]
  diagnosis_fallback?: boolean
}

export interface FeedbackDetail {
  correctness: FeedbackLevel
  clarity: FeedbackLevel
  naturalness: FeedbackLevel
  issues: string[]
  suggestions: string[]
}

export type PracticeState = 'idle' | 'loading_prompt' | 'answering' | 'submitting' | 'feedback_ready' | 'saving_asset' | 'completed'

// --- Expression Asset ---
export interface ExpressionAsset {
  asset_id: string
  node_id: string
  topic_id: string
  attempt_id: string
  expression_type: PracticeType
  user_expression: string
  ai_rewrite: string
  skeleton: string
  quality_tags: string[]
  favorited: boolean
  created_at: string
}

export interface SaveExpressionAssetRequest {
  attempt_id: string
  expression_type: PracticeType
  user_expression: string
  ai_rewrite: string
  skeleton: string
  quality_tags: string[]
}

// --- Friction ---
export interface FrictionRecord {
  friction_id: string
  node_id: string
  topic_id: string
  friction_type: string
  description: string
  tags: string[]
  created_at: string
}

// --- Review ---
export interface ReviewItem {
  review_id: string
  node_id: string
  topic_id: string
  node_name?: string
  review_type: string
  priority: number
  due_at: string
  reason?: string
  status: ReviewStatus
  history_count: number
  last_result?: string
}

export interface ReviewSubmitRequest {
  user_answer: string
  session_id?: string
}

export interface ReviewSubmitResponse {
  result: FeedbackLevel
  feedback: FeedbackDetail
  ability_update: Partial<AbilityRecord> | null
  next_due_time: string | null
  needs_relearn: boolean
}

// --- Graph ---
export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta: GraphMeta
}

export interface GraphNode {
  node_id: string
  name: string
  status: NodeStatus
  importance: number
  is_mainline?: boolean
  is_current?: boolean
  is_collapsed?: boolean
  collapsed_count?: number
}

export interface GraphEdge {
  edge_id: string
  source_node_id: string
  target_node_id: string
  relation_type: EdgeType
  is_misunderstood?: boolean
}

export interface GraphMeta {
  view: GraphView
  collapsed: boolean
  current_node_id?: string
}

// --- Settings ---
export interface Settings {
  // API Provider
  openai_api_key: string
  openai_base_url: string
  openai_model_default: string
  openai_embed_model: string
  // Learning
  default_model: string
  default_learning_intent: LearningIntent
  default_mode: TopicMode
  max_graph_depth: number
  auto_start_practice: boolean
  auto_generate_summary: boolean
  // Ollama
  ollama_enabled: boolean
}

export interface UpdateSettingsRequest {
  openai_api_key?: string
  openai_base_url?: string
  openai_model_default?: string
  openai_embed_model?: string
  default_model?: string
  default_learning_intent?: LearningIntent
  default_mode?: TopicMode
  max_graph_depth?: number
  auto_start_practice?: boolean
  auto_generate_summary?: boolean
  ollama_enabled?: boolean
}

// --- Diagnostics ---
export interface DiagnoseResponse {
  friction_tags: string[]
  reasoning_summary: string
  suggested_prerequisites: RelatedNode[]
  recommended_practice_types: PracticeType[]
}

export interface AbilityOverviewNode extends RelatedNode {
  avg?: number
}

export interface ExplainGapNode extends RelatedNode {
  explain?: number
  understand?: number
}

export interface AbilityOverview {
  ability_averages: AbilityRecord | null
  weak_nodes: AbilityOverviewNode[]
  strongest_nodes: AbilityOverviewNode[]
  explain_gap_nodes: ExplainGapNode[]
}

// --- Health ---
export interface HealthStatus {
  status: 'ok' | 'degraded' | 'error'
  services: {
    api: boolean
    sqlite: boolean
    neo4j: boolean
    lancedb: boolean
    model_provider: boolean
    ollama: boolean
  }
}

// --- System Capabilities ---
export interface SystemCapabilities {
  ai_provider: 'openai' | 'ollama' | null
  ai_model: string
  embed_model: string
  ollama_enabled: boolean
  ollama_base_url: string
  supports_multimodal: boolean
  supports_local_fallback: boolean
  supports_export: boolean
  supports_review: boolean
  supports_expression_assets: boolean
}
