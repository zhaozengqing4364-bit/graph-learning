import { BookOpenText, FileText, Plus, Sparkles, Layers } from 'lucide-react'

import { Button } from '../../components/ui/button'
import {
  buildArticleLibrarySections,
  type WorkspaceArticle,
  type WorkspaceArticleSection,
} from '../../lib/article-workspace'

interface LegacyLibraryShape {
  guide: WorkspaceArticle[]
  source: WorkspaceArticle[]
  concepts: WorkspaceArticle[]
}

interface ArticleLibrarySidebarProps {
  currentArticleId: string
  library: WorkspaceArticleSection[] | LegacyLibraryShape
  onSelectArticle: (article: WorkspaceArticle) => void
  onCreateSourceArticle: () => void
}

const sectionIcons = {
  guide: BookOpenText,
  source: FileText,
  concept: Sparkles,
} as const

const SectionIconFallback = Layers

function isLegacyLibraryShape(
  library: ArticleLibrarySidebarProps['library'],
): library is LegacyLibraryShape {
  return !Array.isArray(library)
}

function normalizeSections(library: ArticleLibrarySidebarProps['library']) {
  if (!isLegacyLibraryShape(library)) {
    return library
  }

  return buildArticleLibrarySections({
    guide: library.guide[0] || null,
    sourceArticles: library.source || [],
    conceptArticles: library.concepts || [],
  })
}

export function ArticleLibrarySidebar({
  currentArticleId,
  library,
  onSelectArticle,
  onCreateSourceArticle,
}: ArticleLibrarySidebarProps) {
  const sections = normalizeSections(library)

  return (
    <aside className="flex h-full flex-col border-r border-[color:var(--border)] bg-[color:var(--sidebar)]">
      <div className="flex items-center justify-between gap-3 border-b border-[color:var(--border)] px-4 py-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
            文章库
          </p>
          <h2 className="mt-1 text-sm font-medium text-[color:var(--foreground)]">
            阅读路径
          </h2>
        </div>
        <Button variant="outline" size="sm" onClick={onCreateSourceArticle}>
          <Plus className="h-4 w-4" />
          新建
        </Button>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {sections.map((section) => {
          const Icon = sectionIcons[section.key as keyof typeof sectionIcons] ?? SectionIconFallback

          return (
            <section key={section.key} className="space-y-2">
              <div className="flex items-center gap-2 px-2 text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
                <Icon className="h-3.5 w-3.5" />
                {section.title}
              </div>

              <div className="space-y-1">
                {section.articles.map((article) => {
                  const active = article.article_id === currentArticleId

                  return (
                    <button
                      key={article.article_id}
                      type="button"
                      onClick={() => onSelectArticle(article)}
                      className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                        active
                          ? 'border-[color:var(--accent)] bg-[color:var(--accent-soft)] shadow-sm'
                          : 'border-transparent bg-transparent hover:border-[color:var(--border)] hover:bg-[color:var(--card)]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-[color:var(--foreground)]">
                            {article.title}
                          </p>
                          <p className="mt-1 line-clamp-2 text-xs leading-5 text-[color:var(--muted-foreground)]">
                            {article.deck}
                          </p>
                        </div>
                        <span className="shrink-0 text-[10px] uppercase tracking-[0.12em] text-[color:var(--muted-foreground)]">
                          {article.kind === 'guide' ? '导读' : article.kind === 'source' ? '源文' : '专文'}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </section>
          )
        })}
      </div>
    </aside>
  )
}
