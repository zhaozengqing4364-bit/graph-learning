import { Clock } from 'lucide-react'
import { ArticleWorkspacePage } from '../features/article-workspace/article-workspace-page'
import { useInactivityWarning } from '../lib/session-timer'

export function LearningPage() {
  const isIdle = useInactivityWarning()

  return (
    <div className="relative">
      <ArticleWorkspacePage />
      {isIdle && (
        <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-4 py-2.5 text-sm text-amber-700 shadow-lg animate-pulse">
          <Clock size={14} />
          已超过 30 分钟未操作
        </div>
      )}
    </div>
  )
}
