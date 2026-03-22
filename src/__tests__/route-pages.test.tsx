import type { ReactElement } from 'react'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SummaryPage } from '../routes/summary-page'
import { PracticePage } from '../routes/practice-page'
import { AssetsPage } from '../routes/assets-page'
import { useAppStore } from '../stores'

const hookMocks = vi.hoisted(() => ({
  useSessionSummaryQuery: vi.fn(),
  useNodeDetailQuery: vi.fn(),
  useGetPracticePromptMutation: vi.fn(),
  useSubmitPracticeMutation: vi.fn(),
  useSaveExpressionAssetMutation: vi.fn(),
  useExpressionAssetsQuery: vi.fn(),
  usePracticeAttemptsQuery: vi.fn(),
  useUpdateNodeStatusMutation: vi.fn(),
  useCompleteSessionMutation: vi.fn(),
  useRecommendedPracticeQuery: vi.fn(),
  useToggleFavoriteMutation: vi.fn(),
  useTopicQuery: vi.fn(),
  useSettingsQuery: vi.fn(),
  useResolvedTopicContext: vi.fn(),
}))

vi.mock('../hooks', () => ({
  useSessionSummaryQuery: hookMocks.useSessionSummaryQuery,
  useNodeDetailQuery: hookMocks.useNodeDetailQuery,
  useGetPracticePromptMutation: hookMocks.useGetPracticePromptMutation,
  useSubmitPracticeMutation: hookMocks.useSubmitPracticeMutation,
  useSaveExpressionAssetMutation: hookMocks.useSaveExpressionAssetMutation,
  useExpressionAssetsQuery: hookMocks.useExpressionAssetsQuery,
  usePracticeAttemptsQuery: hookMocks.usePracticeAttemptsQuery,
  useUpdateNodeStatusMutation: hookMocks.useUpdateNodeStatusMutation,
  useCompleteSessionMutation: hookMocks.useCompleteSessionMutation,
  useRecommendedPracticeQuery: hookMocks.useRecommendedPracticeQuery,
  useToggleFavoriteMutation: hookMocks.useToggleFavoriteMutation,
  useTopicQuery: hookMocks.useTopicQuery,
  useSettingsQuery: hookMocks.useSettingsQuery,
  useResolvedTopicContext: hookMocks.useResolvedTopicContext,
}))

vi.mock('../components/ui/toast', () => ({
  useToast: () => vi.fn(),
}))

function renderRoute(entry: string, element: ReactElement) {
  return renderToStaticMarkup(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/topic/:topicId/summary" element={element} />
        <Route path="/topic/:topicId/practice" element={element} />
        <Route path="/topic/:topicId/assets" element={element} />
      </Routes>
    </MemoryRouter>,
  )
}

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}{location.search}</div>
}

async function renderInteractiveSummary(entry: string) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/topic/:topicId/summary" element={<><LocationProbe /><SummaryPage /></>} />
          <Route path="/topic/:topicId/learn" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    )
  })

  return {
    container,
    root,
    getLocation: () => container.querySelector('[data-testid="location"]')?.textContent || '',
  }
}

describe('route page regressions', () => {
  afterEach(() => {
    vi.clearAllMocks()
    hookMocks.useSettingsQuery.mockReturnValue({ data: null })
    hookMocks.useRecommendedPracticeQuery.mockReturnValue({ data: null })
    hookMocks.useResolvedTopicContext.mockReturnValue({ node_id: null, topic_id: 'tp_graph' })
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
      practice_state: 'idle',
      practice_draft: '',
      sidebar_collapsed: false,
    })
  })

  it('shows a partial-summary warning instead of fake precise session stats', () => {
    hookMocks.useSessionSummaryQuery.mockReturnValue({
      data: {
        session_id: 'ss_partial',
        topic_id: 'tp_graph',
        status: 'completed',
        summary: '仅恢复了规则型摘要',
        synthesis: {
          mainline_summary: '',
          key_takeaways: [],
          next_recommendations: [],
          review_items_created: 0,
          new_assets_count: 0,
          covered_scope: '',
          skippable_nodes: [],
          review_candidates: [],
        },
        partial_summary: true,
      },
    })

    const markup = renderRoute('/topic/tp_graph/summary?sessionId=ss_partial', <SummaryPage />)

    expect(markup).toContain('详细收束信息暂不可用')
    expect(markup).not.toContain('新增表达资产')
    expect(markup).not.toContain('复习候选')
  })

  it('renders an explicit empty state when practice starts without a node id', () => {
    hookMocks.useNodeDetailQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    hookMocks.useGetPracticePromptMutation.mockReturnValue({ mutateAsync: vi.fn() })
    hookMocks.useSubmitPracticeMutation.mockReturnValue({ mutateAsync: vi.fn() })
    hookMocks.useSaveExpressionAssetMutation.mockReturnValue({ mutateAsync: vi.fn() })
    hookMocks.useExpressionAssetsQuery.mockReturnValue({ data: [] })
    hookMocks.usePracticeAttemptsQuery.mockReturnValue({ data: [] })
    hookMocks.useUpdateNodeStatusMutation.mockReturnValue({ mutate: vi.fn() })
    hookMocks.useCompleteSessionMutation.mockReturnValue({ mutateAsync: vi.fn() })

    const markup = renderRoute('/topic/tp_graph/practice', <PracticePage />)

    expect(markup).toContain('请选择一个节点后再开始练习')
    expect(markup).toContain('返回学习')
  })

  it('routes empty assets state back to learn when no practiceable node is available', () => {
    hookMocks.useExpressionAssetsQuery.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    })
    hookMocks.useToggleFavoriteMutation.mockReturnValue({ mutate: vi.fn() })
    hookMocks.useTopicQuery.mockReturnValue({ data: null })

    const markup = renderRoute('/topic/tp_graph/assets', <AssetsPage />)

    expect(markup).toContain('暂无表达资产')
    expect(markup).toContain('返回学习')
    expect(markup).not.toContain('前往练习')
  })

  it('keeps the session id when retrying from a partial summary warning', async () => {
    hookMocks.useSessionSummaryQuery.mockReturnValue({
      data: {
        session_id: 'ss_partial',
        topic_id: 'tp_graph',
        status: 'completed',
        summary: '仅恢复了规则型摘要',
        synthesis: {
          mainline_summary: '',
          key_takeaways: [],
          next_recommendations: [],
          review_items_created: 0,
          new_assets_count: 0,
          covered_scope: '',
          skippable_nodes: [],
          review_candidates: [],
        },
        partial_summary: true,
      },
    })

    const view = await renderInteractiveSummary('/topic/tp_graph/summary?sessionId=ss_partial')
    const retryButton = Array.from(view.container.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('返回学习页重新完成会话'))

    expect(retryButton).toBeTruthy()

    await act(async () => {
      retryButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(view.getLocation()).toBe('/topic/tp_graph/learn?sessionId=ss_partial')

    await act(async () => {
      view.root.unmount()
    })
    view.container.remove()
  })
})
