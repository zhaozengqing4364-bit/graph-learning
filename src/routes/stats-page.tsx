import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart3, BookOpen, Brain, Target, TrendingUp,
  AlertTriangle, RefreshCw, Star, Clock, ArrowLeft,
} from 'lucide-react'
import {
  useTopicListQuery, useAbilityOverviewQuery, useReviewListQuery,
  useFrictionsQuery, useExpressionAssetsQuery, useAbilitySnapshotsQuery,
} from '../hooks'
import { Card, LoadingSkeleton, EmptyState, Badge, Button, ErrorState } from '../components/shared'
import { AbilityRadar, AbilityBars } from '../components/shared/ability-radar'
import { ABILITY_DIMENSIONS, type AbilityRecord } from '../types'
import { PRACTICE_TYPE_LABELS } from '../lib/practice-constants'

export function StatsPage() {
  const navigate = useNavigate()
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>('')
  const {
    data: topics,
    isLoading: topicsLoading,
    error: topicsError,
    refetch: refetchTopics,
  } = useTopicListQuery({ limit: 50 })
  const {
    data: reviews,
    error: reviewsError,
    refetch: refetchReviews,
  } = useReviewListQuery({ status: 'pending', limit: 100 })

  const activeTopics = topics?.filter((t) => t.status === 'active') || []
  const [selectedTopicIdx, setSelectedTopicIdx] = useState(0)
  const safeSelectedTopicIdx = activeTopics.length > 0
    ? Math.min(selectedTopicIdx, activeTopics.length - 1)
    : 0
  const activeTopic = activeTopics[safeSelectedTopicIdx] || null
  const { data: abilityOverview } = useAbilityOverviewQuery(activeTopic?.topic_id || '')
  const { data: frictions } = useFrictionsQuery(activeTopic?.topic_id || '', { limit: 20 })
  const { data: expressionAssets } = useExpressionAssetsQuery(activeTopic?.topic_id || '')
  const { data: snapshots } = useAbilitySnapshotsQuery(activeTopic?.topic_id || '')

  if (topicsLoading) {
    return <div className="p-6"><LoadingSkeleton lines={5} /></div>
  }

  if (topicsError && !topics) {
    return (
      <div className="p-6">
        <ErrorState message="无法加载主题列表" onRetry={() => { void refetchTopics() }} />
      </div>
    )
  }

  const filteredAssets = expressionAssets?.filter((a) =>
    !assetTypeFilter || a.expression_type === assetTypeFilter
  ) || []
  const assetTypes = [...new Set(expressionAssets?.map((a) => a.expression_type) || [])]

  const totalNodes = topics?.reduce((s, t) => s + t.total_nodes, 0) || 0
  const totalMastered = topics?.reduce((s, t) => s + t.learned_nodes, 0) || 0
  const dueReviews = reviews?.length || 0
  const totalAssets = expressionAssets?.length || 0
  const favoritedAssets = expressionAssets?.filter((a) => a.favorited).length || 0
  const topDueReviews = [...(reviews ?? [])].sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0)).slice(0, 5)

  // Friction type distribution
  const frictionData = frictions || []
  const frictionTypeCounts: Record<string, number> = {}
  for (const f of frictionData) {
    frictionTypeCounts[f.friction_type] = (frictionTypeCounts[f.friction_type] || 0) + 1
  }

  // Expression asset list for clickable view
  const filteredAssetList = filteredAssets?.slice(0, 5) || []

  if (topicsLoading) {
    return <div className="p-6"><LoadingSkeleton lines={5} /></div>
  }

  if (topicsError || reviewsError) {
    return (
      <div className="p-6">
        <ErrorState
          message="统计数据加载失败"
          onRetry={() => {
            void refetchTopics()
            void refetchReviews()
          }}
        />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <BarChart3 size={24} className="text-indigo-500" />
        学习统计
      </h1>

      {/* Topic selector */}
      {activeTopics.length > 1 && (
        <div className="flex gap-2">
          {activeTopics.map((t, i) => (
            <button
              key={t.topic_id}
              onClick={() => setSelectedTopicIdx(i)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                i === safeSelectedTopicIdx
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {t.title}
            </button>
          ))}
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard
          icon={<BookOpen size={20} className="text-indigo-500" />}
          label="总节点"
          value={totalNodes}
        />
        <StatCard
          icon={<Target size={20} className="text-green-500" />}
          label="已掌握"
          value={totalMastered}
        />
        <StatCard
          icon={<Brain size={20} className="text-purple-500" />}
          label="主题数"
          value={topics?.length || 0}
        />
        <StatCard
          icon={<Star size={20} className="text-rose-500" />}
          label="表达资产"
          value={totalAssets}
        />
        <StatCard
          icon={<RefreshCw size={20} className="text-amber-500" />}
          label="待复习"
          value={dueReviews}
        />
      </div>

      {/* Ability Radar */}
      {abilityOverview && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
              <TrendingUp size={14} className="text-indigo-500" />
              能力雷达
            </h2>
            <div className="flex justify-center">
              <AbilityRadar ability={abilityOverview.ability_averages} size={220} />
            </div>
          </Card>
          <Card>
            <h2 className="text-sm font-semibold text-gray-700 mb-4">能力详情</h2>
            <AbilityBars ability={abilityOverview.ability_averages} />
            {abilityOverview.explain_gap_nodes.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <p className="text-xs font-medium text-amber-600 mb-2 flex items-center gap-1">
                  <AlertTriangle size={12} />
                  解释能力薄弱节点
                </p>
                <div className="space-y-1">
                  {abilityOverview.explain_gap_nodes.map((n) => (
                    <Badge key={n.node_id} variant="warning">{n.name}</Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Ability Trend Chart (simplified bar chart) */}
      {abilityOverview && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-indigo-500" />
            能力分布图
          </h2>
          <AbilityTrendChart ability={abilityOverview.ability_averages} />
        </Card>
      )}

      {/* Ability Timeline (snapshot-based) */}
      {snapshots && snapshots.length > 2 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-green-500" />
            能力变化趋势
          </h2>
          <AbilityTimelineChart snapshots={snapshots} />
        </Card>
      )}

      {/* Weak / Strong Nodes */}
      {abilityOverview && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-red-500" />
              薄弱节点
            </h2>
            {abilityOverview.weak_nodes.length === 0 ? (
              <p className="text-sm text-gray-400">暂无薄弱节点</p>
            ) : (
              <div className="space-y-2">
                {abilityOverview.weak_nodes.map((n) => (
                  <button
                    key={n.node_id}
                    onClick={() => {
                      if (n.node_id && activeTopic) navigate(`/topic/${activeTopic.topic_id}/learn?nodeId=${n.node_id}`)
                    }}
                    className="flex items-center gap-2 p-2 bg-red-50 rounded-lg hover:bg-red-100 transition-colors w-full text-left"
                  >
                    <span className="text-sm text-gray-700">{n.name}</span>
                    <span className="text-xs text-red-500 font-medium ml-auto">{n.avg}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>
          <Card>
            <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              <Target size={14} className="text-green-500" />
              最强节点
            </h2>
            {abilityOverview.strongest_nodes.length === 0 ? (
              <p className="text-sm text-gray-400">继续学习来解锁</p>
            ) : (
              <div className="space-y-2">
                {abilityOverview.strongest_nodes.map((n) => (
                  <button
                    key={n.node_id}
                    onClick={() => {
                      if (n.node_id && activeTopic) navigate(`/topic/${activeTopic.topic_id}/learn?nodeId=${n.node_id}`)
                    }}
                    className="flex items-center gap-2 p-2 bg-green-50 rounded-lg hover:bg-green-100 transition-colors w-full text-left"
                  >
                    <span className="text-sm text-gray-700">{n.name}</span>
                    <span className="text-xs text-green-600 font-medium ml-auto">{n.avg}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Frictions */}
      {frictions && frictions.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <AlertTriangle size={14} className="text-amber-500" />
            近期卡点
          </h2>
          <div className="space-y-2">
            {frictions.slice(0, 10).map((f) => (
              <div key={f.friction_id} className="flex items-start gap-3 p-2 bg-amber-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-700">{f.description}</p>
                  <div className="flex gap-1 mt-1">
                    {f.tags.map((t) => (
                      <Badge key={t} variant="warning" className="text-[10px]">{t}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Friction Distribution */}
      {frictionData && frictionData.length > 0 && Object.keys(frictionTypeCounts).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">卡点类型分布</h3>
          <div className="space-y-2">
            {Object.entries(frictionTypeCounts).map(([type, count]) => {
              const maxCount = Math.max(...Object.values(frictionTypeCounts))
              return (
                <div key={type} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-24 truncate">{type}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                    <div
                      className="bg-indigo-500 h-full rounded-full transition-all"
                      style={{ width: `${(count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600 w-6 text-right">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Expression Assets Summary */}
      {activeTopic && filteredAssets && filteredAssets.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <Star size={14} className="text-yellow-500" />
            表达资产
          </h2>
          <div className="grid grid-cols-2 gap-4 mb-3">
            <StatCard
              icon={<BookOpen size={20} className="text-indigo-500" />}
              label="总保存数"
              value={expressionAssets?.length || 0}
            />
            <StatCard
              icon={<Star size={20} className="text-yellow-500" />}
              label="收藏数"
              value={favoritedAssets}
            />
          </div>

          {/* Type filter chips */}
          {assetTypes.length > 1 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              <button
                onClick={() => setAssetTypeFilter('')}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                  !assetTypeFilter ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                全部
              </button>
              {assetTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => setAssetTypeFilter(assetTypeFilter === type ? '' : type)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                    assetTypeFilter === type ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {PRACTICE_TYPE_LABELS[type] || type}
                </button>
              ))}
            </div>
          )}

          {/* Recent Expression Assets - clickable list */}
          {filteredAssetList.length > 0 && (
            <div className="space-y-2 mt-3 pt-3 border-t border-gray-100">
              <h3 className="text-xs font-medium text-gray-500 mb-2">最近表达资产</h3>
              {filteredAssetList.map((a) => (
                <button
                  key={a.asset_id}
                  onClick={() => navigate(`/topic/${a.topic_id}/learn?nodeId=${a.node_id}`)}
                  className="w-full text-left p-2 bg-gray-50 rounded hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-indigo-600">{a.expression_type}</span>
                    <span className="text-xs text-gray-400">{a.created_at?.slice(0, 10)}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">{a.user_expression}</p>
                </button>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Review Queue Preview */}
      {reviews && reviews.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
              <Clock size={14} className="text-amber-500" />
              待复习队列预览
            </h2>
            <button
              onClick={() => navigate('/reviews')}
              className="text-xs text-indigo-600 hover:text-indigo-700"
            >
              查看全部
            </button>
          </div>
          <div className="space-y-2">
            {topDueReviews.map((r) => (
              <div key={r.review_id} className="flex items-center justify-between p-2 bg-amber-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${r.due_at && new Date(r.due_at) < new Date() ? 'bg-red-500' : r.due_at ? 'bg-amber-400' : 'bg-gray-300'}`} />
                  <span className="text-sm text-gray-700">{r.node_name ?? r.node_id}</span>
                </div>
                <span className="text-xs text-gray-400">优先级 {r.priority}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Back to Learning */}
      <div className="flex justify-center pb-8">
        <Button onClick={() => navigate('/')}>
          <ArrowLeft size={16} />
          返回学习
        </Button>
      </div>

      {/* No data state */}
      {!topicsLoading && (!topics || topics.length === 0) && (
        <EmptyState
          icon={<BarChart3 size={48} />}
          title="暂无学习数据"
          description="完成一些学习后，这里会展示你的能力分析"
          action={
            <Button onClick={() => navigate('/')}>
              <BookOpen size={16} />
              创建第一个学习主题
            </Button>
          }
        />
      )}
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </Card>
  )
}

export function AbilityTrendChart({ ability }: { ability: AbilityRecord | null }) {
  if (!ability) {
    return <div className="py-8 text-center text-sm text-gray-400">暂无能力数据</div>
  }

  const dims = ABILITY_DIMENSIONS
  const maxVal = Math.max(...dims.map((d) => ability[d.key] || 0), 10)
  const barW = 32
  const gap = 16
  const chartH = 120
  const chartW = dims.length * (barW + gap) - gap

  return (
    <div className="overflow-auto">
      <svg width={chartW} height={chartH + 30} className="mx-auto">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((v) => {
          const y = chartH - (v / maxVal) * chartH
          return (
            <g key={v}>
              <line x1={0} y1={y} x2={chartW} y2={y} stroke="#e2e8f0" strokeWidth="0.5" />
              <text x={-4} y={y + 3} textAnchor="end" className="text-[8px] fill-gray-400">{v}</text>
            </g>
          )
        })}
        {/* Bars */}
        {dims.map((d, i) => {
          const val = ability[d.key] || 0
          const h = (val / maxVal) * chartH
          const x = i * (barW + gap)
          const y = chartH - h
          const color = val >= 70 ? '#22c55e' : val >= 40 ? '#6366f1' : '#f59e0b'
          return (
            <g key={d.key}>
              <rect x={x} y={y} width={barW} height={h} rx={4} fill={color} opacity={0.85} />
              <text x={x + barW / 2} y={y - 4} textAnchor="middle" className="text-[10px] font-medium fill-gray-700">{val}</text>
              <text x={x + barW / 2} y={chartH + 16} textAnchor="middle" className="text-[9px] fill-gray-500">{d.label}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function AbilityTimelineChart({ snapshots }: { snapshots: { created_at: string; understand: number; example: number; contrast: number; apply: number; explain: number; recall: number; transfer: number; teach: number }[] }) {
  // Show last 20 snapshots as a mini sparkline
  const recent = snapshots.slice(-20)
  const chartH = 60
  const chartW = recent.length * 8 + 20
  const allDims = ['understand', 'example', 'contrast', 'apply', 'explain', 'recall', 'transfer', 'teach'] as const
  const maxVal = Math.max(...recent.map((s) => Math.max(...allDims.map((d) => s[d] || 0))), 10)

  const DIM_LABELS: Record<string, string> = { understand: '理解', example: '举例', contrast: '对比', apply: '应用', explain: '解释', recall: '回忆', transfer: '迁移', teach: '教学' }
  const DIM_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#06b6d4']

  return (
    <div className="overflow-auto">
      <div className="flex items-center gap-3 mb-2 flex-wrap">
        {allDims.map((dim, i) => (
          <div key={dim} className="flex items-center gap-1.5">
            <div className="w-3 h-1 rounded" style={{ background: DIM_COLORS[i] }} />
            <span className="text-[10px] text-gray-500">{DIM_LABELS[dim]}</span>
          </div>
        ))}
      </div>
      <svg width={chartW} height={chartH + 20} className="mx-auto">
        {/* Baseline */}
        <line x1={10} y1={chartH} x2={chartW} y2={chartH} stroke="#e2e8f0" strokeWidth="0.5" />
        {/* Trend lines */}
        {allDims.map((dim, i) => {
          const points = recent.map((s, j) => `${10 + j * 8},${chartH - ((s[dim] || 0) / maxVal) * chartH}`)
          return (
            <polyline
              key={dim}
              points={points.join(' ')}
              fill="none"
              stroke={DIM_COLORS[i]}
              strokeWidth={1.5}
              opacity={0.7}
            />
          )
        })}
        {/* Time labels */}
        <text x={10} y={chartH + 14} className="text-[8px] fill-gray-400">
          {recent[0]?.created_at?.slice(5, 10)}
        </text>
        <text x={chartW - 10} y={chartH + 14} textAnchor="end" className="text-[8px] fill-gray-400">
          {recent[recent.length - 1]?.created_at?.slice(5, 10)}
        </text>
      </svg>
    </div>
  )
}
