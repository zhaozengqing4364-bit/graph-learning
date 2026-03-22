import type { Node, ReadingStateRecord, Topic } from '../../types'
import {
  buildConceptArticles,
  buildGuideArticle,
  buildArticleLibrarySections,
  buildSourceWorkspaceArticles,
  pushBreadcrumb,
  resolveConceptAppearance,
  upsertSourceArticle,
  type WorkspaceArticle,
  type WorkspaceArticleSection,
  type SourceArticleRecord,
} from '../../lib/article-workspace'

export type { SourceArticleRecord }

export interface WorkspaceArticleItem {
  id: string
  article_id: string
  title: string
  subtitle: string
  kind: 'guide' | 'source' | 'concept'
  body: string
}

export interface CommandResultItem {
  id: string
  label: string
  subtitle: string
  kind: 'article' | 'concept' | 'note' | 'recent'
}

export interface CommandResultSection {
  key: 'articles' | 'concepts' | 'notes' | 'recent'
  title: string
  items: CommandResultItem[]
}

export interface ReadingStatePayload {
  article_id: string
  scroll_top: number
  trail: Array<{ article_id: string; title: string }>
  completed_article_ids: string[]
}

export function buildArticleLibrary(input: {
  topic: Topic
  sourceArticles: SourceArticleRecord[]
  conceptArticles: Node[]
}) {
  const guide = [
    {
      id: `guide:${input.topic.topic_id}`,
      article_id: `guide:${input.topic.topic_id}`,
      title: input.topic.title,
      subtitle: '系统导读',
      kind: 'guide' as const,
      body: buildGuideArticle(input.topic, input.conceptArticles[0], input.conceptArticles.slice(1, 4)).body,
    },
  ]

  const source = buildSourceWorkspaceArticles(input.sourceArticles).map((article) => ({
    id: article.article_id,
    article_id: article.article_id,
    title: article.title,
    subtitle: '我的文章',
    kind: 'source' as const,
    body: article.body,
  }))

  const concepts = buildConceptArticles(input.conceptArticles).map((article) => ({
    id: article.article_id,
    article_id: article.article_id,
    title: article.title,
    subtitle: '概念专文',
    kind: 'concept' as const,
    body: article.body,
  }))

  return { guide, source, concepts }
}

export { buildGuideArticle, buildArticleLibrarySections, pushBreadcrumb }
export type { WorkspaceArticle, WorkspaceArticleSection }

export function partitionCommandResults(input: {
  articles: CommandResultItem[]
  concepts: CommandResultItem[]
  notes: CommandResultItem[]
  recent: CommandResultItem[]
}): CommandResultSection[] {
  const sections: CommandResultSection[] = []
  if (input.articles.length > 0) sections.push({ key: 'articles', title: '文章', items: input.articles })
  if (input.concepts.length > 0) sections.push({ key: 'concepts', title: '概念', items: input.concepts })
  if (input.notes.length > 0) sections.push({ key: 'notes', title: '我的笔记', items: input.notes })
  if (input.recent.length > 0) sections.push({ key: 'recent', title: '最近访问', items: input.recent })
  return sections
}

export function buildReadingStatePayload(input: {
  articleId: string
  scrollTop: number
  trail: Array<{ article_id: string; title: string }>
  completedArticleIds: string[]
}): ReadingStatePayload {
  return {
    article_id: input.articleId,
    scroll_top: input.scrollTop,
    trail: input.trail.map((item) => ({ article_id: item.article_id, title: item.title })),
    completed_article_ids: [...input.completedArticleIds],
  }
}

export function readingStatePayloadEquals(
  previous: Pick<ReadingStateRecord, 'article_id' | 'scroll_top' | 'trail' | 'completed_article_ids'> | ReadingStatePayload | null | undefined,
  next: ReadingStatePayload | null | undefined,
) {
  if (!previous || !next) {
    return false
  }

  if (previous.article_id !== next.article_id || previous.scroll_top !== next.scroll_top) {
    return false
  }

  const previousTrail = previous.trail || []
  if (previousTrail.length !== next.trail.length) {
    return false
  }

  for (let index = 0; index < previousTrail.length; index += 1) {
    if (
      previousTrail[index]?.article_id !== next.trail[index]?.article_id
      || previousTrail[index]?.title !== next.trail[index]?.title
    ) {
      return false
    }
  }

  const previousCompleted = previous.completed_article_ids || []
  if (previousCompleted.length !== next.completed_article_ids.length) {
    return false
  }

  return previousCompleted.every((articleId, index) => articleId === next.completed_article_ids[index])
}

export { resolveConceptAppearance, upsertSourceArticle }
