import { describe, expect, it } from 'vitest'

import {
  resolveArticleCompletionAction,
  resolveLearningSessionPlan,
} from '../features/article-workspace/session-flow'

describe('learning session flow helpers', () => {
  it('starts a session from the entry node when learn workspace has no live session yet', () => {
    expect(resolveLearningSessionPlan({
      entryNodeId: 'nd_entry',
      sessionId: null,
      activeArticleId: 'guide:tp_graph',
      activeConceptNodeId: null,
      lastVisitedNodeId: null,
    })).toEqual({
      shouldStartSession: true,
      startPayload: { entry_node_id: 'nd_entry' },
      visitPayload: null,
    })
  })

  it('records a visit when a live session opens a different concept article', () => {
    expect(resolveLearningSessionPlan({
      entryNodeId: 'nd_entry',
      sessionId: 'ss_live',
      activeArticleId: 'concept:nd_message',
      activeConceptNodeId: 'nd_message',
      lastVisitedNodeId: 'nd_entry',
    })).toEqual({
      shouldStartSession: false,
      startPayload: null,
      visitPayload: {
        node_id: 'nd_message',
        action_type: 'open_node',
      },
    })
  })

  it('routes completed concept articles into practice when auto-start is enabled', () => {
    expect(resolveArticleCompletionAction({
      topicId: 'tp_graph',
      activeArticleId: 'concept:nd_message',
      activeConceptNodeId: 'nd_message',
      sessionId: 'ss_live',
      completedArticleIds: [],
      autoStartPractice: true,
      autoGenerateSummary: false,
    })).toEqual({
      completedArticleIds: ['concept:nd_message'],
      practiceRoute: '/topic/tp_graph/practice?nodeId=nd_message&sessionId=ss_live&auto=true',
      shouldCompleteSession: false,
      completeSessionRequest: null,
      summaryRoute: null,
    })
  })

  it('completes the session and jumps to summary when auto summary is enabled without auto practice', () => {
    expect(resolveArticleCompletionAction({
      topicId: 'tp_graph',
      activeArticleId: 'concept:nd_message',
      activeConceptNodeId: 'nd_message',
      sessionId: 'ss_live',
      completedArticleIds: ['guide:tp_graph'],
      autoStartPractice: false,
      autoGenerateSummary: true,
    })).toEqual({
      completedArticleIds: ['guide:tp_graph', 'concept:nd_message'],
      practiceRoute: null,
      shouldCompleteSession: true,
      completeSessionRequest: {
        generate_summary: true,
        generate_review_items: true,
      },
      summaryRoute: '/topic/tp_graph/summary?sessionId=ss_live',
    })
  })

  it('does not auto-complete the session for guide articles when auto summary is enabled', () => {
    expect(resolveArticleCompletionAction({
      topicId: 'tp_graph',
      activeArticleId: 'guide:tp_graph',
      activeConceptNodeId: null,
      sessionId: 'ss_live',
      completedArticleIds: [],
      autoStartPractice: false,
      autoGenerateSummary: true,
    })).toEqual({
      completedArticleIds: ['guide:tp_graph'],
      practiceRoute: null,
      shouldCompleteSession: false,
      completeSessionRequest: null,
      summaryRoute: null,
    })
  })
})
