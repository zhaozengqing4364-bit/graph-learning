/**
 * Centralized React Query key factory for consistent cache management.
 * All queryKey arrays used in use-queries.ts and use-mutations.ts should reference these.
 */

export const queryKeys = {
  // Topics
  topics: (params?: Record<string, unknown>) => ['topics', params] as const,
  topic: (topicId: string) => ['topic', topicId] as const,
  topicEntryNode: (topicId: string) => ['topic', topicId, 'entry-node'] as const,
  topicWorkspace: (topicId: string) => ['topic', topicId, 'workspace'] as const,
  topicArticles: (topicId: string) => ['topic', topicId, 'articles'] as const,
  topicArticle: (topicId: string, articleId: string) => ['topic', topicId, 'article', articleId] as const,
  topicConceptNote: (topicId: string, conceptKey: string) => ['topic', topicId, 'concept-note', conceptKey] as const,
  topicReadingState: (topicId: string) => ['topic', topicId, 'reading-state'] as const,
  topicConceptCandidates: (topicId: string, status?: string) => ['topic', topicId, 'concept-candidates', status] as const,
  topicWorkspaceSearch: (topicId: string, query: string) => ['topic', topicId, 'workspace-search', query] as const,

  // Nodes
  nodeDetail: (topicId: string, nodeId: string) => ['topic', topicId, 'node', nodeId] as const,
  nodeAbility: (topicId: string, nodeId: string) => ['topic', topicId, 'node', nodeId, 'ability'] as const,
  nodeBacklinks: (topicId: string, nodeId: string) => ['topic', topicId, 'node', nodeId, 'backlinks'] as const,
  nodeNeighborhood: (topicId: string, nodeId: string, params?: Record<string, unknown>) =>
    ['topic', topicId, 'node', nodeId, 'neighborhood', params] as const,

  // Graph
  graph: (topicId: string, params?: Record<string, unknown>) => ['topic', topicId, 'graph', params] as const,
  graphMainline: (topicId: string) => ['topic', topicId, 'graph', 'mainline'] as const,

  // Session
  session: (topicId: string, sessionId: string) => ['topic', topicId, 'session', sessionId] as const,
  sessionSummary: (topicId: string, sessionId: string) => ['session-summary', topicId, sessionId] as const,

  // Practice
  expressionAssets: (topicId: string, params?: Record<string, unknown>) =>
    ['topic', topicId, 'expression-assets', params] as const,
  practiceAttempts: (topicId: string, params?: Record<string, unknown>) =>
    ['practice-attempts', topicId, params] as const,
  recommendedPractice: (topicId: string, nodeId: string) =>
    ['recommended-practice', topicId, nodeId] as const,

  // Ability
  abilitiesOverview: (topicId: string) => ['topic', topicId, 'abilities-overview'] as const,
  frictions: (topicId: string, params?: Record<string, unknown>) =>
    ['topic', topicId, 'frictions', params] as const,

  // Reviews
  reviews: (params?: Record<string, unknown>) => ['reviews', params] as const,
  review: (reviewId: string) => ['review', reviewId] as const,

  // Concept
  conceptSummary: (topicId: string, nodeId: string) => ['concept-summary', topicId, nodeId] as const,

  // Settings & System
  settings: ['settings'] as const,
  health: ['health'] as const,
  systemCapabilities: ['system-capabilities'] as const,
  deferredNodes: (topicId: string) => ['deferred-nodes', topicId] as const,

  // Stats
  globalStats: ['stats', 'global'] as const,
  topicStats: (topicId: string) => ['stats', 'topic', topicId] as const,
  abilitySnapshots: (topicId: string) => ['ability-snapshots', topicId] as const,
} as const
