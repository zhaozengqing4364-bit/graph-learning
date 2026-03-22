import { BookMarked, FilePenLine, Sparkles } from 'lucide-react'

import type { WorkspaceArticle } from '../../lib/article-workspace'

type ArticleHeaderArticle = Partial<WorkspaceArticle> & {
  id?: string
  title: string
  kind: WorkspaceArticle['kind']
  topic_id: string
  updated_at: string
  description?: string
}

interface ArticleHeaderProps {
  article: ArticleHeaderArticle
  sourceLabel: string
  statusLabel?: string
}

const articleIcons = {
  guide: BookMarked,
  source: FilePenLine,
  concept: Sparkles,
} as const

function formatDate(value: string) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function ArticleHeader({
  article,
  sourceLabel,
  statusLabel,
}: ArticleHeaderProps) {
  const Icon = articleIcons[article.kind] || BookMarked

  return (
    <header className="space-y-5 border-b border-[color:var(--border)] pb-8">
      <div className="flex flex-wrap items-start gap-2 text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)] sm:items-center">
        <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-2.5 py-1 shadow-sm">
          <Icon className="h-3.5 w-3.5" />
          {sourceLabel}
        </span>
        {statusLabel ? (
          <span className="inline-flex items-center rounded-full border border-[color:var(--border)] px-2.5 py-1 text-[color:var(--foreground)]">
            {statusLabel}
          </span>
        ) : null}
        <span>{formatDate(article.updated_at)}</span>
      </div>

      <div className="space-y-3">
        <h1 className="font-serif text-3xl leading-tight text-[color:var(--foreground)] sm:text-4xl">
          {article.title}
        </h1>
        {article.description ? (
          <p className="max-w-2xl text-sm leading-7 text-[color:var(--muted-foreground)] sm:text-base">
            {article.description}
          </p>
        ) : null}
      </div>
    </header>
  )
}
