import { useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Trophy,
  BookOpen,
  Star,
  ArrowRight,
  ChevronRight,
  Home,
  CheckCircle,
  RefreshCw,
  GitBranch,
  BarChart3,
  AlertTriangle,
  X,
  BookmarkPlus,
} from 'lucide-react'

import { Card, Button, Badge, LoadingSkeleton, ErrorState } from '../components/shared'
import { useSessionSummaryQuery } from '../hooks'
import { buildLearnRoute } from '../lib/navigation-context'
import { buildSummaryPresentation } from '../lib/summary-display'
import type { CompleteSessionResponse } from '../types'

interface SummaryPayload {
  session_id?: string
  topic_id?: string
  status?: string
  summary?: string
  synthesis?: Partial<CompleteSessionResponse['synthesis']>
  partial_summary?: boolean
}

interface LocationState {
  summary?: SummaryPayload
}

export function SummaryPage() {
  const [dismissedPartial, setDismissedPartial] = useState(false)
  const { topicId } = useParams<{ topicId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const state = location.state as LocationState | null
  const sessionId = searchParams.get('sessionId')
  const {
    data: sessionSummary,
    isLoading,
    error,
    refetch,
  } = useSessionSummaryQuery(topicId || '', !state?.summary ? sessionId : null)

  const summary = state?.summary || sessionSummary || null
  const presentation = summary ? buildSummaryPresentation(summary) : null

  if (!state?.summary && sessionId && isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <LoadingSkeleton lines={5} />
        </Card>
      </div>
    )
  }

  if (!state?.summary && sessionId && error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorState
          message="总结数据加载失败"
          onRetry={() => { void refetch() }}
        />
      </div>
    )
  }

  if (!summary || !presentation) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card className="text-center py-12">
          <BookOpen size={40} className="text-gray-300 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">没有找到本轮总结</h2>
          <p className="text-sm text-gray-500 mb-4">请通过正常学习流程完成本轮后查看</p>
          <div className="flex flex-wrap gap-3 justify-center">
            <Button onClick={() => navigate('/')}>
              <Home size={16} />
              返回首页
            </Button>
            <Button variant="outline" onClick={() => navigate('/reviews')}>
              <RefreshCw size={16} />
              前往复习
            </Button>
            <Button variant="ghost" onClick={() => navigate(`/topic/${topicId}/graph`)}>
              <GitBranch size={16} />
              查看图谱
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Trophy size={24} className="text-amber-500" />
        <h1 className="text-xl font-bold text-gray-900">本轮学习完成</h1>
      </div>

      {summary.partial_summary && !dismissedPartial ? (
        <Card className="border border-amber-200 bg-amber-50">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600" />
            <div className="flex-1 space-y-1">
              <p className="text-sm font-medium text-amber-800">仅恢复了本轮摘要，详细收束信息暂不可用</p>
              <p className="text-sm text-amber-700">推荐节点、复盘建议和统计卡片都已隐藏，避免伪精确展示。</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => navigate(buildLearnRoute(topicId || '', { sessionId }))}
              >
                <RefreshCw size={14} />
                返回学习页重新完成会话
              </Button>
            </div>
            <button
              type="button"
              onClick={() => setDismissedPartial(true)}
              className="shrink-0 text-amber-400 hover:text-amber-600 transition"
              aria-label="关闭提示"
            >
              <X size={16} />
            </button>
          </div>
        </Card>
      ) : null}

      <Card className="border-l-4 border-l-amber-500">
        <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
          <Star size={14} className="text-amber-500" />
          收束总结
        </h2>
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{presentation.sessionSummary}</p>
      </Card>

      {presentation.keyTakeaways.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <BookOpen size={14} className="text-indigo-500" />
            本轮新增关键节点
          </h3>
          <div className="space-y-2">
            {presentation.keyTakeaways.map((takeaway, index) => (
              <div key={`${takeaway}-${index}`} className="flex items-start gap-2 text-sm text-gray-700">
                <CheckCircle size={14} className="text-indigo-500 mt-0.5 shrink-0" />
                <span>{takeaway}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {presentation.coveredScope && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <GitBranch size={14} className="text-indigo-500" />
            已覆盖范围
          </h3>
          <p className="text-sm text-gray-600 mb-2">{presentation.coveredScope}</p>
          {presentation.skippableNodes.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-gray-500 mb-1">暂时可以略过的部分</p>
              <div className="flex flex-wrap gap-1.5">
                {presentation.skippableNodes.map((node, index) => (
                  <Badge key={`${node}-${index}`} variant="default" className="text-[10px]">
                    {node}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {presentation.hasDetailedSynthesis && (
        <>
          <Card>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              <BookOpen size={14} className="text-indigo-500" />
              本轮统计
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-indigo-600">{presentation.newAssetsCount}</p>
                <p className="text-xs text-gray-600 mt-1">新增表达资产</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-amber-600">{presentation.reviewItemsCreated}</p>
                <p className="text-xs text-gray-600 mt-1">新增复习任务</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-indigo-600">{presentation.nextRecommendations.length}</p>
                <p className="text-xs text-gray-600 mt-1">推荐下一步节点</p>
              </div>
            </div>
          </Card>
        </>
      )}

      {presentation.assetHighlights.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <BookmarkPlus size={14} className="text-indigo-500" />
            本轮表达资产亮点
          </h3>
          <div className="space-y-2">
            {presentation.assetHighlights.map((asset, index) => (
              <div key={`${asset.node_id}-${asset.practice_type}-${index}`} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <Badge variant="info" className="text-[10px]">{asset.practice_type}</Badge>
                  <span className="text-sm text-gray-700">{asset.node_id}</span>
                </div>
                {asset.correctness != null && (
                  <span className={`text-xs font-medium ${asset.correctness >= 0.7 ? 'text-green-600' : asset.correctness >= 0.4 ? 'text-amber-600' : 'text-red-500'}`}>
                    {(asset.correctness * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            ))}
          </div>
          <button
            onClick={() => navigate(`/topic/${topicId}/assets`)}
            className="mt-3 flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
          >
            <ArrowRight size={12} />
            查看全部资产
          </button>
        </Card>
      )}

      {presentation.nextRecommendations.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <ArrowRight size={14} className="text-indigo-500" />
            下一步建议
          </h3>
          <div className="space-y-2">
            {presentation.nextRecommendations.map((node) => (
              <button
                key={node.node_id}
                onClick={() => navigate(buildLearnRoute(topicId || '', { nodeId: node.node_id, sessionId }))}
                className="flex items-center gap-2 w-full text-left p-3 rounded-lg hover:bg-indigo-50 transition-colors group"
              >
                <ChevronRight size={14} className="text-gray-400 group-hover:text-indigo-500" />
                <div>
                  <span className="text-sm font-medium text-gray-700 group-hover:text-indigo-700">{node.name}</span>
                  <p className="text-xs text-gray-500 mt-0.5">{node.summary}</p>
                </div>
              </button>
            ))}
          </div>
        </Card>
      )}

      {presentation.reviewCandidates.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <CheckCircle size={14} className="text-amber-500" />
            复习候选 ({presentation.reviewCandidates.length})
          </h3>
          <div className="space-y-2">
            {presentation.reviewCandidates.map((item) => (
              <button
                key={`${item.review_id}-${item.node_id}`}
                type="button"
                onClick={() => navigate('/reviews')}
                className="flex w-full items-center justify-between p-3 bg-amber-50 rounded-lg hover:bg-amber-100 transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  <Badge variant="warning">{item.node_name || item.node_id}</Badge>
                  <span className="text-xs text-gray-600">{item.reason}</span>
                </div>
                <span className="text-xs text-amber-600 shrink-0">去复习 &rarr;</span>
              </button>
            ))}
          </div>
        </Card>
      )}

      <div className="flex flex-col gap-3 pb-8 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => navigate('/')}>
            <Home size={16} />
            返回首页
          </Button>
          <Button variant="outline" onClick={() => navigate(buildLearnRoute(topicId || '', { sessionId }))}>
            <BookOpen size={16} />
            结束会话，继续学习
          </Button>
        </div>
        <div className="flex flex-wrap gap-3">
          {presentation.reviewCandidates.length > 0 && (
            <Button variant="secondary" onClick={() => navigate('/reviews')}>
              <RefreshCw size={16} />
              前往复习
            </Button>
          )}
          <Button variant="ghost" onClick={() => navigate(`/topic/${topicId}/graph`)}>
            <GitBranch size={16} />
            查看图谱
          </Button>
          <Button variant="ghost" onClick={() => navigate('/stats')}>
            <BarChart3 size={16} />
            查看统计
          </Button>
          {presentation.nextRecommendations.length > 0 && (
            <Button onClick={() => navigate(buildLearnRoute(topicId || '', { nodeId: presentation.nextRecommendations[0].node_id, sessionId }))}>
              <BookOpen size={16} />
              继续学习
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
