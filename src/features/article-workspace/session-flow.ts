import { buildPracticeRoute, buildSummaryRoute } from '../../lib/navigation-context'
import type { CompleteSessionRequest } from '../../types'

interface ResolveLearningSessionPlanArgs {
  entryNodeId?: string | null
  sessionId?: string | null
  activeArticleId?: string | null
  activeConceptNodeId?: string | null
  lastVisitedNodeId?: string | null
}

interface LearningSessionPlan {
  shouldStartSession: boolean
  startPayload: { entry_node_id: string } | null
  visitPayload: { node_id: string; action_type: string } | null
}

interface ResolveArticleCompletionActionArgs {
  topicId: string
  activeArticleId: string
  activeConceptNodeId?: string | null
  sessionId?: string | null
  completedArticleIds: string[]
  autoStartPractice: boolean
  autoGenerateSummary: boolean
}

interface ArticleCompletionAction {
  completedArticleIds: string[]
  practiceRoute: string | null
  shouldCompleteSession: boolean
  completeSessionRequest: CompleteSessionRequest | null
  summaryRoute: string | null
}

interface ArticleCompletionIntentArgs {
  topicId: string
  articleId: string
  articleKind: 'guide' | 'source' | 'concept'
  nodeId?: string | null
  sessionId?: string | null
  autoStartPractice: boolean
}

type ArticleCompletionIntent =
  | { type: 'practice'; route: string }
  | { type: 'mark_only' }

interface SessionCompletionIntentArgs {
  topicId: string
  sessionId?: string | null
  autoGenerateSummary: boolean
}

type SessionCompletionIntent =
  | { type: 'summary'; route: string; request: CompleteSessionRequest }
  | { type: 'manual'; route: string | null; request: CompleteSessionRequest | null }

function appendUniqueId(ids: string[], articleId: string) {
  return ids.includes(articleId) ? ids : [...ids, articleId]
}

function defaultCompleteSessionRequest(): CompleteSessionRequest {
  return {
    generate_summary: true,
    generate_review_items: true,
  }
}

export function resolveLearningSessionPlan(args: ResolveLearningSessionPlanArgs): LearningSessionPlan {
  const sessionId = args.sessionId?.trim() || null
  const entryNodeId = args.entryNodeId?.trim() || null
  const activeConceptNodeId = args.activeConceptNodeId?.trim() || null
  const activeArticleId = args.activeArticleId?.trim() || null
  const lastVisitedNodeId = args.lastVisitedNodeId?.trim() || null

  if (!sessionId && entryNodeId) {
    return {
      shouldStartSession: true,
      startPayload: { entry_node_id: entryNodeId },
      visitPayload: null,
    }
  }

  if (
    sessionId
    && activeArticleId?.startsWith('concept:')
    && activeConceptNodeId
    && activeConceptNodeId !== lastVisitedNodeId
  ) {
    return {
      shouldStartSession: false,
      startPayload: null,
      visitPayload: {
        node_id: activeConceptNodeId,
        action_type: 'open_node',
      },
    }
  }

  return {
    shouldStartSession: false,
    startPayload: null,
    visitPayload: null,
  }
}

export function resolveArticleCompletionAction(
  args: ResolveArticleCompletionActionArgs,
): ArticleCompletionAction {
  const completedArticleIds = appendUniqueId(args.completedArticleIds, args.activeArticleId)
  const sessionId = args.sessionId?.trim() || null
  const activeConceptNodeId = args.activeConceptNodeId?.trim() || null
  const isConceptArticle = args.activeArticleId.startsWith('concept:') && Boolean(activeConceptNodeId)
  const shouldAutoPractice = isConceptArticle && args.autoStartPractice
  const shouldCompleteSession = isConceptArticle
    && !shouldAutoPractice
    && args.autoGenerateSummary
    && Boolean(sessionId)

  if (shouldAutoPractice && activeConceptNodeId) {
    return {
      completedArticleIds,
      practiceRoute: buildPracticeRoute(args.topicId, activeConceptNodeId, {
        auto: true,
        sessionId,
        summary: args.autoGenerateSummary && Boolean(sessionId),
      }),
      shouldCompleteSession: false,
      completeSessionRequest: null,
      summaryRoute: null,
    }
  }

  return {
    completedArticleIds,
    practiceRoute: null,
    shouldCompleteSession,
    completeSessionRequest: shouldCompleteSession ? defaultCompleteSessionRequest() : null,
    summaryRoute: shouldCompleteSession ? buildSummaryRoute(args.topicId, sessionId) : null,
  }
}

export function getArticleCompletionIntent(args: ArticleCompletionIntentArgs): ArticleCompletionIntent {
  const completion = resolveArticleCompletionAction({
    topicId: args.topicId,
    activeArticleId: args.articleId,
    activeConceptNodeId: args.articleKind === 'concept' ? args.nodeId : null,
    sessionId: args.sessionId,
    completedArticleIds: [],
    autoStartPractice: args.autoStartPractice,
    autoGenerateSummary: false,
  })

  if (completion.practiceRoute) {
    return {
      type: 'practice',
      route: completion.practiceRoute,
    }
  }

  return { type: 'mark_only' }
}

export function getSessionCompletionIntent(args: SessionCompletionIntentArgs): SessionCompletionIntent {
  const route = buildSummaryRoute(args.topicId, args.sessionId)
  const request = route ? defaultCompleteSessionRequest() : null

  if (args.autoGenerateSummary && route && request) {
    return {
      type: 'summary',
      route,
      request,
    }
  }

  return {
    type: 'manual',
    route,
    request,
  }
}
