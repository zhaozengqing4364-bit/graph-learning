import { beforeEach, describe, expect, it } from 'vitest'

import {
  clearWorkspaceTopicState,
  loadConceptNotes,
  loadReadingState,
  loadSourceArticles,
  saveReadingState,
  upsertConceptNote,
  upsertSourceArticleRecord,
} from '../lib/workspace-storage'

describe('workspace storage', () => {
  beforeEach(() => {
    clearWorkspaceTopicState('tp_graph')
  })

  it('persists source articles by topic', () => {
    upsertSourceArticleRecord('tp_graph', {
      article_id: 'src-1',
      topic_id: 'tp_graph',
      title: '图学习随记',
      body: '第一版内容',
      created_at: '2026-03-16T00:00:00Z',
      updated_at: '2026-03-16T00:00:00Z',
    })

    const stored = loadSourceArticles('tp_graph')

    expect(stored).toHaveLength(1)
    expect(stored[0].title).toBe('图学习随记')
  })

  it('updates a concept note without duplicating it', () => {
    upsertConceptNote('tp_graph', {
      note_id: 'note-1',
      topic_id: 'tp_graph',
      concept_key: 'nd_message',
      title: '消息传递笔记',
      body: '先记下聚合阶段。',
      updated_at: '2026-03-16T00:00:00Z',
    })

    upsertConceptNote('tp_graph', {
      note_id: 'note-1',
      topic_id: 'tp_graph',
      concept_key: 'nd_message',
      title: '消息传递笔记',
      body: '再补上更新阶段。',
      updated_at: '2026-03-16T01:00:00Z',
    })

    const notes = loadConceptNotes('tp_graph')

    expect(notes).toHaveLength(1)
    expect(notes[0].body).toBe('再补上更新阶段。')
  })

  it('stores reading state for precise resume', () => {
    saveReadingState('tp_graph', {
      article_id: 'concept:nd_message',
      scroll_top: 420,
      trail: [
        { article_id: 'guide:tp_graph', title: '图学习' },
        { article_id: 'concept:nd_message', title: '消息传递' },
      ],
      updated_at: '2026-03-16T02:00:00Z',
    })

    const state = loadReadingState('tp_graph')

    expect(state?.article_id).toBe('concept:nd_message')
    expect(state?.scroll_top).toBe(420)
    expect(state?.trail).toHaveLength(2)
  })
})
