import React from 'react'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PracticePage } from '../routes/practice-page'
import { useAppStore } from '../stores'

const routerMocks = vi.hoisted(() => ({
  useParams: vi.fn(),
  useNavigate: vi.fn(),
  useSearchParams: vi.fn(),
}))

const hookMocks = vi.hoisted(() => ({
  useNodeDetailQuery: vi.fn(),
  useGetPracticePromptMutation: vi.fn(),
  useSubmitPracticeMutation: vi.fn(),
  useSaveExpressionAssetMutation: vi.fn(),
  useExpressionAssetsQuery: vi.fn(),
  usePracticeAttemptsQuery: vi.fn(),
  useUpdateNodeStatusMutation: vi.fn(),
  useSettingsQuery: vi.fn(),
  useCompleteSessionMutation: vi.fn(),
  useRecommendedPracticeQuery: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useParams: routerMocks.useParams,
    useNavigate: routerMocks.useNavigate,
    useSearchParams: routerMocks.useSearchParams,
  }
})

vi.mock('../hooks', () => ({
  useNodeDetailQuery: hookMocks.useNodeDetailQuery,
  useGetPracticePromptMutation: hookMocks.useGetPracticePromptMutation,
  useSubmitPracticeMutation: hookMocks.useSubmitPracticeMutation,
  useSaveExpressionAssetMutation: hookMocks.useSaveExpressionAssetMutation,
  useExpressionAssetsQuery: hookMocks.useExpressionAssetsQuery,
  usePracticeAttemptsQuery: hookMocks.usePracticeAttemptsQuery,
  useUpdateNodeStatusMutation: hookMocks.useUpdateNodeStatusMutation,
  useSettingsQuery: hookMocks.useSettingsQuery,
  useCompleteSessionMutation: hookMocks.useCompleteSessionMutation,
  useRecommendedPracticeQuery: hookMocks.useRecommendedPracticeQuery,
}))

vi.mock('../components/ui/toast', () => ({
  useToast: () => vi.fn(),
}))

vi.mock('../components/shared', () => ({
  Card: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Button: ({
    children,
    onClick,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children?: React.ReactNode }) => (
    <button type="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
  Badge: ({ children }: { children?: React.ReactNode }) => <span>{children}</span>,
  LoadingSkeleton: () => <div>loading</div>,
  EmptyState: ({ title, action }: { title: string; action?: React.ReactNode }) => <div>{title}{action}</div>,
  ErrorState: ({ title = 'error', message, onRetry }: { title?: string; message: string; onRetry?: () => void }) => (
    <div>
      <span>{title}</span>
      <span>{message}</span>
      <button type="button" onClick={onRetry}>retry</button>
    </div>
  ),
}))

vi.mock('../components/shared/ability-radar', () => ({
  AbilityBars: () => <div>ability-bars</div>,
}))

function makeMutation<T extends object>(overrides?: Partial<T>): T {
  return {
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    ...(overrides || {}),
  } as T
}

function createNodeDetail() {
  return {
    node: {
      node_id: 'nd_message',
      name: '消息传递',
      summary: '图神经网络的核心更新机制',
    },
    ability: {
      understand: 60,
      example: 50,
      contrast: 40,
      apply: 45,
      explain: 48,
      recall: 38,
      transfer: 35,
      teach: 30,
    },
    applications: [{ node_id: 'nd_apply', name: '应用一' }],
    related: [{ node_id: 'nd_related', name: '相关概念' }],
  }
}

async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

describe('practice session flow', () => {
  let container: HTMLDivElement
  let root: Root
  let navigate: ReturnType<typeof vi.fn>

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    navigate = vi.fn()

    routerMocks.useParams.mockReturnValue({ topicId: 'tp_graph' })
    routerMocks.useNavigate.mockReturnValue(navigate)
    routerMocks.useSearchParams.mockReturnValue([
      new URLSearchParams('nodeId=nd_message&sessionId=ss_live'),
    ])

    hookMocks.useNodeDetailQuery.mockReturnValue({
      data: createNodeDetail(),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    hookMocks.useGetPracticePromptMutation.mockReturnValue(makeMutation())
    hookMocks.useSubmitPracticeMutation.mockReturnValue(makeMutation())
    hookMocks.useSaveExpressionAssetMutation.mockReturnValue(makeMutation())
    hookMocks.useExpressionAssetsQuery.mockReturnValue({ data: [] })
    hookMocks.usePracticeAttemptsQuery.mockReturnValue({ data: [] })
    hookMocks.useUpdateNodeStatusMutation.mockReturnValue(makeMutation())
    hookMocks.useSettingsQuery.mockReturnValue({
      data: {
        auto_generate_summary: true,
      },
    })
    hookMocks.useCompleteSessionMutation.mockReturnValue(makeMutation())
    hookMocks.useRecommendedPracticeQuery.mockReturnValue({ data: null })

    useAppStore.setState({
      current_topic_id: null,
      current_node_id: null,
      current_session_id: null,
      session_restored: false,
      graph_view: 'mainline',
      graph_sidebar_open: true,
      graph_selected_node_id: null,
      graph_edge_filters: new Set(),
      graph_collapsed_node_ids: new Set(),
      graph_show_edge_filter: false,
      practice_state: 'completed',
      practice_draft: '',
      sidebar_collapsed: false,
    })
  })

  afterEach(async () => {
    await act(async () => {
      root.unmount()
    })
    container.remove()
    vi.clearAllMocks()
  })

  it('automatically completes the session and enters summary when auto_generate_summary is enabled', async () => {
    const completeSessionMutation = makeMutation<{
      mutateAsync: ReturnType<typeof vi.fn>
    }>({
      mutateAsync: vi.fn().mockResolvedValue({
        session_id: 'ss_live',
        topic_id: 'tp_graph',
        status: 'completed',
        summary: '本轮学习完成',
        synthesis: {
          mainline_summary: '总结',
          key_takeaways: [],
          next_recommendations: [],
          review_items_created: 1,
          new_assets_count: 1,
          covered_scope: '',
          skippable_nodes: [],
          review_candidates: [],
        },
      }),
    })
    hookMocks.useCompleteSessionMutation.mockReturnValue(completeSessionMutation)

    await act(async () => {
      root.render(<PracticePage />)
    })
    await flush()

    expect(completeSessionMutation.mutateAsync).toHaveBeenCalled()
    expect(navigate).toHaveBeenCalled()
  })
})
