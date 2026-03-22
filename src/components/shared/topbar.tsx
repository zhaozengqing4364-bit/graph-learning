import { BookOpen, GitBranch, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useResolvedTopicContext } from '../../hooks'
import { buildLearnRoute } from '../../lib/navigation-context'

export function Topbar() {
  const navigate = useNavigate()
  const { topicId: topicIdToShow, nodeId: currentNodeId, sessionId } = useResolvedTopicContext()

  return (
    <nav className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white bg-opacity-95" aria-label="主导航">
      <div className="flex items-center gap-3 text-sm">
        {topicIdToShow && (
          <>
            <span className="text-gray-400" aria-hidden="true">/</span>
            <button
              onClick={() => navigate(buildLearnRoute(topicIdToShow, { nodeId: currentNodeId, sessionId }))}
              className="flex items-center gap-1.5 text-gray-700 hover:text-indigo-600 transition-colors"
            >
              <BookOpen size={14} className="text-gray-400" />
              <span className="text-xs font-medium truncate max-w-[200px]">学习</span>
            </button>
            <button
              onClick={() => navigate(`/topic/${topicIdToShow}/graph`)}
              className="flex items-center gap-1 text-gray-500 hover:text-indigo-600 transition-colors"
              aria-label="查看图谱"
              title="查看图谱"
            >
              <GitBranch size={14} />
            </button>
          </>
        )}
        {!topicIdToShow && (
          <span className="text-xs text-gray-500">未开始学习</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {topicIdToShow && (
          <button
            onClick={() => navigate('/reviews')}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-amber-600 transition-colors"
            aria-label="复习队列"
            title="复习队列"
          >
            <Clock size={14} />
          </button>
        )}
      </div>
    </nav>
  )
}
