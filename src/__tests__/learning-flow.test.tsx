import { act } from 'react'
import type { ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ArticleWorkspacePage } from '../features/article-workspace/article-workspace-page'
import type { Settings, Topic } from '../types'

const hookMocks = vi.hoisted(() => ({
  toast: vi.fn(),
  useTopicQuery: vi.fn(),
  useEntryNodeQuery: vi.fn(),
  useGraphQuery: vi.fn(),
  useMainlineQuery: vi.fn(),
  useWorkspaceBundleQuery: vi.fn(),
  useWorkspaceSearchQuery: vi.fn(),
  useNodeDetailQuery: vi.fn(),
  useBacklinksQuery: vi.fn(),
  useSettingsQuery: vi.fn(),
  useCreateSourceArticleMutation: vi.fn(),
  useUpdateSourceArticleMutation: vi.fn(),
  useUpsertConceptNoteMutation: vi.fn(),
  useSaveReadingStateMutation: vi.fn(),
  useCreateConceptCandidateMutation: vi.fn(),
  useConfirmConceptCandidateMutation: vi.fn(),
  useIgnoreConceptCandidateMutation: vi.fn(),
  useGenerateArticleMutation: vi.fn(),
  useStartSessionMutation: vi.fn(),
  useVisitNodeMutation: vi.fn(),
  useCompleteSessionMutation: vi.fn(),
}))

vi.mock('../hooks/use-queries', () => ({
  useTopicQuery: hookMocks.useTopicQuery,
  useEntryNodeQuery: hookMocks.useEntryNodeQuery,
  useGraphQuery: hookMocks.useGraphQuery,
  useMainlineQuery: hookMocks.useMainlineQuery,
  useWorkspaceBundleQuery: hookMocks.useWorkspaceBundleQuery,
  useWorkspaceSearchQuery: hookMocks.useWorkspaceSearchQuery,
  useNodeDetailQuery: hookMocks.useNodeDetailQuery,
  useBacklinksQuery: hookMocks.useBacklinksQuery,
  useSettingsQuery: hookMocks.useSettingsQuery,
}))

vi.mock('../hooks/use-mutations', () => ({
  useCreateSourceArticleMutation: hookMocks.useCreateSourceArticleMutation,
  useUpdateSourceArticleMutation: hookMocks.useUpdateSourceArticleMutation,
  useUpsertConceptNoteMutation: hookMocks.useUpsertConceptNoteMutation,
  useSaveReadingStateMutation: hookMocks.useSaveReadingStateMutation,
  useCreateConceptCandidateMutation: hookMocks.useCreateConceptCandidateMutation,
  useConfirmConceptCandidateMutation: hookMocks.useConfirmConceptCandidateMutation,
  useIgnoreConceptCandidateMutation: hookMocks.useIgnoreConceptCandidateMutation,
  useGenerateArticleMutation: hookMocks.useGenerateArticleMutation,
  useStartSessionMutation: hookMocks.useStartSessionMutation,
  useVisitNodeMutation: hookMocks.useVisitNodeMutation,
  useCompleteSessionMutation: hookMocks.useCompleteSessionMutation,
}))

vi.mock('../hooks/use-mobile', () => ({
  useIsMobile: () => false,
}))

vi.mock('../components/ui/toast', () => ({
  useToast: () => hookMocks.toast,
}))

vi.mock('../components/ui/button', () => ({
  Button: ({ children, onClick, type = 'button', ...props }: { children?: ReactNode; onClick?: () => void; type?: 'button' | 'submit' | 'reset' }) => (
    <button type={type} onClick={onClick} {...props}>{children}</button>
  ),
}))

vi.mock('../components/ui/textarea', () => ({
  Textarea: (props: Record<string, unknown>) => <textarea {...props} />,
}))

vi.mock('../components/ui/command', () => ({
  Command: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CommandDialog: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CommandEmpty: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CommandGroup: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CommandInput: (props: Record<string, unknown>) => <input {...props} />,
  CommandItem: ({ children, onSelect }: { children?: ReactNode; onSelect?: () => void }) => <button onClick={onSelect}>{children}</button>,
  CommandList: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
}))

vi.mock('../components/ui/drawer', () => ({
  Drawer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  DrawerContent: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  DrawerHeader: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  DrawerTitle: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
}))

vi.mock('../components/ui/sheet', () => ({
  Sheet: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  SheetContent: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
}))

vi.mock('../components/shared/article-renderer', () => ({
  ArticleRenderer: ({ article }: { article?: { title?: string } }) => <div data-testid="article-renderer">{article?.title || 'article'}</div>,
}))

vi.mock('../features/article-workspace/article-header', () => ({
  ArticleHeader: ({ article }: { article: { title: string } }) => <div data-testid="article-header">{article.title}</div>,
}))

vi.mock('../features/article-workspace/article-library-sidebar', () => ({
  ArticleLibrarySidebar: () => <div data-testid="article-library" />,
}))

vi.mock('../features/article-workspace/article-footer-panel', () => ({
  ArticleFooterPanel: () => <div data-testid="article-footer" />,
}))

vi.mock('../features/article-workspace/concept-drawer-content', () => ({
  ConceptDrawerContent: () => <div data-testid="concept-drawer" />,
}))

const TOPIC: Topic = {
  topic_id: 'tp_graph',
  title: '图学习',
  source_type: 'article',
  source_content: '图学习主题',
  learning_intent: 'build_system',
  mode: 'full_system',
  status: 'active',
  current_node_id: 'nd_graph',
  entry_node_id: 'nd_entry',
  last_session_id: undefined,
  total_nodes: 3,
  learned_nodes: 0,
  due_review_count: 0,
  deferred_count: 0,
  created_at: '2026-03-17T00:00:00Z',
  updated_at: '2026-03-17T00:00:00Z',
}

const DEFAULT_SETTINGS: Settings = {
  openai_api_key: '',
  openai_base_url: 'https://api.openai.com/v1',
  openai_model_default: 'gpt-4o',
  openai_embed_model: 'text-embedding-3-small',
  default_model: 'gpt-4o',
  default_learning_intent: 'build_system',
  default_mode: 'full_system',
  max_graph_depth: 3,
  auto_start_practice: false,
  auto_generate_summary: true,
  ollama_enabled: false,
}

const DEFAULT_SUMMARY_RESPONSE = {
  session_id: 'ss_graph',
  topic_id: 'tp_graph',
  status: 'completed',
  summary: '本轮学习完成',
  synthesis: {
    mainline_summary: '主线总结',
    key_takeaways: ['图表示'],
    next_recommendations: [],
    review_items_created: 1,
    new_assets_count: 0,
    covered_scope: '图表示 -> 消息传递',
    skippable_nodes: [],
    review_candidates: [],
  },
}

const defaultMutation = () => ({
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  isPending: false,
  variables: undefined,
})

const mountedRoots: Array<{ root: Root; container: HTMLDivElement }> = []

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}{location.search}</div>
}

async function flushEffects() {
  await act(async () => {
    await Promise.resolve()
  })
}

async function renderWorkspace(entry: string) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  mountedRoots.push({ root, container })

  await act(async () => {
    root.render(
      <MemoryRouter initialEntries={[entry]}>
        <LocationProbe />
        <Routes>
          <Route path="/topic/:topicId/learn" element={<ArticleWorkspacePage />} />
          <Route path="/topic/:topicId/practice" element={<div data-testid="practice-page">practice</div>} />
          <Route path="/topic/:topicId/summary" element={<div data-testid="summary-page">summary</div>} />
        </Routes>
      </MemoryRouter>,
    )
  })

  await flushEffects()
  await flushEffects()
  await flushEffects()
  await flushEffects()

  return {
    container,
    getLocation: () => container.querySelector('[data-testid="location"]')?.textContent || '',
  }
}

function configureWorkspaceMocks(overrides?: {
  settings?: Partial<Settings>
  sessionId?: string
}) {
  const sessionId = overrides?.sessionId || 'ss_graph'
  const settings = { ...DEFAULT_SETTINGS, ...overrides?.settings }
  const startSessionMutation = {
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({
      session_id: sessionId,
      topic_id: TOPIC.topic_id,
      entry_node_id: TOPIC.entry_node_id,
      status: 'active',
      restored: false,
    }),
    isPending: false,
  }
  const visitNodeMutation = {
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue(undefined),
    isPending: false,
  }
  const completeSessionMutation = {
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue(DEFAULT_SUMMARY_RESPONSE),
    isPending: false,
  }

  hookMocks.useTopicQuery.mockReturnValue({ data: TOPIC, isLoading: false, error: null })
  hookMocks.useEntryNodeQuery.mockReturnValue({ data: { node_id: 'nd_entry', name: '入口节点', summary: '入口摘要' } })
  hookMocks.useGraphQuery.mockReturnValue({ data: { nodes: [{ node_id: 'nd_graph', name: '消息传递', importance: 5, status: 'unseen' }], edges: [] } })
  hookMocks.useMainlineQuery.mockReturnValue({ data: { nodes: [{ node_id: 'nd_graph', name: '消息传递', importance: 5, status: 'unseen' }], edges: [] } })
  hookMocks.useWorkspaceBundleQuery.mockReturnValue({
    data: {
      source_articles: [],
      concept_notes: [],
      reading_state: null,
      concept_candidates: [],
    },
    isLoading: false,
    error: null,
  })
  hookMocks.useWorkspaceSearchQuery.mockReturnValue({ data: null })
  hookMocks.useNodeDetailQuery.mockImplementation((_topicId: string, nodeId: string) => ({
    data: nodeId
      ? {
          node: {
            node_id: nodeId,
            name: '消息传递',
            summary: '概念摘要',
            article_body: '概念正文',
            importance: 5,
            status: 'learning',
            topic_id: TOPIC.topic_id,
            created_at: '2026-03-17T00:00:00Z',
            updated_at: '2026-03-17T00:00:00Z',
          },
          prerequisites: [],
          contrasts: [],
          applications: [],
          misunderstandings: [],
          related: [],
          ability: null,
          why_now: '',
        }
      : undefined,
    refetch: vi.fn(),
  }))
  hookMocks.useBacklinksQuery.mockReturnValue({ data: [] })
  hookMocks.useSettingsQuery.mockReturnValue({ data: settings })

  hookMocks.useCreateSourceArticleMutation.mockReturnValue(defaultMutation())
  hookMocks.useUpdateSourceArticleMutation.mockReturnValue(defaultMutation())
  hookMocks.useUpsertConceptNoteMutation.mockReturnValue(defaultMutation())
  hookMocks.useSaveReadingStateMutation.mockReturnValue(defaultMutation())
  hookMocks.useCreateConceptCandidateMutation.mockReturnValue(defaultMutation())
  hookMocks.useConfirmConceptCandidateMutation.mockReturnValue(defaultMutation())
  hookMocks.useIgnoreConceptCandidateMutation.mockReturnValue(defaultMutation())
  hookMocks.useGenerateArticleMutation.mockReturnValue({ ...defaultMutation(), variables: undefined })
  hookMocks.useStartSessionMutation.mockReturnValue(startSessionMutation)
  hookMocks.useVisitNodeMutation.mockReturnValue(visitNodeMutation)
  hookMocks.useCompleteSessionMutation.mockReturnValue(completeSessionMutation)

  return {
    startSessionMutation,
    visitNodeMutation,
    completeSessionMutation,
  }
}

describe('learning flow wiring', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => window.setTimeout(() => callback(0), 0))
    vi.stubGlobal('cancelAnimationFrame', (handle: number) => window.clearTimeout(handle))
  })

  afterEach(async () => {
    while (mountedRoots.length > 0) {
      const mounted = mountedRoots.pop()
      if (!mounted) {
        break
      }

      await act(async () => {
        mounted.root.unmount()
      })
      mounted.container.remove()
    }
    vi.unstubAllGlobals()
  })

  it('starts a session when the learning workspace first loads', async () => {
    const { startSessionMutation } = configureWorkspaceMocks()

    await renderWorkspace('/topic/tp_graph/learn')

    expect(startSessionMutation.mutateAsync).toHaveBeenCalledWith({
      entry_node_id: 'nd_entry',
    })
  })

  it('records a node visit when opening a concept article inside the workspace', async () => {
    const { visitNodeMutation } = configureWorkspaceMocks()

    await renderWorkspace('/topic/tp_graph/learn?article=concept:nd_graph')

    expect(visitNodeMutation.mutateAsync).toHaveBeenCalledWith({
      node_id: 'nd_graph',
      action_type: 'open_node',
    })
  })

  it('auto jumps to practice with sessionId when the setting is enabled', async () => {
    configureWorkspaceMocks({
      settings: {
        auto_start_practice: true,
        auto_generate_summary: false,
      },
    })

    const view = await renderWorkspace('/topic/tp_graph/learn?article=concept:nd_graph')
    const markCompleteButton = Array.from(view.container.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('标记完成'))

    expect(markCompleteButton).toBeTruthy()

    await act(async () => {
      markCompleteButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    await flushEffects()

    expect(view.getLocation()).toContain('/topic/tp_graph/practice?')
    expect(view.getLocation()).toContain('nodeId=nd_graph')
    expect(view.getLocation()).toContain('sessionId=ss_graph')
  })

  it('completes the session and routes to summary when auto summary is enabled', async () => {
    const { completeSessionMutation } = configureWorkspaceMocks({
      settings: {
        auto_start_practice: false,
        auto_generate_summary: true,
      },
    })

    const view = await renderWorkspace('/topic/tp_graph/learn?article=concept:nd_graph&sessionId=ss_graph')
    const markCompleteButton = Array.from(view.container.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('标记完成'))

    expect(markCompleteButton).toBeTruthy()

    await act(async () => {
      markCompleteButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    await flushEffects()

    expect(completeSessionMutation.mutateAsync).toHaveBeenCalledWith({
      generate_summary: true,
      generate_review_items: true,
    })
    expect(view.getLocation()).toContain('/topic/tp_graph/summary?sessionId=ss_graph')
  })
})
