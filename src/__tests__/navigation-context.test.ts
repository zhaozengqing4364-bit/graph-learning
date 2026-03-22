import { describe, expect, it } from 'vitest'

import {
  buildLearnRoute,
  buildPracticeRoute,
  buildSummaryRoute,
  extractRouteSessionId,
  extractRouteTopicId,
  extractContextNodeId,
  pickResolvedTopic,
  resolveNavigationContext,
  resolveTopicNodeId,
  sortTopicsByUpdatedAtDesc,
} from '../lib/navigation-context'
import type { Topic } from '../types'

const TOPICS: Topic[] = [
  {
    topic_id: 'tp_old',
    title: 'Old Topic',
    source_type: 'article',
    learning_intent: 'build_system',
    mode: 'full_system',
    status: 'active',
    current_node_id: 'nd_old_current',
    entry_node_id: 'nd_old_entry',
    last_session_id: 'ss_old',
    total_nodes: 4,
    learned_nodes: 1,
    due_review_count: 0,
    deferred_count: 0,
    created_at: '2026-03-15T09:00:00.000Z',
    updated_at: '2026-03-15T10:00:00.000Z',
  },
  {
    topic_id: 'tp_new',
    title: 'New Topic',
    source_type: 'article',
    learning_intent: 'build_system',
    mode: 'full_system',
    status: 'active',
    current_node_id: 'nd_new_current',
    entry_node_id: 'nd_new_entry',
    last_session_id: 'ss_new',
    total_nodes: 8,
    learned_nodes: 2,
    due_review_count: 1,
    deferred_count: 0,
    created_at: '2026-03-16T09:00:00.000Z',
    updated_at: '2026-03-16T10:00:00.000Z',
  },
]

describe('navigation context helpers', () => {
  it('sorts topics by updated_at descending', () => {
    expect(sortTopicsByUpdatedAtDesc(TOPICS).map((topic) => topic.topic_id)).toEqual(['tp_new', 'tp_old'])
  })

  it('prefers the route topic over the last active topic', () => {
    expect(pickResolvedTopic(TOPICS, 'tp_old')?.topic_id).toBe('tp_old')
    expect(pickResolvedTopic(TOPICS, null)?.topic_id).toBe('tp_new')
  })

  it('extracts a node id from node, focus, or concept article params', () => {
    expect(extractContextNodeId({ nodeId: 'nd_direct', focusNodeId: null, articleId: null })).toBe('nd_direct')
    expect(extractContextNodeId({ nodeId: '', focusNodeId: 'nd_focus', articleId: null })).toBe('nd_focus')
    expect(extractContextNodeId({ nodeId: '', focusNodeId: '', articleId: 'concept:nd_article' })).toBe('nd_article')
  })

  it('extracts topic and session ids from explicit route state', () => {
    expect(extractRouteTopicId('/topic/tp_new/graph')).toBe('tp_new')
    expect(extractRouteTopicId('/settings')).toBeNull()
    expect(extractRouteSessionId('?sessionId=ss_live')).toBe('ss_live')
    expect(extractRouteSessionId('view=full')).toBeNull()
  })

  it('falls back to topic current node and then entry node', () => {
    expect(resolveTopicNodeId(TOPICS[0], null)).toBe('nd_old_current')
    expect(resolveTopicNodeId({ ...TOPICS[0], current_node_id: undefined }, null)).toBe('nd_old_entry')
  })

  it('builds a practice route only when a node is available', () => {
    expect(buildPracticeRoute('tp_new', 'nd_new_current', { auto: true, sessionId: 'ss_live' })).toBe('/topic/tp_new/practice?nodeId=nd_new_current&sessionId=ss_live&auto=true')
    expect(buildPracticeRoute('tp_new', null)).toBe('/topic/tp_new/learn')
  })

  it('builds a learn route while preserving node and session context', () => {
    expect(buildLearnRoute('tp_new', { nodeId: 'nd_new_current', sessionId: 'ss_live' })).toBe('/topic/tp_new/learn?nodeId=nd_new_current&sessionId=ss_live')
    expect(buildLearnRoute('tp_new', { articleId: 'concept:nd_new_current', sessionId: 'ss_live' })).toBe('/topic/tp_new/learn?article=concept%3And_new_current&sessionId=ss_live')
  })

  it('only builds a summary route when a session id is available', () => {
    expect(buildSummaryRoute('tp_new', 'ss_new')).toBe('/topic/tp_new/summary?sessionId=ss_new')
    expect(buildSummaryRoute('tp_new', null)).toBeNull()
  })

  it('resolves topic, node, and session from route-first navigation state', () => {
    expect(resolveNavigationContext({
      topics: TOPICS,
      routeTopicId: 'tp_old',
      nodeId: '',
      focusNodeId: 'nd_focus',
      articleId: null,
      sessionId: 'ss_live',
    })).toMatchObject({
      topic_id: 'tp_old',
      node_id: 'nd_focus',
      session_id: 'ss_live',
    })
  })

  it('falls back to the freshest active topic and its current node when route data is missing', () => {
    expect(resolveNavigationContext({
      topics: TOPICS,
      routeTopicId: null,
      nodeId: null,
      focusNodeId: null,
      articleId: null,
      sessionId: null,
    })).toMatchObject({
      topic_id: 'tp_new',
      node_id: 'nd_new_current',
      session_id: null,
    })
  })
})
