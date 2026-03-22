import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { PracticeState, GraphView, EdgeType } from '../types'

interface AppState {
  // Legacy current context IDs. Runtime views should derive from route/query data.
  current_topic_id: string | null
  current_node_id: string | null
  current_session_id: string | null
  session_restored: boolean

  // Graph view
  graph_view: GraphView
  graph_sidebar_open: boolean
  graph_selected_node_id: string | null
  graph_edge_filters: Set<EdgeType>
  graph_collapsed_node_ids: Set<string>
  graph_show_edge_filter: boolean

  // Practice state machine
  practice_state: PracticeState
  practice_draft: string

  // Sidebar
  sidebar_collapsed: boolean

  // Actions
  setCurrentTopic: (id: string | null) => void
  setCurrentNode: (id: string | null) => void
  setCurrentSession: (id: string | null) => void
  setGraphView: (view: GraphView) => void
  setGraphSidebarOpen: (open: boolean) => void
  setGraphSelectedNode: (id: string | null) => void
  toggleGraphEdgeFilter: (type: EdgeType) => void
  clearGraphEdgeFilters: () => void
  toggleGraphCollapsedNode: (nodeId: string) => void
  setGraphShowEdgeFilter: (show: boolean) => void
  setPracticeState: (state: PracticeState) => void
  setPracticeDraft: (text: string) => void
  resetPractice: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
}

const initialState = {
  current_topic_id: null,
  current_node_id: null,
  current_session_id: null,
  session_restored: false,
  graph_view: 'mainline' as GraphView,
  graph_sidebar_open: true,
  graph_selected_node_id: null,
  graph_edge_filters: new Set<EdgeType>(),
  graph_collapsed_node_ids: new Set<string>(),
  graph_show_edge_filter: false,
  practice_state: 'idle' as PracticeState,
  practice_draft: '',
  sidebar_collapsed: false,
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      ...initialState,

      setCurrentTopic: (id) => set({ current_topic_id: id }),
      setCurrentNode: (id) => set({ current_node_id: id }),
      setCurrentSession: (id) => set({ current_session_id: id }),
      setGraphView: (view) => set({ graph_view: view }),
      setGraphSidebarOpen: (open) => set({ graph_sidebar_open: open }),
      setGraphSelectedNode: (id) => set({ graph_selected_node_id: id }),
      toggleGraphEdgeFilter: (type) => set((s) => {
        const next = new Set(s.graph_edge_filters)
        if (next.has(type)) next.delete(type)
        else next.add(type)
        return { graph_edge_filters: next }
      }),
      clearGraphEdgeFilters: () => set({ graph_edge_filters: new Set() }),
      toggleGraphCollapsedNode: (nodeId) => set((s) => {
        const next = new Set(s.graph_collapsed_node_ids)
        if (next.has(nodeId)) next.delete(nodeId)
        else next.add(nodeId)
        return { graph_collapsed_node_ids: next }
      }),
      setGraphShowEdgeFilter: (show) => set({ graph_show_edge_filter: show }),
      setPracticeState: (state) => set({ practice_state: state }),
      setPracticeDraft: (text) => set({ practice_draft: text }),
      resetPractice: () => set({ practice_state: 'idle', practice_draft: '' }),
      setSidebarCollapsed: (collapsed) => set({ sidebar_collapsed: collapsed }),
    }),
    {
      name: 'axon-app-store',
      version: 1,
      migrate: (persistedState, version) => {
        const state = (persistedState as Record<string, unknown>)?.state as Record<string, unknown> | undefined
        if (!state) {
          return persistedState as unknown as AppState
        }

        // Version 0 (pre-migrate) resets session-scoped fields
        if (version < 1) {
          return {
            ...state,
            current_topic_id: null,
            current_node_id: null,
            current_session_id: null,
          } as unknown as AppState
        }

        return state as unknown as AppState
      },
      partialize: (state) => ({
        sidebar_collapsed: state.sidebar_collapsed,
        graph_view: state.graph_view,
      }),
    },
  ),
)
