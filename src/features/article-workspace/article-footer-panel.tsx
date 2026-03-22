import { ArrowRight, Network } from 'lucide-react'

import type { WorkspaceRecommendation } from '../../lib/article-workspace'
import { Button } from '../../components/ui/button'

export interface KnowledgeMapItem {
  name: string
  node_id?: string
}

export interface KnowledgeMapGroup {
  title: string
  items: KnowledgeMapItem[]
}

interface ArticleFooterPanelProps {
  recommendation: WorkspaceRecommendation | null
  knowledgeMap: KnowledgeMapGroup[]
  onOpenArticle: (articleId: string) => void
}

export function ArticleFooterPanel({
  recommendation,
  knowledgeMap,
  onOpenArticle,
}: ArticleFooterPanelProps) {
  return (
    <section className="space-y-6 border-t border-[color:var(--border)] pt-8">
      {recommendation ? (
        <div className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--card)] p-5 shadow-sm">
          <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
            继续阅读
          </p>
          <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="space-y-2">
              <h3 className="font-serif text-2xl text-[color:var(--foreground)]">
                继续下一篇：{recommendation.title}
              </h3>
              <p className="max-w-2xl text-sm leading-6 text-[color:var(--muted-foreground)]">
                {recommendation.reason}
              </p>
            </div>

            <Button onClick={() => onOpenArticle(recommendation.article_id)}>
              打开文章
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}

      {knowledgeMap.length > 0 && (
      <div className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--card)] p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-[color:var(--accent)]" />
          <h3 className="font-serif text-2xl text-[color:var(--foreground)]">
            知识地图
          </h3>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {knowledgeMap.map((group) => (
            <div
              key={group.title}
              className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--background)] p-4"
            >
              <p className="text-xs uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
                {group.title}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {group.items.map((item) => (
                  item.node_id ? (
                    <button
                      key={`${group.title}:${item.name}`}
                      type="button"
                      className="rounded-full border border-[color:var(--border)] bg-transparent px-2.5 py-1 text-xs text-[color:var(--foreground)] hover:bg-[color:var(--accent-soft)] transition-colors cursor-pointer"
                      onClick={() => onOpenArticle(`concept:${item.node_id}`)}
                    >
                      {item.name}
                    </button>
                  ) : (
                    <span
                      key={`${group.title}:${item.name}`}
                      className="rounded-full border border-[color:var(--border)] px-2.5 py-1 text-xs text-[color:var(--foreground)]"
                    >
                      {item.name}
                    </span>
                  )
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      )}
    </section>
  )
}
