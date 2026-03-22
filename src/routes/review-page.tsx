import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RefreshCw, Send, CheckCircle, ArrowLeft,
  Clock, AlertTriangle, BookOpen, PenTool, SkipForward,
  PartyPopper,
} from 'lucide-react'
import {
  useReviewListQuery, useReviewDetailQuery, useSubmitReviewMutation,
  useSkipReviewMutation, useSnoozeReviewMutation,
  useTopicListQuery,
} from '../hooks'
import { useQueryClient } from '@tanstack/react-query'
import { generateReviewQueue } from '../services'
import { Card, Button, Badge, LoadingSkeleton, EmptyState, ErrorState } from '../components/shared'
import { useToast } from '../components/ui/toast'
import { resolveReviewNodeTitle } from '../lib/review-display'
import { PRACTICE_LABELS, LEVEL_COLORS } from '../lib/practice-constants'
import { queryKeys } from '../lib/query-keys'
import type { ReviewItem, FeedbackLevel } from '../types'

export function ReviewPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [submittingResult, setSubmittingResult] = useState<{
    result: FeedbackLevel
    feedback: { correctness: FeedbackLevel; clarity: FeedbackLevel; naturalness: FeedbackLevel; issues: string[]; suggestions: string[] }
    needs_relearn: boolean
  } | null>(null)

  const { data: reviews, isLoading, error, refetch } = useReviewListQuery({ status: 'pending', limit: 200 })
  const { data: reviewDetail } = useReviewDetailQuery(selectedId || '')

  // Persist review answer draft to localStorage keyed by review_id
  useEffect(() => {
    if (!selectedId) return
    const saved = localStorage.getItem(`review_draft_${selectedId}`)
    if (saved) {
      setAnswer(saved)
    } else {
      setAnswer('')
    }
  }, [selectedId])

  useEffect(() => {
    if (!selectedId) return
    localStorage.setItem(`review_draft_${selectedId}`, answer)
  }, [answer, selectedId])

  // Clear draft on successful submit
  useEffect(() => {
    if (submittingResult && selectedId) {
      localStorage.removeItem(`review_draft_${selectedId}`)
    }
  }, [submittingResult, selectedId])

  // Manual review queue generation — iterate ALL active topics
  const { data: topics } = useTopicListQuery({ limit: 200 })
  const qc = useQueryClient()
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerateQueue = async () => {
    if (!topics) return
    const activeTopics = topics.filter((t) => t.status === 'active')
    if (activeTopics.length === 0) {
      toast({ message: '没有活跃的学习主题', type: 'info' })
      return
    }
    setIsGenerating(true)
    try {
      const results = await Promise.allSettled(activeTopics.map((t) => generateReviewQueue(t.topic_id)))
      const failures = results.filter((r) => r.status === 'rejected')
      if (failures.length > 0) {
        toast({ message: `${failures.length} 个主题的复习队列生成失败，请稍后重试`, type: 'warning' })
      } else if (results.length > 0) {
        toast({ message: '复习队列已生成', type: 'success' })
      }
    } catch {
      toast({ message: '复习队列生成失败，请稍后重试', type: 'error' })
    } finally {
      setIsGenerating(false)
      qc.invalidateQueries({ queryKey: queryKeys.reviews() })
    }
  }
  const submitMutation = useSubmitReviewMutation(selectedId || '')
  const skipMutation = useSkipReviewMutation(selectedId || '')
  const snoozeMutation = useSnoozeReviewMutation(selectedId || '')

  const handleSubmit = async () => {
    if (!selectedId || !answer.trim()) return
    try {
      const res = await submitMutation.mutateAsync({ user_answer: answer.trim() })
      setSubmittingResult({
        result: res.result,
        feedback: res.feedback,
        needs_relearn: res.needs_relearn,
      })
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : '提交复习失败，请稍后重试', type: 'error' })
    }
  }

  const handleSkip = async () => {
    try {
      await skipMutation.mutateAsync()
      toast({ message: '已跳过当前复习', type: 'info' })
      handleNext()
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : '跳过失败，请稍后重试', type: 'error' })
    }
  }

  const handleSnooze = async () => {
    try {
      await snoozeMutation.mutateAsync()
      toast({ message: '已稍后提醒当前复习', type: 'info' })
      handleNext()
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : '稍后提醒失败，请稍后重试', type: 'error' })
    }
  }

  const handleBack = () => {
    setSelectedId(null)
    setAnswer('')
    setSubmittingResult(null)
  }

  const handleNext = () => {
    handleBack()
    refetch()
  }

  if (isLoading) return <div className="p-6"><LoadingSkeleton lines={5} /></div>
  if (error) return <div className="p-6"><ErrorState message="复习队列加载失败" onRetry={() => refetch()} /></div>

  // Review detail mode
  if (selectedId && reviewDetail) {
    const reviewTitle = resolveReviewNodeTitle(reviewDetail, reviews || [])

    return (
      <div className="max-w-3xl mx-auto p-6 space-y-6">
        <div className="flex items-center gap-3">
          <button onClick={handleBack} className="text-gray-400 hover:text-gray-600" aria-label="返回复习列表">
            <ArrowLeft size={18} />
          </button>
          <RefreshCw size={20} className="text-amber-500" />
          <div>
            <h1 className="text-lg font-bold text-gray-900">复习: {reviewTitle}</h1>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Badge>{PRACTICE_LABELS[reviewDetail.review_type] || reviewDetail.review_type}</Badge>
              <span className={`flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${reviewDetail.priority >= 5 ? 'bg-red-100 text-red-700' : reviewDetail.priority >= 2 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'}`}>
                {reviewDetail.priority >= 5 ? '高' : reviewDetail.priority >= 2 ? '中' : '低'}
              </span>
              {reviewDetail.history_count > 0 && (
                <span>已复习 {reviewDetail.history_count} 次</span>
              )}
            </div>
          </div>
        </div>

        {/* Question area */}
        {!submittingResult && (
          <>
            <Card>
              <p className="text-xs text-gray-500 mb-1">复习原因</p>
              <p className="text-sm text-gray-700">{reviewDetail.reason ?? '系统推荐的复习内容'}</p>
            </Card>
            <Card>
              <label className="block text-sm font-medium text-gray-700 mb-2">回忆并写下你的理解</label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onInput={(e) => {
                  e.currentTarget.style.height = 'auto'
                  e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`
                }}
                placeholder="不看书，试着用自己的话表达..."
                rows={5}
                autoComplete="off"
                maxLength={50000}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              />
              <div className="flex justify-between items-center mt-3">
                <div className="flex gap-2">
                {answer.trim().length > 0 && answer.trim().length < 5 && (
                  <span className="text-xs text-amber-500 self-center">（至少 5 字）</span>
                )}
                  <Button variant="ghost" size="sm" onClick={handleSkip} loading={skipMutation.isPending}>
                    <SkipForward size={14} />
                    跳过
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleSnooze} loading={snoozeMutation.isPending}>
                    <Clock size={14} />
                    稍后提醒
                  </Button>
                </div>
                <Button
                  onClick={handleSubmit}
                  disabled={!answer.trim() || answer.trim().length < 5}
                  loading={submitMutation.isPending}
                >
                  <Send size={14} />
                  提交复习
                </Button>
              </div>
            </Card>
          </>
        )}

        {/* Result */}
        {submittingResult && (
          <Card className={`border-l-4 ${submittingResult.result === 'good' ? 'border-l-green-500' : submittingResult.result === 'medium' ? 'border-l-amber-500' : 'border-l-red-500'}`}>
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle size={18} className={LEVEL_COLORS[submittingResult.result]} />
              <span className={`text-sm font-semibold ${LEVEL_COLORS[submittingResult.result]}`}>
                {{ good: '回忆良好', medium: '有待加强', weak: '需要重新学习' }[submittingResult.result]}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 mb-3">
              {(['correctness', 'clarity', 'naturalness'] as const).map((dim) => (
                <div key={dim} className="text-center p-2 bg-gray-50 rounded-lg">
                  <p className="text-[10px] text-gray-500">
                    {{ correctness: '正确性', clarity: '清晰度', naturalness: '自然度' }[dim]}
                  </p>
                  <p className={`text-sm font-semibold ${LEVEL_COLORS[submittingResult.feedback[dim]]}`}>
                    {{ good: '良好', medium: '一般', weak: '薄弱' }[submittingResult.feedback[dim]]}
                  </p>
                </div>
              ))}
            </div>
            {submittingResult.feedback.issues.length > 0 && (
              <div className="mb-2">
                {submittingResult.feedback.issues.map((issue, i) => (
                  <p key={i} className="text-xs text-gray-600">{issue}</p>
                ))}
              </div>
            )}
            {submittingResult.feedback.suggestions.length > 0 && (
              <div className="mb-2">
                {submittingResult.feedback.suggestions.map((s, i) => (
                  <p key={i} className="text-xs text-indigo-600">{s}</p>
                ))}
              </div>
            )}
            {submittingResult.needs_relearn && (
              <div className="bg-red-50 rounded-lg p-3 mt-3">
                <p className="text-xs text-red-600 flex items-center gap-1">
                  <AlertTriangle size={12} />
                  建议重新学习这个节点
                </p>
              </div>
            )}
            <div className="flex flex-wrap gap-3 mt-4">
              <Button onClick={handleNext}>继续下一个</Button>
              {reviewDetail.topic_id && reviewDetail.node_id && (
                <>
                  <Button variant="secondary" onClick={() => navigate(`/topic/${reviewDetail.topic_id}/learn?nodeId=${reviewDetail.node_id}`)}>
                    <BookOpen size={14} />
                    返回学习该节点
                  </Button>
                  <Button variant="outline" onClick={() => navigate(`/topic/${reviewDetail.topic_id}/practice?nodeId=${reviewDetail.node_id}`)}>
                    <PenTool size={14} />
                    练习巩固
                  </Button>
                </>
              )}
              <Button variant="ghost" onClick={() => navigate('/')}>返回首页</Button>
            </div>
          </Card>
        )}
      </div>
    )
  }

  // Queue list mode
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <RefreshCw size={24} className="text-amber-500" />
        复习队列
      </h1>

      {isGenerating ? (
        <div className="space-y-3">
          <LoadingSkeleton lines={5} />
        </div>
      ) : !reviews || reviews.length === 0 ? (
        <EmptyState
          icon={<PartyPopper size={48} className="text-emerald-400" />}
          title="全部复习完毕"
          description="暂无待复习任务，继续保持学习节奏即可"
          action={
            <Button onClick={handleGenerateQueue}>
              <RefreshCw size={14} />
              检查是否有新复习
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <ReviewCard key={review.review_id} review={review} onSelect={setSelectedId} />
          ))}
        </div>
      )}
    </div>
  )
}

function ReviewCard({ review, onSelect }: { review: ReviewItem; onSelect: (id: string) => void }) {
  const now = new Date()
  const hasDue = !!review.due_at
  const dueDate = hasDue ? new Date(review.due_at) : null
  const isOverdue = hasDue && dueDate! < now
  const isDueSoon = hasDue && !isOverdue && (dueDate!.getTime() - now.getTime()) < 3 * 24 * 60 * 60 * 1000

  return (
    <Card
      className="cursor-pointer hover:border-indigo-300 transition-colors"
    >
      <div
        className="flex items-center justify-between"
        role="button"
        tabIndex={0}
        onClick={() => onSelect(review.review_id)}
        onKeyDown={(e) => { if (e.key === 'Enter') onSelect(review.review_id) }}
      >
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${isOverdue ? 'bg-red-500' : isDueSoon ? 'bg-amber-400' : hasDue ? 'bg-green-500' : 'bg-gray-300'}`} />
          <div>
            <h3 className="text-sm font-medium text-gray-900">{review.node_name ?? review.node_id}</h3>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{PRACTICE_LABELS[review.review_type] || review.review_type}</span>
              <span className="text-gray-300">|</span>
              <span className="flex items-center gap-1">
                <Clock size={10} />
                {isOverdue ? '已过期' : hasDue ? dueDate!.toLocaleDateString() : '待安排'}
              </span>
              {isDueSoon && (
                <span className="inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                  即将到期
                </span>
              )}
              {review.history_count > 0 && (
                <>
                  <span className="text-gray-300">|</span>
                  <span>{review.history_count} 次</span>
                </>
              )}
            </div>
            {review.reason && (
              <p className="text-xs text-gray-400 mt-1 truncate max-w-xs">{review.reason}</p>
            )}
          </div>
        </div>
        <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${review.priority >= 5 ? 'bg-red-100 text-red-700' : review.priority >= 2 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'}`}>
          {review.priority >= 5 ? '高' : review.priority >= 2 ? '中' : '低'}
        </span>
      </div>
    </Card>
  )
}
