import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'

import type { Node, ReadingStateRecord, Topic } from '../types'
import {
  buildArticleLibrary,
  partitionCommandResults,
  readingStatePayloadEquals,
  resolveConceptAppearance,
  upsertSourceArticle,
} from '../features/article-workspace/workspace-helpers'
import { ArticleHeader } from '../features/article-workspace/article-header'
import { ArticleLibrarySidebar } from '../features/article-workspace/article-library-sidebar'

const topic: Topic = {
  topic_id: 'tp_graph',
  title: '图学习',
  source_type: 'article',
  source_content: '图学习关注图结构数据上的表示学习。',
  learning_intent: 'build_system',
  mode: 'full_system',
  status: 'active',
  current_node_id: 'nd_message',
  entry_node_id: 'nd_intro',
  last_session_id: undefined,
  total_nodes: 4,
  learned_nodes: 1,
  due_review_count: 0,
  deferred_count: 0,
  created_at: '2026-03-16T00:00:00Z',
  updated_at: '2026-03-16T00:00:00Z',
}

const concepts: Node[] = [
  {
    node_id: 'nd_intro',
    name: '图表示',
    summary: '节点和边的表示基础',
    importance: 5,
    status: 'learning',
    topic_id: 'tp_graph',
    article_body: '图表示是图学习的入口。',
    created_at: '2026-03-16T00:00:00Z',
    updated_at: '2026-03-16T00:00:00Z',
  },
  {
    node_id: 'nd_message',
    name: '消息传递',
    summary: '图神经网络的核心更新机制',
    importance: 5,
    status: 'unseen',
    topic_id: 'tp_graph',
    article_body: '消息传递定义节点如何聚合邻居信息。',
    created_at: '2026-03-16T00:00:00Z',
    updated_at: '2026-03-16T00:00:00Z',
  },
]

describe('article workspace helpers', () => {
  it('builds guide, source, and concept groups for the article library', () => {
    const library = buildArticleLibrary({
      topic,
      sourceArticles: [
        {
          article_id: 'src-note-1',
          topic_id: 'tp_graph',
          title: '我的图学习笔记',
          body: '[[图表示]] 和 [[消息传递]] 是我现在最关心的概念。',
          created_at: '2026-03-16T00:00:00Z',
          updated_at: '2026-03-16T00:00:00Z',
        },
      ],
      conceptArticles: concepts,
    })

    expect(library.guide).toHaveLength(1)
    expect(library.guide[0].kind).toBe('guide')
    expect(library.guide[0].title).toBe('图学习')

    expect(library.source).toHaveLength(1)
    expect(library.source[0].kind).toBe('source')
    expect(library.source[0].title).toBe('我的图学习笔记')

    expect(library.concepts).toHaveLength(2)
    expect(library.concepts.map((item) => item.title)).toEqual(['图表示', '消息传递'])
  })

  it('partitions command results into workspace sections', () => {
    const sections = partitionCommandResults({
      articles: [
        { id: 'guide:tp_graph', label: '图学习', subtitle: '系统导读', kind: 'article' },
      ],
      concepts: [
        { id: 'concept:nd_message', label: '消息传递', subtitle: '概念', kind: 'concept' },
      ],
      notes: [
        { id: 'note:nd_message', label: '消息传递笔记', subtitle: '我的笔记', kind: 'note' },
      ],
      recent: [
        { id: 'recent:guide:tp_graph', label: '回到主题导读', subtitle: '最近访问', kind: 'recent' },
      ],
    })

    expect(sections.map((section) => section.key)).toEqual(['articles', 'concepts', 'notes', 'recent'])
    expect(sections[0].items[0].label).toBe('图学习')
    expect(sections[1].items[0].kind).toBe('concept')
  })

  it('distinguishes candidate from confirmed concept appearances', () => {
    expect(resolveConceptAppearance({ isConfirmed: true, isRecognized: true })).toBe('confirmed')
    expect(resolveConceptAppearance({ isConfirmed: false, isRecognized: true })).toBe('candidate')
    expect(resolveConceptAppearance({ isConfirmed: false, isRecognized: false })).toBe('plain')
  })

  it('updates or appends source articles deterministically', () => {
    const first = upsertSourceArticle([], {
      article_id: 'src-note-1',
      topic_id: 'tp_graph',
      title: '我的图学习笔记',
      body: '第一版',
      created_at: '2026-03-16T00:00:00Z',
      updated_at: '2026-03-16T00:00:00Z',
    })

    const second = upsertSourceArticle(first, {
      article_id: 'src-note-1',
      topic_id: 'tp_graph',
      title: '我的图学习笔记',
      body: '第二版',
      created_at: '2026-03-16T00:00:00Z',
      updated_at: '2026-03-16T01:00:00Z',
    })

    expect(second).toHaveLength(1)
    expect(second[0].body).toBe('第二版')
  })

  it('treats unchanged reading payloads as equal even if updated_at changes', () => {
    const savedState: ReadingStateRecord = {
      article_id: 'concept:nd_message',
      scroll_top: 420,
      trail: [
        { article_id: 'guide:tp_graph', title: '图学习' },
        { article_id: 'concept:nd_message', title: '消息传递' },
      ],
      completed_article_ids: ['guide:tp_graph'],
      updated_at: '2026-03-16T02:00:00Z',
    }

    expect(readingStatePayloadEquals(savedState, {
      article_id: 'concept:nd_message',
      scroll_top: 420,
      trail: [
        { article_id: 'guide:tp_graph', title: '图学习' },
        { article_id: 'concept:nd_message', title: '消息传递' },
      ],
      completed_article_ids: ['guide:tp_graph'],
    })).toBe(true)
  })

  it('detects meaningful reading payload changes', () => {
    const savedState: ReadingStateRecord = {
      article_id: 'concept:nd_message',
      scroll_top: 420,
      trail: [
        { article_id: 'guide:tp_graph', title: '图学习' },
        { article_id: 'concept:nd_message', title: '消息传递' },
      ],
      completed_article_ids: [],
      updated_at: '2026-03-16T02:00:00Z',
    }

    expect(readingStatePayloadEquals(savedState, {
      article_id: 'concept:nd_message',
      scroll_top: 421,
      trail: [
        { article_id: 'guide:tp_graph', title: '图学习' },
        { article_id: 'concept:nd_message', title: '消息传递' },
      ],
      completed_article_ids: [],
    })).toBe(false)
  })

  it('renders an editorial article header with source meta and summary', () => {
    const markup = renderToStaticMarkup(
      <ArticleHeader
        article={{
          id: 'guide:tp_graph',
          article_id: 'tp_graph',
          kind: 'guide',
          topic_id: 'tp_graph',
          title: '图学习',
          description: '从图表示到消息传递的主题导读。',
          updated_at: '2026-03-16T00:00:00Z',
        }}
        sourceLabel="系统导读"
        statusLabel="在读"
      />,
    )

    expect(markup).toContain('系统导读')
    expect(markup).toContain('图学习')
    expect(markup).toContain('从图表示到消息传递的主题导读。')
  })

  it('renders library groups for guide, source articles, and concept articles', () => {
    const library = buildArticleLibrary({
      topic,
      sourceArticles: [
        {
          article_id: 'src-note-1',
          topic_id: 'tp_graph',
          title: '我的图学习笔记',
          body: '[[图表示]] 和 [[消息传递]]',
          created_at: '2026-03-16T00:00:00Z',
          updated_at: '2026-03-16T00:00:00Z',
        },
      ],
      conceptArticles: concepts,
    })

    const markup = renderToStaticMarkup(
      <ArticleLibrarySidebar
        currentArticleId="guide:tp_graph"
        library={library}
        onSelectArticle={() => undefined}
        onCreateSourceArticle={() => undefined}
      />,
    )

    expect(markup).toContain('主题导读')
    expect(markup).toContain('源文章')
    expect(markup).toContain('概念专文')
    expect(markup).toContain('我的图学习笔记')
    expect(markup).toContain('消息传递')
  })
})
