import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Star, Search, BookOpen, ChevronRight, PenTool } from 'lucide-react'
import { useExpressionAssetsQuery, useToggleFavoriteMutation, useTopicQuery } from '../hooks'
import { Card, Badge, LoadingSkeleton, EmptyState, ErrorState, Button, Tabs } from '../components/shared'
import { useToast } from '../components/ui/toast'
import type { PracticeType } from '../types'
import { buildPracticeRoute } from '../lib/navigation-context'

const PRACTICE_TYPE_LABELS: Record<string, string> = {
  define: '定义',
  example: '举例',
  contrast: '对比',
  apply: '应用',
  teach_beginner: '教学',
  compress: '压缩',
  explain: '解释',
}

export function AssetsPage() {
  const { topicId } = useParams<{ topicId: string }>()
  const navigate = useNavigate()
  const [filterType, setFilterType] = useState<string>('all')
  const [showFavoritedOnly, setShowFavoritedOnly] = useState(false)
  const [searchText, setSearchText] = useState('')
  const { data: topic } = useTopicQuery(topicId || '')

  const { data: assets, isLoading, error, refetch } = useExpressionAssetsQuery(topicId!, {
    expression_type: filterType !== 'all' ? (filterType as PracticeType) : undefined,
    favorited: showFavoritedOnly || undefined,
    limit: 100,
  })

  const toggleFavorite = useToggleFavoriteMutation(topicId!)
  const toast = useToast()

  const filteredAssets = assets
    ? assets.filter((a) => {
        if (!searchText) return true
        const q = searchText.toLowerCase()
        return (
          (a.user_expression || '').toLowerCase().includes(q) ||
          (a.ai_rewrite || '').toLowerCase().includes(q) ||
          a.expression_type.toLowerCase().includes(q)
        )
      })
    : []

  const favoriteCount = assets?.filter((a) => a.favorited).length ?? 0
  const practiceNodeId = topic?.current_node_id || topic?.entry_node_id || null

  const tabs = [
    { key: 'all', label: '全部', count: assets?.length ?? 0 },
    { key: 'define', label: '定义', count: assets?.filter((a) => a.expression_type === 'define').length ?? 0 },
    { key: 'example', label: '举例', count: assets?.filter((a) => a.expression_type === 'example').length ?? 0 },
    { key: 'contrast', label: '对比', count: assets?.filter((a) => a.expression_type === 'contrast').length ?? 0 },
    { key: 'apply', label: '应用', count: assets?.filter((a) => a.expression_type === 'apply').length ?? 0 },
    { key: 'teach_beginner', label: '教学', count: assets?.filter((a) => a.expression_type === 'teach_beginner').length ?? 0 },
  ]

  if (isLoading) {
    return <div className="p-6"><LoadingSkeleton lines={5} /></div>
  }

  if (error) {
    return (
      <div className="p-6">
        <ErrorState message="无法获取表达资产列表" onRetry={() => { void refetch() }} />
      </div>
    )
  }

  if (!assets || assets.length === 0) {
    const emptyActionRoute = topicId ? buildPracticeRoute(topicId, practiceNodeId) : '/'
    const emptyActionLabel = practiceNodeId ? '前往练习' : '返回学习'

    return (
      <div className="p-6">
        <EmptyState
          icon={<BookOpen size={48} />}
          title="暂无表达资产"
          description="完成练习并保存表达后，资产会出现在这里"
          action={
            <Button onClick={() => navigate(emptyActionRoute)}>
              {emptyActionLabel}
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-gray-900">表达资产</h1>
          <p className="text-xs text-gray-500 mt-0.5">{assets.length} 条资产 / {favoriteCount} 收藏</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFavoritedOnly(!showFavoritedOnly)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              showFavoritedOnly
                ? 'bg-amber-100 text-amber-700 border border-amber-200'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            <Star size={12} className={showFavoritedOnly ? 'fill-amber-500 text-amber-500' : ''} />
            收藏
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="搜索表达内容..."
          autoComplete="off"
          className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </div>

      {/* Type Tabs */}
      <Tabs items={tabs} activeKey={filterType} onChange={setFilterType} />

      {/* Asset List */}
      <div className="space-y-3">
        {filteredAssets.map((asset) => (
          <Card key={asset.asset_id} className="group hover:border-indigo-200 transition-colors">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="info" className="text-[10px]">
                    {PRACTICE_TYPE_LABELS[asset.expression_type] || asset.expression_type}
                  </Badge>
                  {(asset.quality_tags?.length ?? 0) > 0 && (
                    <div className="flex gap-1">
                      {asset.quality_tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="text-[10px] text-gray-400">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-sm text-gray-800 leading-relaxed mb-1">
                  {asset.user_expression || '（空）'}
                </p>
                {asset.ai_rewrite && (
                  <div className="bg-indigo-50 rounded-md p-2 mt-2">
                    <p className="text-xs text-indigo-700 leading-relaxed">{asset.ai_rewrite}</p>
                  </div>
                )}
                {asset.skeleton && (
                  <p className="text-xs text-gray-400 mt-1 italic">
                    骨架：{asset.skeleton}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => navigate(buildPracticeRoute(topicId!, asset.node_id))}
                    className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
                  >
                    <PenTool size={12} />
                    再练一次
                  </button>
                  <button
                    onClick={() => navigate(`/topic/${topicId}/learn?nodeId=${asset.node_id}`)}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors"
                  >
                    <ChevronRight size={12} />
                    查看节点
                  </button>
                  <span className="text-[10px] text-gray-300">{asset.created_at?.slice(0, 10)}</span>
                </div>
              </div>
              <button
                onClick={() => {
                  const wasFav = asset.favorited
                  toggleFavorite.mutate(asset.asset_id, {
                    onSuccess: () => toast({ message: wasFav ? '已取消收藏' : '已收藏', type: 'success' }),
                    onError: () => toast({ message: '操作失败', type: 'error' }),
                  })
                }}
                className="flex-shrink-0 p-1 rounded hover:bg-gray-100 transition-colors"
                aria-label={asset.favorited ? '取消收藏' : '收藏'}
                title={asset.favorited ? '取消收藏' : '收藏'}
              >
                <Star
                  size={16}
                  className={
                    asset.favorited
                      ? 'fill-amber-400 text-amber-400'
                      : 'text-gray-300 hover:text-amber-400'
                  }
                />
              </button>
            </div>
          </Card>
        ))}

        {filteredAssets.length === 0 && searchText && (
          <div className="text-center py-8 text-sm text-gray-400">
            没有匹配 "{searchText}" 的资产
          </div>
        )}
      </div>
    </div>
  )
}
