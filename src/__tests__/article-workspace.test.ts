import { describe, expect, it } from 'vitest'

import {
  articleStatusLabel,
  buildBacklinksForConcept,
  buildArticleLibrarySections,
  buildCommandPaletteGroups,
  buildGuideArticle,
  pickNextArticleRecommendation,
  pushBreadcrumb,
  validateWikiLinks,
  type WorkspaceArticle,
  type WorkspaceBreadcrumbItem,
} from '../lib/article-workspace'

describe('article workspace transforms', () => {
  it('builds a guide article from topic, entry node, and mainline concepts', () => {
    const guide = buildGuideArticle(
      {
        topic_id: 'tp_graph',
        title: '图学习',
        learning_intent: 'build_system',
        source_content: '图学习关注图结构数据上的表示、推理和预测。',
        updated_at: '2026-03-16T08:00:00.000Z',
      },
      {
        node_id: 'nd_message',
        name: '消息传递',
        summary: '图神经网络通过邻居聚合传递信息的核心机制。',
      },
      [
        { node_id: 'nd_graph', name: '图的表示', summary: '节点、边与属性的表达方式。', importance: 5, status: 'unseen' },
        { node_id: 'nd_sampling', name: '邻居采样', summary: '控制大图训练成本的常见方法。', importance: 4, status: 'unseen' },
      ],
    )

    expect(guide.kind).toBe('guide')
    expect(guide.article_id).toBe('guide:tp_graph')
    expect(guide.title).toBe('图学习')
    expect(guide.deck).toContain('构建体系')
    expect(guide.body).toContain('[[消息传递]]')
    expect(guide.body).toContain('[[图的表示]]')
    expect(guide.body).toContain('[[邻居采样]]')
  })

  it('builds article library sections with stable ordering', () => {
    const guide: WorkspaceArticle = {
      article_id: 'guide:tp_graph',
      topic_id: 'tp_graph',
      kind: 'guide',
      title: '图学习',
      deck: '主题导读',
      body: '导读正文',
      source_label: '系统导读',
      updated_at: '2026-03-16T08:00:00.000Z',
    }

    const sections = buildArticleLibrarySections({
      guide,
      sourceArticles: [
        {
          article_id: 'source:2',
          topic_id: 'tp_graph',
          kind: 'source',
          title: '第二篇笔记',
          deck: '我的文章',
          body: 'B',
          source_label: '我的文章',
          updated_at: '2026-03-16T10:00:00.000Z',
        },
        {
          article_id: 'source:1',
          topic_id: 'tp_graph',
          kind: 'source',
          title: '第一篇笔记',
          deck: '我的文章',
          body: 'A',
          source_label: '我的文章',
          updated_at: '2026-03-16T09:00:00.000Z',
        },
      ],
      conceptArticles: [
        {
          article_id: 'concept:nd_sampling',
          topic_id: 'tp_graph',
          kind: 'concept',
          title: '邻居采样',
          deck: '概念专文',
          body: '...',
          source_label: '概念专文',
          node_id: 'nd_sampling',
          updated_at: '2026-03-16T11:00:00.000Z',
        },
      ],
    })

    expect(sections.map((section) => section.key)).toEqual(['guide', 'source', 'concept'])
    expect(sections[0].articles).toHaveLength(1)
    expect(sections[1].articles.map((article) => article.article_id)).toEqual(['source:2', 'source:1'])
    expect(sections[2].articles[0].title).toBe('邻居采样')
  })

  it('pushes breadcrumb items without duplicating the current article twice in a row', () => {
    const trail: WorkspaceBreadcrumbItem[] = [
      { article_id: 'guide:tp_graph', kind: 'guide', title: '图学习' },
      { article_id: 'concept:nd_message', kind: 'concept', title: '消息传递', node_id: 'nd_message' },
    ]

    const next = pushBreadcrumb(trail, { article_id: 'concept:nd_message', kind: 'concept', title: '消息传递', node_id: 'nd_message' })
    const expanded = pushBreadcrumb(next, { article_id: 'concept:nd_sampling', kind: 'concept', title: '邻居采样', node_id: 'nd_sampling' })

    expect(next).toEqual(trail)
    expect(expanded.map((item) => item.article_id)).toEqual(['guide:tp_graph', 'concept:nd_message', 'concept:nd_sampling'])
  })

  it('groups command palette results by articles, concepts, notes, and actions', () => {
    const groups = buildCommandPaletteGroups({
      query: '图',
      sections: [
        {
          key: 'guide',
          title: '主题导读',
          articles: [
            {
              article_id: 'guide:tp_graph',
              topic_id: 'tp_graph',
              kind: 'guide',
              title: '图学习',
              deck: '主题导读',
              body: '导读正文',
              source_label: '系统导读',
              updated_at: '2026-03-16T08:00:00.000Z',
            },
          ],
        },
      ],
      conceptMatches: [
        { node_id: 'nd_graph', name: '图的表示', summary: '图结构的表达方式。' },
      ],
      conceptNotes: [
        { node_id: 'nd_graph', name: '图的表示', preview: '我总把邻接矩阵和边列表混掉。' },
      ],
      recentArticles: [
        { article_id: 'guide:tp_graph', kind: 'guide', title: '图学习' },
      ],
    })

    expect(groups.map((group) => group.key)).toEqual(['articles', 'concepts', 'notes', 'actions'])
    expect(groups[0].items[0].label).toBe('图学习')
    expect(groups[1].items[0].label).toBe('图的表示')
    expect(groups[2].items[0].label).toBe('图的表示')
    expect(groups[3].items.some((item) => item.label === '新建源文章')).toBe(true)
  })

  it('prefers backend workspace search results when query is present', () => {
    const groups = buildCommandPaletteGroups({
      query: '采样',
      sections: [
        {
          key: 'guide',
          title: '主题导读',
          articles: [
            {
              article_id: 'guide:tp_graph',
              topic_id: 'tp_graph',
              kind: 'guide',
              title: '图学习',
              deck: '主题导读',
              body: '导读正文',
              source_label: '系统导读',
              updated_at: '2026-03-16T08:00:00.000Z',
            },
          ],
        },
      ],
      conceptMatches: [],
      conceptNotes: [],
      recentArticles: [],
      searchResults: {
        articles: [
          {
            article_id: 'source:2',
            title: '邻居采样实验',
            body: '记录采样策略。',
            updated_at: '2026-03-16T10:00:00.000Z',
          },
        ],
        concepts: [
          {
            node_id: 'nd_sampling',
            name: '邻居采样',
            summary: '控制大图训练成本的常见方法。',
          },
        ],
        notes: [
          {
            concept_key: 'nd_sampling',
            title: '邻居采样笔记',
            body: '先记住分层采样。',
            updated_at: '2026-03-16T11:00:00.000Z',
          },
        ],
      },
    })

    expect(groups.map((group) => group.key)).toEqual(['articles', 'concepts', 'notes', 'actions'])
    expect(groups[0].items[0].article_id).toBe('source:2')
    expect(groups[1].items[0].article_id).toBe('concept:nd_sampling')
    expect(groups[2].items[0].label).toBe('邻居采样笔记')
  })

  it('prefers the most important prerequisite as the next article recommendation', () => {
    const recommendation = pickNextArticleRecommendation({
      currentArticle: {
        article_id: 'concept:nd_message',
        topic_id: 'tp_graph',
        kind: 'concept',
        title: '消息传递',
        deck: '概念专文',
        body: '...',
        source_label: '概念专文',
        updated_at: '2026-03-16T12:00:00.000Z',
        node_id: 'nd_message',
      },
      conceptRelations: {
        prerequisites: [
          { node_id: 'nd_graph', name: '图的表示', summary: '图结构表示是前提。', importance: 5 },
          { node_id: 'nd_linear', name: '线性代数', summary: '矩阵运算基础。', importance: 3 },
        ],
        related: [
          { node_id: 'nd_sampling', name: '邻居采样', summary: '控制采样成本。', importance: 4 },
        ],
      },
      visitedArticleIds: ['guide:tp_graph'],
    })

    expect(recommendation?.article_id).toBe('concept:nd_graph')
    expect(recommendation?.reason).toContain('前置概念')
  })

  it('validates wiki links and reports unresolved concepts on save', () => {
    const validation = validateWikiLinks(
      '我先记下 [[图的表示]]，再补一个 [[不存在的概念]]。',
      [
        { node_id: 'nd_graph', name: '图的表示' },
        { node_id: 'nd_message', name: '消息传递' },
      ],
    )

    expect(validation.valid_links).toEqual(['图的表示'])
    expect(validation.invalid_links).toEqual(['不存在的概念'])
  })

  it('builds collapsed backlinks for source articles mentioning a concept', () => {
    const backlinks = buildBacklinksForConcept('消息传递', [
      {
        article_id: 'source:1',
        topic_id: 'tp_graph',
        title: 'GNN 学习随记',
        body: '第一段。\n\n第二段提到 [[消息传递]] 如何聚合邻居信息。\n\n第三段。',
        created_at: '2026-03-16T10:00:00.000Z',
        updated_at: '2026-03-16T10:00:00.000Z',
      },
    ])

    expect(backlinks).toHaveLength(1)
    expect(backlinks[0].article_id).toBe('source:1')
    expect(backlinks[0].anchor_id).toBe('source:1:paragraph:1')
    expect(backlinks[0].snippet).toContain('消息传递')
  })

  it('marks the active article as in progress before treating it as visited', () => {
    expect(articleStatusLabel('concept:nd_message', 'concept:nd_message', [
      { article_id: 'guide:tp_graph', kind: 'guide', title: '图学习' },
      { article_id: 'concept:nd_message', kind: 'concept', title: '消息传递', node_id: 'nd_message' },
    ], [])).toBe('在读')
  })
})
