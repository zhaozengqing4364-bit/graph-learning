import { useState, useCallback, useEffect, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  PenTool, Send, RotateCcw, BookmarkPlus, ArrowLeft,
  CheckCircle, AlertTriangle, Info, RefreshCw, FileText,
  ChevronDown, History, Check, Loader2,
} from 'lucide-react'
import {
  useNodeDetailQuery, useGetPracticePromptMutation,
  useSubmitPracticeMutation, useSaveExpressionAssetMutation,
  useExpressionAssetsQuery, usePracticeAttemptsQuery,
  useUpdateNodeStatusMutation, useSettingsQuery,
  useCompleteSessionMutation, useRecommendedPracticeQuery,
} from '../hooks'
import { useAppStore } from '../stores'
import { PRACTICE_LABELS, PRACTICE_SEQUENCE, LEVEL_COLORS } from '../lib/practice-constants'
import { Card, Button, Badge, LoadingSkeleton, EmptyState, ErrorState } from '../components/shared'
import { AbilityBars } from '../components/shared/ability-radar'
import { ConfirmDialog } from '../components/ui/confirm-dialog'
import { useToast } from '../components/ui/toast'
import { ABILITY_DIMENSIONS, type AbilityRecord, type PracticeType, type PracticePrompt, type PracticeFeedback } from '../types'
import { buildPracticeRoute, buildSummaryRoute } from '../lib/navigation-context'
import { getSessionCompletionIntent } from '../features/article-workspace/session-flow'

const FRICTION_LABELS: Record<string, { label: string; practice: string }> = {
  prerequisite_gap: { label: '前置知识缺失', practice: '定义' },
  concept_confusion: { label: '概念混淆', practice: '对比' },
  lack_of_example: { label: '缺少实例', practice: '举例' },
  weak_structure: { label: '结构薄弱', practice: '教新手' },
  abstract_overload: { label: '抽象超载', practice: '举例' },
  weak_recall: { label: '记忆薄弱', practice: '压缩' },
  weak_application: { label: '应用不熟练', practice: '应用' },
}

function mergeAbilityUpdate(
  base: AbilityRecord | null | undefined,
  delta: Partial<AbilityRecord> | undefined,
): AbilityRecord | null {
  if (!base) {
    return null
  }

  if (!delta) {
    return base
  }

  return ABILITY_DIMENSIONS.reduce<AbilityRecord>((next, dimension) => {
    const increment = delta[dimension.key] ?? 0
    next[dimension.key] = Math.max(0, Math.min(100, base[dimension.key] + increment))
    return next
  }, { ...base })
}

export function PracticePage() {
  const { topicId } = useParams<{ topicId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const nodeId = searchParams.get('nodeId') || ''
  const sessionId = searchParams.get('sessionId')?.trim() || ''

  const { practice_state, setPracticeState, practice_draft, setPracticeDraft } = useAppStore()
  const toast = useToast()
  const { data: settings } = useSettingsQuery()
  const autoStart = searchParams.get('auto') === 'true'
  const shouldAutoSummary = searchParams.get('summary') === 'true' || (settings?.auto_generate_summary ?? true)
  const sessionCompletionIntent = getSessionCompletionIntent({
    topicId: topicId || '',
    sessionId,
    autoGenerateSummary: shouldAutoSummary,
  })
  const summaryRoute = buildSummaryRoute(topicId || '', sessionId)

  const {
    data: nodeDetail,
    isLoading: nodeLoading,
    error: nodeError,
    refetch: refetchNodeDetail,
  } = useNodeDetailQuery(topicId!, nodeId)
  const getPromptMutation = useGetPracticePromptMutation(topicId!, nodeId)
  const submitMutation = useSubmitPracticeMutation(topicId!, nodeId)
  const saveAssetMutation = useSaveExpressionAssetMutation(topicId!, nodeId)
  const updateStatusMutation = useUpdateNodeStatusMutation(topicId!, nodeId)
  const completeSessionMutation = useCompleteSessionMutation(topicId!, sessionId)
  const { data: expressionAssets } = useExpressionAssetsQuery(topicId!, { node_id: nodeId, limit: 10 })
  const { data: practiceAttempts } = usePracticeAttemptsQuery(topicId!, { node_id: nodeId, limit: 20 })
  const { data: recommendedPractice } = useRecommendedPracticeQuery(topicId!, nodeId)
  const [showHistory, setShowHistory] = useState(false)
  const [feedbackExpanded, setFeedbackExpanded] = useState(true)

  const [currentType, setCurrentType] = useState<PracticeType>('define')
  const [prompt, setPrompt] = useState<PracticePrompt | null>(null)
  const [feedback, setFeedback] = useState<PracticeFeedback | null>(null)
  const [answerState, setAnswerState] = useState(() => ({ nodeId, value: practice_draft }))
  const answer = answerState.nodeId === nodeId ? answerState.value : ''
  const setAnswerValue = useCallback((value: string) => {
    setAnswerState({ nodeId, value })
    setPracticeDraft(value)
  }, [nodeId, setPracticeDraft])

  // Clear draft when switching nodes to prevent cross-node pollution
  const prevNodeIdRef = useRef(nodeId)
  useEffect(() => {
    if (prevNodeIdRef.current !== nodeId) {
      prevNodeIdRef.current = nodeId
      if (practice_draft) {
        setPracticeDraft('')
      }
    }
  }, [nodeId, practice_draft, setPracticeDraft])
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false)
  const autoSummaryStartedRef = useRef<string | null>(null)

  const buildLearnRoute = useCallback((nextNodeId?: string) => {
    if (!topicId) {
      return '/'
    }

    const params = new URLSearchParams()
    if (nextNodeId) {
      params.set('nodeId', nextNodeId)
    }
    if (sessionId) {
      params.set('sessionId', sessionId)
    }

    const query = params.toString()
    return query ? `/topic/${topicId}/learn?${query}` : `/topic/${topicId}/learn`
  }, [sessionId, topicId])

  const handleGetPrompt = useCallback(async (type: PracticeType, regenerate = false) => {
    setPracticeState('loading_prompt')
    setCurrentType(type)
    setFeedback(null)
    setAnswerValue('')
    setSubmitError(null)
    try {
      const res = await getPromptMutation.mutateAsync({ practice_type: type, regenerate })
      setPrompt(res)
      setPracticeState('answering')
    } catch {
      setPracticeState('idle')
      toast({ message: '题目生成失败，请稍后重试', type: 'error' })
    }
  }, [getPromptMutation, setAnswerValue, setPracticeState, toast])

  const handleRegenerate = useCallback(() => {
    handleGetPrompt(currentType, true)
  }, [currentType, handleGetPrompt])

  const autoStartedForRef = useRef<string | null>(null)

  useEffect(() => {
    if (!nodeId || !autoStart) {
      return
    }

    const autoStartKey = `${topicId || ''}:${nodeId}`
    if (autoStartedForRef.current === autoStartKey) {
      return
    }

    autoStartedForRef.current = autoStartKey
    const timer = window.setTimeout(() => {
      void handleGetPrompt('define')
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [autoStart, handleGetPrompt, nodeId, topicId])

  const handleSubmit = useCallback(async () => {
    if (!prompt || !answer.trim()) return
    setPracticeState('submitting')
    setSubmitError(null)
    try {
      const res = await submitMutation.mutateAsync({
        session_id: sessionId,
        practice_type: currentType,
        prompt_text: prompt.prompt_text,
        user_answer: answer.trim(),
      })
      setFeedback(res)
      setPracticeState('feedback_ready')
      // Only advance node status when answer quality is not weak
      if (nodeId && res.feedback.correctness !== 'weak') {
        try {
          await updateStatusMutation.mutateAsync('practiced')
        } catch {
          // Status update failure should not block feedback display
        }
      }
    } catch (err) {
      setPracticeState('answering')
      setSubmitError(err instanceof Error ? err.message : '提交失败，请重试')
    }
  }, [answer, currentType, prompt, sessionId, setPracticeState, submitMutation, updateStatusMutation, nodeId])

  const handleSaveAsset = useCallback(async () => {
    if (!feedback) return
    setPracticeState('saving_asset')
    try {
      await saveAssetMutation.mutateAsync({
        attempt_id: feedback.attempt_id,
        expression_type: currentType,
        user_expression: answer,
        ai_rewrite: feedback.recommended_answer,
        skeleton: feedback.expression_skeleton,
        quality_tags: feedback.feedback.correctness === 'good' ? ['clear'] : [],
      })
      setPracticeState('completed')
    } catch {
      setPracticeState('feedback_ready')
      toast({ message: '表达资产保存失败，请重试', type: 'error' })
    }
  }, [answer, currentType, feedback, saveAssetMutation, setPracticeState, toast])

  const handleCompleteSession = useCallback(async () => {
    if (!summaryRoute) {
      return
    }

    const summaryKey = `${sessionId}:${practice_state}`
    if (autoSummaryStartedRef.current === summaryKey) {
      return
    }

    autoSummaryStartedRef.current = summaryKey

    try {
      const request = sessionCompletionIntent.request ?? {
        generate_summary: true,
        generate_review_items: true,
      }
      const summary = await completeSessionMutation.mutateAsync(request)
      navigate(summaryRoute, {
        state: { summary },
      })
    } catch (error) {
      autoSummaryStartedRef.current = null
      toast({ message: error instanceof Error ? error.message : '会话收束失败，请稍后重试', type: 'warning' })
    }
  }, [
    completeSessionMutation,
    navigate,
    practice_state,
    sessionCompletionIntent.request,
    sessionId,
    summaryRoute,
    toast,
  ])

  useEffect(() => {
    if (practice_state !== 'completed' || sessionCompletionIntent.type !== 'summary') {
      return
    }

    void handleCompleteSession()
  }, [handleCompleteSession, practice_state, sessionCompletionIntent.type])

  const handleNext = () => {
    handleGetPrompt(currentType)
  }

  if (!nodeId) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<PenTool size={48} />}
          title="请选择一个节点后再开始练习"
          description="请先从学习页或图谱里选中一个节点，再进入表达练习。"
          action={
            <Button onClick={() => navigate(buildLearnRoute())}>
              返回学习
            </Button>
          }
        />
      </div>
    )
  }

  if (nodeLoading) return <div className="p-6"><LoadingSkeleton lines={5} /></div>
  if (nodeError) {
    return (
      <div className="p-6">
        <ErrorState
          message={nodeError instanceof Error ? nodeError.message : '练习节点加载失败'}
          onRetry={() => { void refetchNodeDetail() }}
        />
      </div>
    )
  }
  if (!nodeDetail) {
    return (
      <div className="p-6">
        <ErrorState
          title="练习节点不可用"
          message="当前练习节点没有可显示的数据，请返回学习页重新选择。"
          onRetry={() => { void refetchNodeDetail() }}
        />
      </div>
    )
  }

  const { node } = nodeDetail
  // Collect practiceable neighbor nodes
  const neighborNodes = [
    ...(nodeDetail.applications || []),
    ...(nodeDetail.related || []),
  ].filter((n) => n.node_id !== nodeId)
  const uniqueNeighbors = neighborNodes.filter((n, i, arr) => arr.findIndex((x) => x.node_id === n.node_id) === i).slice(0, 5)

  const frictionRecommendation = feedback?.friction_tags && feedback.friction_tags.length > 0 ? (
    <div className="p-3 bg-indigo-50 rounded-lg text-sm text-indigo-700">
      <span className="font-medium">下一步推荐：</span>
      <span>尝试 {feedback.friction_tags.slice(0, 3).map((tag) => FRICTION_LABELS[tag]?.label || tag).join('、')}（建议练习：{feedback.friction_tags.slice(0, 3).map((tag) => FRICTION_LABELS[tag]?.practice || tag).join('、')}）</span>
    </div>
  ) : null

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => { if (practice_state === 'answering' && answer.trim()) { setShowLeaveConfirm(true); return } navigate(buildLearnRoute(nodeId)) }} className="text-gray-400 hover:text-gray-600" aria-label="返回学习页">
            <ArrowLeft size={18} />
          </button>
          <PenTool size={20} className="text-indigo-500" />
          <div>
            <h1 className="text-lg font-bold text-gray-900">表达练习</h1>
            <p className="text-xs text-gray-500">{node.name}</p>
          </div>
        </div>
        <div className="flex gap-1">
          {(Object.keys(PRACTICE_LABELS) as PracticeType[]).map((type) => (
            <button
              key={type}
              onClick={() => handleGetPrompt(type)}
              disabled={getPromptMutation.isPending}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                currentType === type
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              {PRACTICE_LABELS[type]}
            </button>
          ))}
        </div>
      </div>

      {practice_state === 'idle' && !prompt && !feedback && (
        <Card>
          <div className="space-y-4">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-gray-900">选择一种练习方式开始</p>
              <p className="text-sm text-gray-500 leading-relaxed">
                {node.summary || '围绕当前节点生成一题表达练习，完成后会获得诊断反馈、推荐表达和可保存的表达资产。'}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {PRACTICE_SEQUENCE.map((type) => {
                const hasAttempt = practiceAttempts?.some((a) => a.practice_type === type)
                return (
                <button
                  key={type}
                  onClick={() => setCurrentType(type)}
                  className={`relative px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    currentType === type
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {PRACTICE_LABELS[type]}
                  {hasAttempt && (
                    <Check size={10} className="absolute -right-0.5 -top-0.5 text-green-500 bg-white rounded-full" />
                  )}
                </button>
                )
              })}
            </div>

            {recommendedPractice?.recommended_type && recommendedPractice.recommended_type !== currentType && (
              <p className="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1.5">
                建议：{recommendedPractice.reason}
              </p>
            )}

            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-xs text-gray-500">
                当前将开始
                <span className="font-medium text-indigo-600 ml-1">{PRACTICE_LABELS[currentType]}</span>
                练习
              </div>
              <Button onClick={() => handleGetPrompt(currentType)}>
                <PenTool size={16} />
                开始{PRACTICE_LABELS[currentType]}练习
              </Button>
            </div>
            {expressionAssets && expressionAssets.length > 0 && (
              <div className="mt-3 text-xs text-gray-400 flex items-center gap-1">
                <BookmarkPlus size={12} />
                <span>已保存 {expressionAssets.length} 条表达资产</span>
                <button
                  onClick={() => document.getElementById('expression-assets')?.scrollIntoView({ behavior: 'smooth' })}
                  className="text-indigo-400 hover:text-indigo-600 ml-1"
                >
                  查看
                </button>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Guided practice sequence hint */}
      {prompt && (
        <div className="flex items-center gap-2 px-3 py-2 bg-indigo-50 rounded-lg text-xs text-indigo-600">
          <span className="font-medium">推荐顺序：</span>
          <span className="text-indigo-500">
            {PRACTICE_SEQUENCE.map((t, i) => (
              <span key={t}>
                {i > 0 && ' → '}
                <span className={PRACTICE_LABELS[t] === PRACTICE_LABELS[currentType] ? 'font-bold underline' : ''}>
                  {PRACTICE_LABELS[t]}
                </span>
              </span>
            ))}
          </span>
        </div>
      )}

      {/* Prompt */}
      {prompt && (
        <Card>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-indigo-700 text-xs font-medium">
              <PenTool size={14} />
              题目 ({PRACTICE_LABELS[prompt.practice_type]})
              {prompt.cached && (
                <Badge variant="info" className="ml-1.5 text-[10px]">缓存</Badge>
              )}
            </div>
            <button
              onClick={handleRegenerate}
              disabled={getPromptMutation.isPending}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="重新生成（会消耗 AI 调用）"
            >
              <RefreshCw size={12} />
              重新生成
            </button>
          </div>
          <p className="text-sm text-gray-700 mb-3 leading-relaxed">{prompt.prompt_text}</p>
          {prompt.evaluation_dimensions.length > 0 && (
            <ul className="space-y-1 mb-2">
              {prompt.evaluation_dimensions.map((r, i) => (
                <li key={i} className="text-xs text-gray-500 flex items-start gap-1">
                  <span className="text-indigo-400 mt-0.5">-</span>
                  {r}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {/* Answer Input */}
      {(practice_state === 'answering' || practice_state === 'submitting') && (
        <Card>
          <label className="block text-sm font-medium text-gray-700 mb-2">你的回答</label>
            <textarea
              value={answer}
              onChange={(e) => {
                setAnswerValue(e.target.value)
              }}
            onInput={(e) => {
              e.currentTarget.style.height = 'auto'
              e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`
            }}
            placeholder={prompt?.minimum_answer_hint || '在此输入你的回答...'}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                e.preventDefault()
                handleSubmit()
              }
            }}
            rows={5}
            autoComplete="off"
            maxLength={50000}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <div className="flex justify-between items-center mt-3">
            <p className="text-xs text-gray-400">
              {answer.length} 字
              {answer.trim().length > 0 && answer.trim().length < 5 && (
                <span className="text-amber-500 ml-1">（至少 5 字，例如："深度学习是一种基于神经网络的机器学习方法"）</span>
              )}
            </p>
            <div className="flex items-center gap-2">
              {submitError && (
                <Button variant="secondary" onClick={handleSubmit}>
                  <RefreshCw size={14} />
                  重试
                </Button>
              )}
              <Button
                onClick={handleSubmit}
                disabled={!answer.trim() || answer.trim().length < 5 || practice_state === 'submitting'}
              >
                {practice_state === 'submitting' ? (
                  <><Loader2 size={14} className="animate-spin" /> 提交中...</>
                ) : (
                  <><Send size={14} /> 提交答案</>
                )}
              </Button>
            </div>
          </div>
          {submitError && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
              <AlertTriangle size={12} />
              {submitError}
            </div>
          )}
        </Card>
      )}

      {/* Loading prompt state */}
      {practice_state === 'loading_prompt' && (
        <Card>
          <LoadingSkeleton lines={3} />
          <p className="text-xs text-gray-400 mt-2">正在生成练习题...</p>
        </Card>
      )}

      {/* Submitting */}
      {practice_state === 'submitting' && (
        <Card>
          <LoadingSkeleton lines={3} />
          <p className="text-xs text-gray-400 mt-2">正在评估你的回答...</p>
        </Card>
      )}

      {/* Feedback */}
      {feedback && (practice_state === 'feedback_ready' || practice_state === 'saving_asset') && (
        <Card className="border-l-4 border-l-indigo-500">
          <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-1.5">
            <CheckCircle size={14} className="text-indigo-500" />
            评估反馈
            {feedback.diagnosis_fallback && (
              <Badge className="text-[10px] bg-amber-100 text-amber-700">简化诊断</Badge>
            )}
            <button
              onClick={() => setFeedbackExpanded(!feedbackExpanded)}
              className="ml-auto p-0.5 rounded hover:bg-gray-100 transition-colors"
              aria-label={feedbackExpanded ? '折叠反馈' : '展开反馈'}
            >
              <ChevronDown size={14} className={`text-gray-400 transition-transform duration-200 ${feedbackExpanded ? '' : '-rotate-90'}`} />
            </button>
          </h3>

          {/* Collapsible feedback body */}
          <div className={`overflow-hidden transition-all duration-300 ease-in-out ${feedbackExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>

          {/* Scores */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            {(['correctness', 'clarity', 'naturalness'] as const).map((dim) => (
              <div key={dim} className="text-center p-2 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">
                  {{ correctness: '正确性', clarity: '清晰度', naturalness: '自然度' }[dim]}
                </p>
                <p className={`text-sm font-semibold ${LEVEL_COLORS[feedback.feedback[dim]]}`}>
                  {{ good: '好', medium: '中', weak: '弱' }[feedback.feedback[dim]]}
                </p>
              </div>
            ))}
          </div>

          {/* Issues */}
          {feedback.feedback.issues.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-amber-600 mb-1 flex items-center gap-1">
                <AlertTriangle size={12} />
                主要问题
              </p>
              <ul className="space-y-1">
                {feedback.feedback.issues.map((issue, i) => (
                  <li key={i} className="text-xs text-gray-600">{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggestions */}
          {feedback.feedback.suggestions.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-indigo-600 mb-1 flex items-center gap-1">
                <Info size={12} />
                改进建议
              </p>
              <ul className="space-y-1">
                {feedback.feedback.suggestions.map((s, i) => (
                  <li key={i} className="text-xs text-gray-600">{s}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommended answer */}
          <div className="bg-green-50 rounded-lg p-3 mb-3">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-medium text-green-700">推荐表达</p>
              <button
                onClick={() => {
                  if (feedback?.recommended_answer) {
                    setAnswerValue(feedback.recommended_answer)
                  }
                }}
                className="text-xs text-indigo-600 hover:text-indigo-700 transition-colors"
              >
                采纳
              </button>
            </div>
            <p className="text-sm text-green-800">{feedback.recommended_answer}</p>
          </div>

          {/* Skeleton */}
          <div className="bg-blue-50 rounded-lg p-3 mb-4">
            <p className="text-xs font-medium text-blue-700 mb-1">表达骨架</p>
            <p className="text-sm text-blue-800 font-mono whitespace-pre-wrap">{feedback.expression_skeleton}</p>
          </div>

          {/* Ability update */}
          {feedback.ability_update && Object.keys(feedback.ability_update).length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <p className="text-xs font-medium text-gray-500 mb-1">能力变化</p>
              <AbilityBars ability={mergeAbilityUpdate(nodeDetail.ability, feedback.ability_update)} />
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <Button onClick={handleSaveAsset} loading={saveAssetMutation.isPending}>
              <BookmarkPlus size={16} />
              保存表达资产
            </Button>
            {expressionAssets && expressionAssets.length > 0 && (
              <button
                onClick={() => document.getElementById('expression-assets')?.scrollIntoView({ behavior: 'smooth' })}
                className="inline-flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
              >
                <History size={14} />
                查看历史表达({expressionAssets.length})
              </button>
            )}
            <Button variant="secondary" disabled={getPromptMutation.isPending} onClick={handleNext}>
              <RotateCcw size={16} />
              再练一题
            </Button>
            <Button variant="ghost" onClick={() => navigate(buildLearnRoute(nodeId))}>
              返回学习
            </Button>
          </div>
          </div>{/* end collapsible feedback body */}
        </Card>
      )}

      {/* Next Step Recommendation */}
      {practice_state === 'feedback_ready' && frictionRecommendation && (
        <div className="mt-3">{frictionRecommendation}</div>
      )}

      {/* Completed */}
      {practice_state === 'completed' && (
        <Card className="text-center py-8">
          <CheckCircle size={32} className="text-green-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-900 mb-1">表达资产已保存</h3>
          <p className="text-sm text-gray-500 mb-4">你的优秀表达已记录，随时可以在资产库中回顾</p>
          <div className="flex justify-center gap-3">
            <Button disabled={getPromptMutation.isPending} onClick={handleNext}>
              <RotateCcw size={16} />
              继续练习
            </Button>
            <Button variant="secondary" onClick={() => navigate(buildLearnRoute(nodeId))}>
              返回学习
            </Button>
            {summaryRoute ? (
              <Button
                variant="outline"
                size="sm"
                disabled={completeSessionMutation.isPending}
                onClick={() => {
                  void handleCompleteSession()
                }}
              >
                <FileText size={14} />
                {completeSessionMutation.isPending ? '生成总结中...' : '完成本轮'}
                结束本轮
              </Button>
            ) : null}
          </div>
          {!summaryRoute && (
            <p className="mt-3 text-xs text-gray-500">当前练习没有绑定到有效会话，暂不提供收束总结入口。</p>
          )}
          {/* Practice next node */}
          {uniqueNeighbors.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-gray-500 mb-2">练习下一个节点</p>
              <div className="flex flex-wrap justify-center gap-2">
                {uniqueNeighbors.map((n) => (
                  <button
                    key={n.node_id}
                    onClick={() => navigate(buildPracticeRoute(topicId!, n.node_id, { sessionId }))}
                    className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full hover:bg-indigo-100 transition-colors"
                  >
                    {n.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {/* Friction tags recommendation */}
          {frictionRecommendation && (
            <div className="mt-4">{frictionRecommendation}</div>
          )}
        </Card>
      )}

      {/* Practice History Panel */}
      {practiceAttempts && practiceAttempts.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <button
            className="flex items-center justify-between w-full text-left"
            onClick={() => setShowHistory(!showHistory)}
          >
            <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
              <History size={14} />
              练习记录 ({practiceAttempts.length})
            </h3>
            <ChevronDown size={14} className={`text-gray-400 transition-transform ${showHistory ? 'rotate-180' : ''}`} />
          </button>
          {showHistory && (
            <div className="mt-3 space-y-2 max-h-60 overflow-auto">
              {practiceAttempts.map((a) => (
                <div key={a.attempt_id} className="text-sm p-2 bg-gray-50 rounded flex items-center justify-between">
                  <div>
                    <Badge variant="info" className="text-[10px]">{a.practice_type}</Badge>
                    <span className="text-xs text-gray-400 ml-2">{a.created_at?.slice(5, 16)}</span>
                  </div>
                  <span className="text-xs text-gray-500 max-w-[200px] truncate">{a.user_answer?.slice(0, 40)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Expression Assets Panel */}
      {expressionAssets && expressionAssets.length > 0 && (
        <div id="expression-assets" className="mt-4 bg-white rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">历史表达资产</h3>
          <div className="space-y-2 max-h-48 overflow-auto">
            {expressionAssets.map((a) => (
              <div key={a.asset_id} className="text-sm p-2 bg-gray-50 rounded">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-indigo-600">{a.expression_type}</span>
                  {a.favorited && <span className="text-yellow-500 text-xs">&#9733;</span>}
                </div>
                <p className="text-gray-600 mt-1 line-clamp-2">{a.user_expression}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Leave confirmation dialog */}
      <ConfirmDialog
        open={showLeaveConfirm}
        onClose={() => setShowLeaveConfirm(false)}
        onConfirm={() => { setShowLeaveConfirm(false); navigate(buildLearnRoute(nodeId)) }}
        title="确认离开"
        message="答案尚未提交，确定要离开吗？"
        confirmLabel="离开"
        variant="warning"
      />
    </div>
  )
}
