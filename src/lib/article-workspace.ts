import type { EntryNode, Node, SourceArticleRecord, Topic, WorkspaceSearchResult } from '../types'

export type { SourceArticleRecord }

export type WorkspaceArticleKind = 'guide' | 'source' | 'concept'

export interface WorkspaceArticle {
  article_id: string
  topic_id: string
  kind: WorkspaceArticleKind
  title: string
  deck: string
  body: string
  source_label: string
  updated_at: string
  description?: string
  node_id?: string
}

export interface WorkspaceArticleSection {
  key: 'guide' | 'source' | 'concept'
  title: string
  articles: WorkspaceArticle[]
}

export interface WorkspaceBreadcrumbItem {
  article_id: string
  kind: WorkspaceArticleKind
  title: string
  node_id?: string
}

export interface WorkspaceCommandItem {
  id: string
  label: string
  subtitle: string
  kind: 'article' | 'concept' | 'note' | 'recent' | 'action'
  article_id?: string
  node_id?: string
  action_id?: 'new-source-article' | 'return-guide' | 'open-library' | 'recent-history'
}

export interface WorkspaceCommandGroup {
  key: 'articles' | 'concepts' | 'notes' | 'recent' | 'actions'
  title: string
  items: WorkspaceCommandItem[]
}

export interface WorkspaceConceptNoteMatch {
  node_id: string
  name: string
  preview: string
}

export interface WorkspaceRecommendation {
  article_id: string
  title: string
  reason: string
  node_id?: string
}

export interface WorkspaceBacklink {
  article_id: string
  title: string
  anchor_id: string
  snippet: string
}

const WIKI_LINK_RE = /\[\[(.+?)\]\]/g

export function resolveConceptAppearance({
  isConfirmed,
  isRecognized,
}: {
  isConfirmed: boolean
  isRecognized: boolean
}): 'confirmed' | 'candidate' | 'plain' {
  if (isConfirmed && isRecognized) {
    return 'confirmed'
  }

  if (!isConfirmed && isRecognized) {
    return 'candidate'
  }

  return 'plain'
}

export function upsertSourceArticle(
  articles: SourceArticleRecord[],
  nextArticle: SourceArticleRecord,
): SourceArticleRecord[] {
  const existingIndex = articles.findIndex((article) => article.article_id === nextArticle.article_id)

  if (existingIndex === -1) {
    return [...articles, nextArticle]
  }

  return articles.map((article, index) => (index === existingIndex ? nextArticle : article))
}

function intentLabel(intent?: Topic['learning_intent']) {
  return {
    build_system: '构建体系',
    fix_gap: '弥补短板',
    solve_task: '解决任务',
    prepare_expression: '准备表达',
    prepare_interview: '准备面试',
  }[intent || 'build_system'] || '构建体系'
}

function sectionTitle(key: WorkspaceArticleSection['key']) {
  return {
    guide: '主题导读',
    source: '源文章',
    concept: '概念专文',
  }[key]
}

function sortByUpdatedAtDesc<T extends { updated_at?: string }>(items: T[]) {
  return [...items].sort((left, right) => (right.updated_at || '').localeCompare(left.updated_at || ''))
}

function normalizeQuery(value: string) {
  return value.trim().toLowerCase()
}

function matchesQuery(value: string, query: string) {
  if (!query) {
    return true
  }

  return value.toLowerCase().includes(query)
}

export function buildGuideArticle(
  topic: Pick<Topic, 'topic_id' | 'title' | 'learning_intent' | 'source_content' | 'updated_at'>,
  entryNode?: Pick<EntryNode, 'node_id' | 'name' | 'summary'> | null,
  mainlineConcepts: Array<Pick<Node, 'node_id' | 'name' | 'summary' | 'importance' | 'status'>> = [],
): WorkspaceArticle {
  const sections = [
    topic.source_content?.trim() || `${topic.title} 的主题导读会先给出整体叙事，再把关键概念拆成可继续阅读的文章。`,
  ]

  if (entryNode) {
    sections.push(
      `## 从 [[${entryNode.name}]] 开始\n${entryNode.summary || `${entryNode.name} 是这条阅读路径的入口概念。`}`,
    )
  }

  if (mainlineConcepts.length > 0) {
    const bullets = mainlineConcepts.map(
      (concept) => `- [[${concept.name}]]：${concept.summary || `${concept.name} 是本主题的重要节点。`}`,
    )
    sections.push(`## 这条阅读链会继续展开\n${bullets.join('\n')}`)
  }

  return {
    article_id: `guide:${topic.topic_id}`,
    topic_id: topic.topic_id,
    kind: 'guide',
    title: topic.title,
    deck: `${intentLabel(topic.learning_intent)}导向的叙事式主题导读`,
    body: sections.join('\n\n'),
    source_label: '系统导读',
    updated_at: topic.updated_at,
    description: entryNode
      ? `从 ${entryNode.name} 出发，把这组概念组织成一条连续的阅读路径。`
      : '从主题总览切入，逐步展开概念文章和源文章。',
  }
}

export function buildSourceWorkspaceArticles(sourceArticles: SourceArticleRecord[]): WorkspaceArticle[] {
  return sortByUpdatedAtDesc(sourceArticles).map((article) => ({
    article_id: article.article_id,
    topic_id: article.topic_id,
    kind: 'source',
    title: article.title,
    deck: '我在当前主题下持续编辑的源文章。',
    body: article.body,
    source_label: '我的文章',
    updated_at: article.updated_at,
    description: '可编辑的原始文章，会在保存后重新分析概念提及。',
  }))
}

export function buildConceptArticles(
  concepts: Array<Pick<Node, 'node_id' | 'name' | 'summary' | 'article_body' | 'topic_id' | 'updated_at'>>,
): WorkspaceArticle[] {
  return sortByUpdatedAtDesc(concepts).map((concept) => ({
    article_id: `concept:${concept.node_id}`,
    topic_id: concept.topic_id,
    kind: 'concept',
    title: concept.name,
    deck: '稳定的概念专文，用于承载解释、关系与回链。',
    body: concept.article_body || concept.summary,
    source_label: '概念专文',
    updated_at: concept.updated_at,
    description: concept.summary,
    node_id: concept.node_id,
  }))
}

export function buildArticleLibrarySections({
  guide,
  sourceArticles,
  conceptArticles,
}: {
  guide: WorkspaceArticle
  sourceArticles: WorkspaceArticle[]
  conceptArticles: WorkspaceArticle[]
}): WorkspaceArticleSection[] {
  const sections: WorkspaceArticleSection[] = [
    { key: 'guide', title: sectionTitle('guide'), articles: [guide] },
  ]

  if (sourceArticles.length > 0) {
    sections.push({
      key: 'source',
      title: sectionTitle('source'),
      articles: sortByUpdatedAtDesc(sourceArticles),
    })
  }

  if (conceptArticles.length > 0) {
    sections.push({
      key: 'concept',
      title: sectionTitle('concept'),
      articles: sortByUpdatedAtDesc(conceptArticles),
    })
  }

  return sections
}

export function pushBreadcrumb(
  trail: WorkspaceBreadcrumbItem[],
  nextItem: WorkspaceBreadcrumbItem,
): WorkspaceBreadcrumbItem[] {
  const current = trail[trail.length - 1]

  if (current?.article_id === nextItem.article_id) {
    return trail
  }

  return [...trail, nextItem]
}

export function popBreadcrumb(trail: WorkspaceBreadcrumbItem[]) {
  if (trail.length <= 1) {
    return trail
  }

  return trail.slice(0, -1)
}

export function articleStatusLabel(
  articleId: string,
  activeArticleId: string,
  trail: WorkspaceBreadcrumbItem[],
  completedArticleIds: string[],
) {
  if (completedArticleIds.includes(articleId)) {
    return '已完成'
  }

  if (articleId !== activeArticleId && trail.some((item) => item.article_id === articleId)) {
    return '已浏览'
  }

  return '在读'
}

export function buildCommandPaletteGroups({
  query,
  sections,
  conceptMatches,
  conceptNotes,
  recentArticles,
  searchResults,
}: {
  query: string
  sections: WorkspaceArticleSection[]
  conceptMatches: Array<Pick<Node, 'node_id' | 'name' | 'summary'>>
  conceptNotes: WorkspaceConceptNoteMatch[]
  recentArticles: Array<Pick<WorkspaceBreadcrumbItem, 'article_id' | 'kind' | 'title'>>
  searchResults?: WorkspaceSearchResult | null
}): WorkspaceCommandGroup[] {
  const normalizedQuery = normalizeQuery(query)
  const groups: WorkspaceCommandGroup[] = []

  const articleItems = normalizedQuery && searchResults
    ? searchResults.articles
      .filter((article) => matchesQuery(`${article.title} ${article.body || ''}`, normalizedQuery))
      .map<WorkspaceCommandItem>((article) => ({
        id: article.article_id,
        label: article.title,
        subtitle: '搜索命中 · 源文章',
        kind: 'article',
        article_id: article.article_id,
      }))
    : sections
      .flatMap((section) => section.articles)
      .filter((article) => matchesQuery(`${article.title} ${article.deck} ${article.description || ''}`, normalizedQuery))
      .map<WorkspaceCommandItem>((article) => ({
        id: article.article_id,
        label: article.title,
        subtitle: article.source_label,
        kind: 'article',
        article_id: article.article_id,
        node_id: article.node_id,
      }))

  if (articleItems.length > 0) {
    groups.push({ key: 'articles', title: '文章', items: articleItems })
  }

  const conceptItems = normalizedQuery && searchResults
    ? searchResults.concepts
      .filter((concept) => matchesQuery(`${concept.name} ${concept.summary || ''}`, normalizedQuery))
      .map<WorkspaceCommandItem>((concept) => ({
        id: `concept:${concept.node_id}`,
        label: concept.name,
        subtitle: concept.summary || '搜索命中 · 概念',
        kind: 'concept',
        article_id: `concept:${concept.node_id}`,
        node_id: concept.node_id,
      }))
    : conceptMatches
      .filter((concept) => matchesQuery(`${concept.name} ${concept.summary || ''}`, normalizedQuery))
      .map<WorkspaceCommandItem>((concept) => ({
        id: `concept:${concept.node_id}`,
        label: concept.name,
        subtitle: concept.summary || '概念',
        kind: 'concept',
        article_id: `concept:${concept.node_id}`,
        node_id: concept.node_id,
      }))

  if (conceptItems.length > 0) {
    groups.push({ key: 'concepts', title: '概念', items: conceptItems })
  }

  const noteItems = normalizedQuery && searchResults
    ? searchResults.notes
      .filter((note) => matchesQuery(`${note.title} ${note.body || ''}`, normalizedQuery))
      .map<WorkspaceCommandItem>((note) => ({
        id: `note:${note.concept_key}`,
        label: note.title,
        subtitle: note.body.slice(0, 36) || '搜索命中 · 概念笔记',
        kind: 'note',
        article_id: note.concept_key.startsWith('nd_') ? `concept:${note.concept_key}` : undefined,
        node_id: note.concept_key,
      }))
    : conceptNotes
      .filter((note) => matchesQuery(`${note.name} ${note.preview}`, normalizedQuery))
      .map<WorkspaceCommandItem>((note) => ({
        id: `note:${note.node_id}`,
        label: note.name,
        subtitle: note.preview,
        kind: 'note',
        article_id: `concept:${note.node_id}`,
        node_id: note.node_id,
      }))

  if (noteItems.length > 0) {
    groups.push({ key: 'notes', title: '我的笔记', items: noteItems })
  }

  if (!normalizedQuery && recentArticles.length > 0) {
    groups.push({
      key: 'recent',
      title: '最近访问',
      items: recentArticles.map((article) => ({
        id: `recent:${article.article_id}`,
        label: article.title,
        subtitle: '最近访问',
        kind: 'recent',
        article_id: article.article_id,
      })),
    })
  }

  groups.push({
    key: 'actions',
    title: '操作',
    items: [
      {
        id: 'action:new-source-article',
        label: '新建源文章',
        subtitle: '在当前主题下写一篇可编辑文章',
        kind: 'action',
        action_id: 'new-source-article',
      },
      {
        id: 'action:return-guide',
        label: '回到主题导读',
        subtitle: '回到当前主题的导读文章',
        kind: 'action',
        action_id: 'return-guide',
      },
      {
        id: 'action:open-library',
        label: '打开文章库',
        subtitle: '展开左侧文章列表',
        kind: 'action',
        action_id: 'open-library',
      },
      {
        id: 'action:recent-history',
        label: '查看最近访问',
        subtitle: '查看最近读过的文章',
        kind: 'action',
        action_id: 'recent-history',
      },
    ],
  })

  return groups
}

export function extractWikiLinks(body: string) {
  if (!body) {
    return []
  }

  return Array.from(body.matchAll(WIKI_LINK_RE), (match) => match[1].trim()).filter(Boolean)
}

export function validateWikiLinks(
  body: string,
  conceptCatalog: Array<Pick<Node, 'node_id' | 'name'>>,
) {
  const knownConcepts = new Set(conceptCatalog.map((concept) => concept.name))
  const validLinks: string[] = []
  const invalidLinks: string[] = []

  for (const link of extractWikiLinks(body)) {
    if (knownConcepts.has(link)) {
      validLinks.push(link)
    } else {
      invalidLinks.push(link)
    }
  }

  return {
    valid_links: Array.from(new Set(validLinks)),
    invalid_links: Array.from(new Set(invalidLinks)),
  }
}

export function pickNextArticleRecommendation({
  currentArticle,
  conceptRelations,
  visitedArticleIds,
}: {
  currentArticle: WorkspaceArticle
  conceptRelations: {
    prerequisites?: Array<Pick<Node, 'node_id' | 'name' | 'summary'> & { importance?: number }>
    related?: Array<Pick<Node, 'node_id' | 'name' | 'summary'> & { importance?: number }>
  }
  visitedArticleIds: string[]
}): WorkspaceRecommendation | null {
  const visited = new Set(visitedArticleIds)
  const prerequisite = [...(conceptRelations.prerequisites || [])]
    .sort((left, right) => (right.importance || 0) - (left.importance || 0))
    .find((concept) => !visited.has(`concept:${concept.node_id}`))

  if (prerequisite) {
    return {
      article_id: `concept:${prerequisite.node_id}`,
      title: prerequisite.name,
      reason: `这是当前文章《${currentArticle.title}》最关键的前置概念。`,
      node_id: prerequisite.node_id,
    }
  }

  const related = [...(conceptRelations.related || [])]
    .sort((left, right) => (right.importance || 0) - (left.importance || 0))
    .find((concept) => !visited.has(`concept:${concept.node_id}`))

  if (related) {
    return {
      article_id: `concept:${related.node_id}`,
      title: related.name,
      reason: `这是与《${currentArticle.title}》联系最紧密的延伸阅读。`,
      node_id: related.node_id,
    }
  }

  return null
}

export function buildBacklinksForConcept(
  conceptName: string,
  sourceArticles: SourceArticleRecord[],
): WorkspaceBacklink[] {
  return sourceArticles.flatMap((article) => {
    const paragraphs = article.body.split(/\n\s*\n/)
    const matchIndex = paragraphs.findIndex((paragraph) => (
      paragraph.includes(`[[${conceptName}]]`) || paragraph.includes(conceptName)
    ))

    if (matchIndex === -1) {
      return []
    }

    return [{
      article_id: article.article_id,
      title: article.title,
      anchor_id: `${article.article_id}:paragraph:${matchIndex}`,
      snippet: paragraphs[matchIndex].trim(),
    }]
  })
}
