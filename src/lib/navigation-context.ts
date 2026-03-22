import type { Topic } from '../types'

export interface NavigationContextInput {
  topics: Topic[]
  routeTopicId?: string | null
  routeTopic?: Topic | null
  nodeId?: string | null
  focusNodeId?: string | null
  articleId?: string | null
  sessionId?: string | null
}

export interface ResolvedNavigationContext {
  topic: Topic | null
  topic_id: string | null
  explicit_node_id?: string | null
  node_id: string | null
  session_id: string | null
}

export function sortTopicsByUpdatedAtDesc(topics: Topic[]): Topic[] {
  return [...topics].sort((left, right) => right.updated_at.localeCompare(left.updated_at))
}

export function extractRouteTopicId(pathname?: string | null): string | null {
  if (!pathname) {
    return null
  }

  const match = pathname.match(/^\/topic\/([^/]+)/)
  return match?.[1] || null
}

export function extractRouteSessionId(search?: string | URLSearchParams | null): string | null {
  if (!search) {
    return null
  }

  const params = typeof search === 'string'
    ? new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
    : search
  const sessionId = params.get('sessionId')?.trim()

  return sessionId || null
}

export function pickResolvedTopic(topics: Topic[], routeTopicId?: string | null): Topic | null {
  if (routeTopicId) {
    return topics.find((topic) => topic.topic_id === routeTopicId) ?? null
  }

  return sortTopicsByUpdatedAtDesc(topics.filter((topic) => topic.status === 'active'))[0] ?? null
}

export function extractContextNodeId(args: {
  nodeId?: string | null
  focusNodeId?: string | null
  articleId?: string | null
}): string | null {
  const nodeId = args.nodeId?.trim()
  if (nodeId) {
    return nodeId
  }

  const focusNodeId = args.focusNodeId?.trim()
  if (focusNodeId) {
    return focusNodeId
  }

  if (args.articleId?.startsWith('concept:')) {
    return args.articleId.slice('concept:'.length) || null
  }

  return null
}

export function resolveTopicNodeId(
  topic: Pick<Topic, 'current_node_id' | 'entry_node_id'> | null,
  explicitNodeId?: string | null,
): string | null {
  return explicitNodeId || topic?.current_node_id || topic?.entry_node_id || null
}

export function resolveNavigationContext(args: NavigationContextInput): ResolvedNavigationContext {
  const topic = args.routeTopic || pickResolvedTopic(args.topics, args.routeTopicId)
  const explicitNodeId = extractContextNodeId({
    nodeId: args.nodeId,
    focusNodeId: args.focusNodeId,
    articleId: args.articleId,
  })

  return {
    topic,
    topic_id: topic?.topic_id || null,
    explicit_node_id: explicitNodeId,
    node_id: resolveTopicNodeId(topic, explicitNodeId),
    session_id: args.sessionId?.trim() || null,
  }
}

export function buildPracticeRoute(
  topicId: string,
  nodeId?: string | null,
  options?: { auto?: boolean; sessionId?: string | null; summary?: boolean },
): string {
  if (!nodeId) {
    return `/topic/${topicId}/learn`
  }

  const search = new URLSearchParams({ nodeId })
  const sessionId = options?.sessionId?.trim()
  if (sessionId) {
    search.set('sessionId', sessionId)
  }
  if (options?.auto) {
    search.set('auto', 'true')
  }
  if (options?.summary) {
    search.set('summary', 'true')
  }

  return `/topic/${topicId}/practice?${search.toString()}`
}

export function buildLearnRoute(
  topicId: string,
  options?: {
    nodeId?: string | null
    articleId?: string | null
    sessionId?: string | null
  },
): string {
  const search = new URLSearchParams()

  const nodeId = options?.nodeId?.trim()
  const articleId = options?.articleId?.trim()
  const sessionId = options?.sessionId?.trim()

  if (nodeId) {
    search.set('nodeId', nodeId)
  } else if (articleId) {
    search.set('article', articleId)
  }

  if (sessionId) {
    search.set('sessionId', sessionId)
  }

  const query = search.toString()
  return query ? `/topic/${topicId}/learn?${query}` : `/topic/${topicId}/learn`
}

export function buildSummaryRoute(topicId: string, sessionId?: string | null): string | null {
  if (!sessionId) {
    return null
  }

  return `/topic/${topicId}/summary?sessionId=${sessionId}`
}
