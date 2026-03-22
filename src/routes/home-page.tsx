import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, BookOpen, ArrowRight, Clock, AlertTriangle, PlayCircle, RefreshCw, Trash2, Archive } from 'lucide-react'
import { useTopicListQuery, useCreateTopicMutation, useReviewListQuery, useSystemCapabilitiesQuery, useDeferredNodesQuery, usePracticeAttemptsQuery, useArchiveTopicMutation, useDeleteTopicMutation, useSettingsQuery } from '../hooks'
import { Card, Button, EmptyState, LoadingSkeleton, Badge, ErrorState, Progress } from '../components/shared'
import { useToast } from '../components/ui/toast'
import { ConfirmDialog } from '../components/ui/confirm-dialog'
import type { SourceType, LearningIntent, TopicMode } from '../types'
import { sortTopicsByUpdatedAtDesc } from '../lib/navigation-context'

export function HomePage() {
  const navigate = useNavigate()
  const {
    data: topics,
    isLoading: topicsLoading,
    error: topicsError,
    refetch: refetchTopics,
  } = useTopicListQuery({ limit: 10 })
  const {
    data: reviews,
    error: reviewsError,
    refetch: refetchReviews,
  } = useReviewListQuery({ status: 'pending', limit: 5 })
  const { data: settings } = useSettingsQuery()
  const { data: capabilities } = useSystemCapabilitiesQuery()
  const createTopicMutation = useCreateTopicMutation()
  const archiveTopicMutation = useArchiveTopicMutation()
  const deleteTopicMutation = useDeleteTopicMutation()
  const toast = useToast()

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [sourceType, setSourceType] = useState<SourceType>('article')
  const [learningIntent, setLearningIntent] = useState<LearningIntent | null>(null)
  const [mode, setMode] = useState<TopicMode | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const resolvedLearningIntent = learningIntent || settings?.default_learning_intent || 'build_system'
  const resolvedMode = mode || settings?.default_mode || 'full_system'

  const handleCreate = async () => {
    if (!title.trim() || !content.trim()) return
    try {
      const res = await createTopicMutation.mutateAsync({
        title: title.trim(),
        source_type: sourceType,
        source_content: content.trim(),
        learning_intent: resolvedLearningIntent,
        mode: resolvedMode,
      })
      navigate(`/topic/${res.topic_id}/learn${res.fallback_used ? '?fallback=true' : ''}`)
      toast({ message: res.fallback_used ? '主题创建成功（AI 降级模式）' : '主题创建成功', type: 'success' })
    } catch {
      toast({ message: '创建失败，请检查输入后重试', type: 'error' })
    }
  }

  const recentTopics = useMemo(
    () => sortTopicsByUpdatedAtDesc((topics || []).filter((topic) => topic.status === 'active')),
    [topics],
  )
  const dueReviewCount = reviews?.length ?? 0
  const currentTopicId = recentTopics.length > 0 ? recentTopics[0].topic_id : null

  const { data: deferredData } = useDeferredNodesQuery(currentTopicId)
  const deferredNodes = deferredData || []
  const { data: recentPractices } = usePracticeAttemptsQuery(currentTopicId, { limit: 5 })

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      {/* OpenAI Warning Banner */}
      {capabilities && capabilities.ai_provider === null && (
        <div className="flex items-center gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle size={16} className="text-amber-600 shrink-0" />
          <p className="text-sm text-amber-700">
            未配置 OpenAI API Key，AI 功能将使用降级模式
          </p>
        </div>
      )}

      {/* Hero: New Topic */}
      <section>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">开始学习</h1>
        <p className="text-sm text-gray-600 mb-5">输入概念、问题或文章，构建你的知识图谱</p>

        <Card>
          <div className="space-y-4">
            <div>
              <label htmlFor="new-topic-title" className="block text-sm font-medium text-gray-700 mb-1">主题标题</label>
              <input
                id="new-topic-title"
                name="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="例如: Transformer 架构学习"
                maxLength={200}
                autoComplete="off"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label htmlFor="new-topic-content" className="block text-sm font-medium text-gray-700 mb-1">内容</label>
              <textarea
                id="new-topic-content"
                name="content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onInput={(e) => {
                  e.currentTarget.style.height = 'auto'
                  e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`
                }}
                placeholder="粘贴文章、笔记，或描述你想学习的概念..."
                rows={4}
                maxLength={500000}
                autoComplete="off"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              />
            </div>
            <div className="flex flex-wrap gap-4">
              <div>
                <label htmlFor="new-topic-source-type" className="block text-xs text-gray-600 mb-1">类型</label>
                <select
                  id="new-topic-source-type"
                  name="source_type"
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value as SourceType)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="article">文章</option>
                  <option value="concept">概念</option>
                  <option value="question">问题</option>
                  <option value="notes">笔记</option>
                  <option value="mixed">混合</option>
                </select>
              </div>
              <div>
                <label htmlFor="new-topic-learning-intent" className="block text-xs text-gray-600 mb-1">学习意图</label>
                <select
                  id="new-topic-learning-intent"
                  name="learning_intent"
                  value={resolvedLearningIntent}
                  onChange={(e) => setLearningIntent(e.target.value as LearningIntent)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="build_system">构建体系</option>
                  <option value="fix_gap">弥补短板</option>
                  <option value="solve_task">解决任务</option>
                  <option value="prepare_expression">准备表达</option>
                  <option value="prepare_interview">面试准备</option>
                </select>
              </div>
              <div>
                <label htmlFor="new-topic-mode" className="block text-xs text-gray-600 mb-1">模式</label>
                <select
                  id="new-topic-mode"
                  name="mode"
                  value={resolvedMode}
                  onChange={(e) => setMode(e.target.value as TopicMode)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="full_system">完整体系</option>
                  <option value="shortest_path">最短路径</option>
                </select>
              </div>
            </div>
            <Button
              onClick={handleCreate}
              loading={createTopicMutation.isPending}
              disabled={!title.trim() || !content.trim()}
            >
              <Plus size={16} />
              创建学习主题
            </Button>
            {createTopicMutation.isPending && (
              <p className="mt-2 text-xs text-muted-foreground animate-pulse">
                AI 正在分析内容并生成知识图谱，通常需要 10-30 秒...
              </p>
            )}
          </div>
        </Card>
      </section>

      {/* Recent Topics */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">最近学习</h2>
          {dueReviewCount > 0 && (
            <button
              onClick={() => navigate('/reviews')}
              className="flex items-center gap-1 text-sm text-amber-600 hover:text-amber-700"
            >
              <Clock size={14} />
              {dueReviewCount} 项待复习
            </button>
          )}
        </div>

        {topicsLoading ? (
          <LoadingSkeleton lines={3} />
        ) : topicsError ? (
          <ErrorState
            title="最近学习加载失败"
            message={topicsError instanceof Error ? topicsError.message : '无法获取学习主题列表'}
            onRetry={() => { void refetchTopics() }}
          />
        ) : recentTopics.length === 0 ? (
          <EmptyState
            title="还没有学习主题"
            description="输入内容开始你的第一个学习主题"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recentTopics.map((topic) => (
              <Card
                key={topic.topic_id}
                className="cursor-pointer hover:border-indigo-300 transition-colors group"
              >
                <div className="flex items-start justify-between">
                    <div
                      className="flex-1 min-w-0"
                      role="button"
                      tabIndex={0}
                      onClick={() => navigate(`/topic/${topic.topic_id}/learn`)}
                      onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/topic/${topic.topic_id}/learn`) }}
                    >
                    <div className="flex items-center gap-2 mb-1">
                      <BookOpen size={14} className="text-indigo-500 shrink-0" />
                      <h3 className="text-sm font-medium text-gray-900 truncate">{topic.title}</h3>
                    </div>
                    {topic.total_nodes > 0 ? (
                      <>
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <span>{topic.learned_nodes}/{topic.total_nodes} 已掌握</span>
                        </div>
                        <Progress value={topic.learned_nodes} max={topic.total_nodes} className="mt-1" />
                      </>
                    ) : (
                      <p className="text-xs text-gray-400">尚未展开节点</p>
                    )}
                  </div>
                  <button
                    onClick={() => navigate(`/topic/${topic.topic_id}/learn`)}
                    className="opacity-0 group-hover:opacity-100 text-indigo-600 hover:text-indigo-700 transition-opacity"
                    aria-label={`继续学习 ${topic.title}`}
                  >
                    <ArrowRight size={16} />
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Badge variant="info">{{ build_system: '构建体系', fix_gap: '弥补短板', solve_task: '解决问题', prepare_expression: '表达训练', prepare_interview: '面试准备' }[topic.learning_intent as keyof Record<string, string>] || topic.learning_intent}</Badge>
                  {topic.due_review_count > 0 && <Badge variant="warning">{topic.due_review_count} 复习</Badge>}
                  {topic.deferred_count > 0 && <Badge variant="warning">{topic.deferred_count} 待学</Badge>}
                  <div className="flex-1" />
                  <button
                    onClick={(e) => { e.stopPropagation(); toast({ message: '正在归档...', type: 'info' }); archiveTopicMutation.mutate(topic.topic_id, { onSuccess: () => toast({ message: '已归档', type: 'success' }), onError: () => toast({ message: '归档失败', type: 'error' }) }) }}
                    className="p-1 text-gray-300 hover:text-amber-500 transition-colors"
                    title="归档"
                    aria-label={`归档主题 ${topic.title}`}
                  >
                    <Archive size={14} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(topic.topic_id) }}
                    className="p-1 text-gray-300 hover:text-red-500 transition-colors"
                    title="删除"
                    aria-label={`删除主题 ${topic.title}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Continue Learning Panel */}
      {recentTopics.length > 0 && (
        <section>
          <Card className="bg-indigo-50 border-indigo-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <PlayCircle size={24} className="text-indigo-600" />
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">继续学习</h2>
                  <p className="text-xs text-gray-600">{recentTopics[0].title}</p>
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => navigate(`/topic/${recentTopics[0].topic_id}/learn`)}
              >
                <ArrowRight size={14} />
                继续
              </Button>
            </div>
          </Card>
        </section>
      )}

      {/* Pending Review Panel */}
      {reviewsError ? (
        <section>
          <Card className="bg-amber-50 border-amber-200">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">待复习加载失败</h2>
                <p className="text-xs text-gray-500 mt-1">暂时无法获取复习队列</p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => { void refetchReviews() }}
              >
                <RefreshCw size={14} />
                重试
              </Button>
            </div>
          </Card>
        </section>
      ) : dueReviewCount > 0 && (
        <section>
          <Card className="bg-amber-50 border-amber-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RefreshCw size={24} className="text-amber-600" />
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">待复习</h2>
                  <p className="text-xs text-gray-600">你有 {dueReviewCount} 项复习任务到期</p>
                </div>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => navigate('/reviews')}
              >
                <Clock size={14} />
                前往复习
              </Button>
            </div>
          </Card>
        </section>
      )}

      {/* Deferred Nodes Panel */}
      {deferredNodes && deferredNodes.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">待学堆栈</h3>
          <div className="space-y-2">
            {deferredNodes.slice(0, 5).map((d) => (
              <button
                key={d.node_id}
                onClick={() => currentTopicId && navigate(`/topic/${currentTopicId}/learn?nodeId=${d.node_id}`)}
                className="w-full flex items-center justify-between text-sm text-left hover:bg-gray-50 rounded px-1 py-0.5 transition-colors"
              >
                <span className="text-gray-600 truncate">{d.node_name || d.node_id}</span>
                <span className="text-xs text-gray-500 shrink-0 ml-2">{d.reason || ''}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Recent Practice Panel */}
      {recentPractices && recentPractices.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">最近表达练习</h3>
          <div className="space-y-2">
            {recentPractices.slice(0, 5).map((p) => (
              <div key={p.attempt_id || p.practice_type} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs text-gray-500 shrink-0">{p.node_name || p.node_id?.slice(0, 6)}</span>
                  <span className="text-gray-600 truncate">{p.practice_type}</span>
                </div>
                <span className="text-xs text-gray-500 shrink-0">{p.created_at?.slice(0, 10)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) {
            toast({ message: '正在删除...', type: 'info' })
            deleteTopicMutation.mutate(deleteTarget, {
              onSuccess: () => { toast({ message: '已删除', type: 'success' }); setDeleteTarget(null) },
              onError: () => toast({ message: '删除失败', type: 'error' }),
            })
          }
        }}
        title="确认删除"
        message="确定要删除这个学习主题吗？所有关联的节点、练习记录、能力数据将被永久删除。"
        confirmLabel="删除"
        variant="danger"
        loading={deleteTopicMutation.isPending}
      />
    </div>
  )
}
