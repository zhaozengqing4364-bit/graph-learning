import { useMemo } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

import { resolveNavigationContext } from '../lib/navigation-context'
import { useTopicListQuery, useTopicQuery } from './use-queries'

export function useResolvedTopicContext() {
  const { topicId: routeTopicId } = useParams<{ topicId: string }>()
  const [searchParams] = useSearchParams()
  const routeNodeId = searchParams.get('nodeId')
  const focusNodeId = searchParams.get('focus')
  const articleId = searchParams.get('article')
  const sessionId = searchParams.get('sessionId')

  const { data: activeTopics = [] } = useTopicListQuery({ status: 'active' })
  const { data: routeTopic } = useTopicQuery(routeTopicId || '')

  const resolved = useMemo(
    () => resolveNavigationContext({
      topics: activeTopics,
      routeTopicId,
      routeTopic: routeTopic || null,
      nodeId: routeNodeId,
      focusNodeId,
      articleId,
      sessionId,
    }),
    [activeTopics, articleId, focusNodeId, routeNodeId, routeTopic, routeTopicId, sessionId],
  )

  return {
    routeTopicId: routeTopicId || null,
    topic: resolved.topic,
    topic_id: resolved.topic_id,
    topicId: resolved.topic_id,
    node_id: resolved.node_id,
    nodeId: resolved.node_id,
    session_id: resolved.session_id,
    sessionId: resolved.session_id,
    explicitNodeId: resolved.explicit_node_id || null,
  }
}
