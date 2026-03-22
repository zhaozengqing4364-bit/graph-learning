import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { ArticleFooterPanel } from '../features/article-workspace/article-footer-panel'
import { ConceptDrawerContent } from '../features/article-workspace/concept-drawer-content'

describe('article workspace UI', () => {
  it('renders a single next-article recommendation and knowledge map groups', () => {
    const markup = renderToStaticMarkup(
      <ArticleFooterPanel
        recommendation={{
          article_id: 'concept:nd_graph',
          title: '图的表示',
          reason: '这是当前概念最关键的前置概念。',
        }}
        knowledgeMap={[
          {
            title: '前置概念',
            items: [{ name: '图的表示' }, { name: '线性代数' }],
          },
          {
            title: '相关概念',
            items: [{ name: '邻居采样' }],
          },
        ]}
        onOpenArticle={() => undefined}
      />,
    )

    expect(markup).toContain('继续下一篇：图的表示')
    expect(markup).toContain('这是当前概念最关键的前置概念。')
    expect(markup).toContain('知识地图')
    expect(markup).toContain('前置概念')
    expect(markup).toContain('相关概念')
  })

  it('renders concept drawer tabs with note editor and open-article action', () => {
    const markup = renderToStaticMarkup(
      <ConceptDrawerContent
        concept={{
          name: '消息传递',
          summary: '图神经网络中节点与邻居交换信息的核心机制。',
          relations: {
            title: '相关概念',
            items: ['图的表示', '邻居采样'],
          },
        }}
        generationState="ready"
        noteValue="记住聚合和更新是两个阶段。"
        onNoteChange={() => undefined}
        onOpenArticle={() => undefined}
        onConfirmConcept={() => undefined}
        onIgnoreConcept={() => undefined}
      />,
    )

    expect(markup).toContain('消息传递')
    expect(markup).toContain('概念')
    expect(markup).toContain('我的笔记')
    expect(markup).toContain('打开专文')
    expect(markup).toContain('确认概念')
  })
})
