import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ReactFlow, Background, Controls, MiniMap,
  type Node as FlowNode, type Edge as FlowEdge, type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { GitBranch, BookOpen, PenTool, AlertTriangle, Target, ChevronDown, ChevronUp, Filter, Clock, X, ArrowLeft, Search } from 'lucide-react'
import { useGraphQuery, useNodeDetailQuery, useNodeAbilityQuery, useResolvedTopicContext, useSettingsQuery } from '../hooks'
import { useAppStore } from '../stores'
import { Button, Badge, LoadingSkeleton, ErrorState, EmptyState } from '../components/shared'
import { graphToReactFlow } from '../components/shared/graph-adapter'
import { CollapsedGroupNode } from '../components/shared/collapsed-group-node'
import { AbilityBars } from '../components/shared/ability-radar'
import type { GraphView, EdgeType } from '../types'

interface KnowledgeNodeData {
  label?: string
  status?: string
  importance?: number
  is_mainline?: boolean
  is_current?: boolean
  ability_summary?: string
  [key: string]: unknown
}

function KnowledgeNode({ data }: { data: KnowledgeNodeData }) {
  const label = String(data?.label ?? '')
  const statusLabels: Record<string, string> = {
    mastered: '已掌握', learning: '学习中', practiced: '已练习', unseen: '未学习',
  }
  const statusText = statusLabels[String(data?.status ?? '')] || String(data?.status ?? 'unknown')
  const tooltip = data?.ability_summary
    || `${statusText} · 重要度 ${data?.importance ?? '-'}/5${data?.is_mainline ? ' · 主干节点' : ''}`
  return (
    <div title={tooltip} style={{ fontSize: 12, textAlign: 'center', whiteSpace: 'nowrap' }}>
      {label}
    </div>
  )
}

const nodeTypes = { collapsedGroup: CollapsedGroupNode, knowledgeNode: KnowledgeNode }

function GraphSearchBar({ nodes, onNodeSelect }: { nodes: FlowNode[]; onNodeSelect: (nodeId: string) => void }) {
  const [query, setQuery] = useState('')
  const [showResults, setShowResults] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  const filtered = useMemo(() => {
    if (!query.trim()) return []
    const q = query.trim().toLowerCase()
    return nodes.filter((n) => {
      const label = String(n.data?.label ?? '').toLowerCase()
      return label.includes(q)
    }).slice(0, 8)
  }, [query, nodes])

  useEffect(() => {
    if (!showResults) return
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target
      if (
        !(target instanceof globalThis.Node) ||
        (inputRef.current && !inputRef.current.contains(target)) ||
        (resultsRef.current && !resultsRef.current.contains(target))
      ) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showResults])

  return (
    <div className="relative" ref={resultsRef}>
      <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5">
        <Search size={12} className="text-gray-400 shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowResults(true) }}
          onFocus={() => setShowResults(true)}
          placeholder="搜索节点…"
          className="w-28 text-xs bg-transparent outline-none placeholder:text-gray-400"
        />
      </div>
      {showResults && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-[180px] max-h-60 overflow-auto">
          {filtered.map((node) => (
            <button
              key={node.id}
              onClick={() => {
                onNodeSelect(node.id)
                setQuery('')
                setShowResults(false)
              }}
              className="block w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              {String(node.data?.label || node.id)}
            </button>
          ))}
        </div>
      )}
      {showResults && query.trim() && filtered.length === 0 && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 px-3 py-2 text-xs text-gray-400">
          未找到匹配节点
        </div>
      )}
    </div>
  )
}

const dagreLayout = (nodes: FlowNode[], edges: FlowEdge[]) => {
  const nodeMap = new Map(nodes.map((n) => [n.id, { ...n, deps: new Set<string>() }]))
  // Build adjacency list: parent -> children
  const childrenOf = new Map<string, FlowNode[]>()
  for (const e of edges) {
    const node = nodeMap.get(e.target)
    if (node) node.deps.add(e.source)
    const child = nodeMap.get(e.target)
    if (child) {
      const existing = childrenOf.get(e.source)
      if (existing) existing.push(child)
      else childrenOf.set(e.source, [child])
    }
  }

  const pos = new Map<string, { x: number; y: number }>()
  let layer = 0
  let currentLayer = nodes.filter((n) => {
    const nd = nodeMap.get(n.id)
    return nd && nd.deps.size === 0
  })
  const visited = new Set<string>()

  while (currentLayer.length > 0) {
    const nextLayer: typeof currentLayer = []
    for (let i = 0; i < currentLayer.length; i++) {
      const n = currentLayer[i]
      if (visited.has(n.id)) continue
      visited.add(n.id)
      pos.set(n.id, {
        x: i * 220 - (currentLayer.length * 220) / 2 + 400,
        y: layer * 120 + 50,
      })
      const children = childrenOf.get(n.id)
      if (children) nextLayer.push(...children)
    }
    currentLayer = nextLayer
    layer++
  }

  for (let i = 0; i < nodes.length; i++) {
    if (!visited.has(nodes[i].id)) {
      pos.set(nodes[i].id, { x: i * 200 + 200, y: layer * 120 + 50 })
    }
  }

  return nodes.map((n) => ({
    ...n,
    position: pos.get(n.id) || { x: 0, y: 0 },
  }))
}

export function GraphPage() {
  const { topicId } = useParams<{ topicId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const view = (searchParams.get('view') as GraphView) || 'mainline'
  const focusNodeId = searchParams.get('focus') || undefined

  const {
    setGraphView, graph_selected_node_id, setGraphSelectedNode,
    graph_sidebar_open, setGraphSidebarOpen,
    graph_edge_filters, toggleGraphEdgeFilter, clearGraphEdgeFilters,
    graph_collapsed_node_ids, toggleGraphCollapsedNode, graph_show_edge_filter, setGraphShowEdgeFilter,
  } = useAppStore()
  const { data: settings } = useSettingsQuery()
  const { nodeId: currentNodeId } = useResolvedTopicContext()

  const [maxDepthOverride, setMaxDepthOverride] = useState<number | null>(null)
  const maxDepth = maxDepthOverride ?? settings?.max_graph_depth ?? 3
  const [edgeTooltip, setEdgeTooltip] = useState<{ text: string; x: number; y: number } | null>(null)

  const EDGE_TYPE_LABELS: Record<EdgeType, string> = {
    PREREQUISITE: '前置',
    CONTRASTS: '对比',
    VARIANT_OF: '变体',
    APPLIES_IN: '应用',
    EXTENDS: '扩展',
    MISUNDERSTOOD_AS: '误解',
    EVIDENCED_BY: '证据',
  }

  const { data: graphData, isLoading, error, refetch: refetchGraph } = useGraphQuery(topicId!, {
    view,
    focus_node_id: focusNodeId,
    max_depth: maxDepth,
  })

  const { data: selectedNodeDetail } = useNodeDetailQuery(
    topicId!,
    graph_selected_node_id || '',
  )

  const { data: selectedNodeAbility } = useNodeAbilityQuery(
    topicId!,
    graph_selected_node_id || '',
  )

  const { rfNodes, rfEdges, totalNodeCount, collapsedCount } = useMemo(() => {
    if (!graphData) return { rfNodes: [], rfEdges: [], totalNodeCount: 0, collapsedCount: 0 }
    const totalNodeCount = graphData.nodes.length
    let limitedNodes = graphData.nodes
    let collapsedCount = 0
    // When over 30 nodes, group excess into a CollapsedGroupNode
    if (limitedNodes.length > 30) {
      const sorted = [...limitedNodes].sort((a, b) => {
        // Mainline nodes first
        const aMain = a.is_mainline ? 1 : 0
        const bMain = b.is_mainline ? 1 : 0
        if (aMain !== bMain) return bMain - aMain
        // Then by importance descending
        return (b.importance || 2) - (a.importance || 2)
      })
      const kept = sorted.slice(0, 29) // keep 29 visible nodes
      const hidden = sorted.slice(29)
      collapsedCount = hidden.length
      // Create a collapsed group node to represent hidden nodes
      if (hidden.length > 0) {
        const collapsedNode = {
          node_id: `collapsed-${topicId}`,
          name: `+${hidden.length} 个节点`,
          summary: hidden.slice(0, 3).map(n => n.name).join('、') + (hidden.length > 3 ? ' 等' : ''),
          is_collapsed: true,
          collapsed_count: hidden.length,
          is_mainline: false,
          status: 'unseen' as const,
          importance: 1,
        }
        limitedNodes = [...kept, collapsedNode]
      }
    }
    const limitedData = { ...graphData, nodes: limitedNodes }

    // Filter edges by EdgeType if filters are active
    let edges = limitedData.edges
    if (graph_edge_filters.size > 0) {
      edges = edges.filter((e) => graph_edge_filters.has(e.relation_type))
    }

    // Filter out collapsed node children
    if (graph_collapsed_node_ids.size > 0) {
      const collapsedChildren = new Set<string>()
      for (const cid of graph_collapsed_node_ids) {
        for (const e of edges) {
          if (e.source_node_id === cid) {
            collapsedChildren.add(e.target_node_id)
          }
        }
      }
      edges = edges.filter((e) => !collapsedChildren.has(e.target_node_id))
    }

    const adapted = graphToReactFlow({ ...limitedData, edges }, focusNodeId)
    const laid = dagreLayout(adapted.nodes, adapted.edges)
    return { rfNodes: laid, rfEdges: adapted.edges, totalNodeCount, collapsedCount }
  }, [graphData, focusNodeId, graph_edge_filters, graph_collapsed_node_ids, topicId])

  const handleNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    // Skip virtual collapsed group nodes — they have no real node detail
    if (node.id.startsWith('collapsed-')) return
    setGraphSelectedNode(node.id)
    setGraphSidebarOpen(true)
  }, [setGraphSelectedNode, setGraphSidebarOpen])

  const handleNodeDoubleClick: NodeMouseHandler = useCallback((_event, node) => {
    navigate(`/topic/${topicId}/learn?nodeId=${node.id}`)
  }, [navigate, topicId])

  const handleViewChange = useCallback((v: GraphView) => {
    setGraphView(v)
    setSearchParams((prev) => {
      prev.set('view', v)
      return prev
    })
  }, [setGraphView, setSearchParams])

  const handleEdgeMouseEnter = useCallback((_event: React.MouseEvent, edge: FlowEdge) => {
    const tooltip = (edge.data as Record<string, unknown> | undefined)?.tooltip as string | undefined
    if (tooltip) {
      setEdgeTooltip({ text: tooltip, x: _event.clientX, y: _event.clientY })
    }
  }, [])

  const handleEdgeMouseLeave = useCallback(() => {
    setEdgeTooltip(null)
  }, [])

  // Auto-switch to mainline view when nodes exceed 30
  const autoSwitched = useRef(false)
  const edgeFilterRef = useRef<HTMLDivElement>(null)
  const graphNodeCount = graphData?.nodes.length ?? 0

  useEffect(() => {
    if (graphNodeCount > 30 && view !== 'mainline') {
      handleViewChange('mainline')
      if (!autoSwitched.current) {
        autoSwitched.current = true
      }
    }
  }, [graphNodeCount, handleViewChange, view])

  useEffect(() => {
    if (!graph_show_edge_filter) return
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target
      if (edgeFilterRef.current && (!(target instanceof globalThis.Node) || !edgeFilterRef.current.contains(target))) {
        setGraphShowEdgeFilter(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [graph_show_edge_filter, setGraphShowEdgeFilter])

  useEffect(() => {
    setGraphView(view)
  }, [setGraphView, view])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
        <div className="relative w-48 h-48 rounded-xl bg-gray-100 animate-pulse" />
        <div className="flex gap-3">
          <div className="h-3 w-20 rounded bg-gray-200 animate-pulse" />
          <div className="h-3 w-16 rounded bg-gray-200 animate-pulse" />
          <div className="h-3 w-24 rounded bg-gray-200 animate-pulse" />
        </div>
        <p className="text-sm text-gray-400">加载知识图谱...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <ErrorState message="图谱加载失败" onRetry={() => { void refetchGraph() }} />
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<GitBranch size={48} />}
          title="暂无图谱数据"
          description="先在学习页中展开节点，图谱会自动生成"
          action={
            <Button onClick={() => navigate(`/topic/${topicId}/learn`)}>
              前往学习页
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-48px)] flex">
      {/* Graph Canvas */}
      <div className="flex-1 relative">
        {/* Toolbar */}
        <div className="absolute top-4 left-4 z-10 flex gap-2 items-center">
          <button
            onClick={() => navigate(`/topic/${topicId}/learn`)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-gray-600 border border-gray-200 hover:bg-gray-50 transition-colors"
            aria-label="返回学习页"
          >
            <ArrowLeft size={14} />
            返回
          </button>
          {(['mainline', 'full', 'prerequisite', 'misconception'] as GraphView[]).map((v) => (
            <button
              key={v}
              onClick={() => handleViewChange(v)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                view === v
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {{ mainline: '主干', full: '全图', prerequisite: '前置', misconception: '误解' }[v]}
            </button>
          ))}
          <div className="flex items-center gap-2 ml-3 bg-white border border-gray-200 rounded-lg px-3 py-1.5">
            <span className="text-xs text-gray-500">深度</span>
            <input
              type="range"
              min={1}
              max={5}
              value={maxDepth}
              onChange={(event) => setMaxDepthOverride(Number(event.target.value))}
              className="w-20 h-1 accent-indigo-600"
            />
            <span className="text-xs font-medium text-gray-700 w-4 text-center">{maxDepth}</span>
          </div>
          {currentNodeId && (
            <button
              onClick={() => {
                setSearchParams((prev) => { prev.set('focus', currentNodeId); return prev })
              }}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-indigo-600 border border-indigo-200 hover:bg-indigo-50 transition-colors"
            >
              <Target size={12} />
              当前节点
            </button>
          )}

          {/* Edge type filter toggle */}
          <div className="relative" ref={edgeFilterRef}>
            <button
              onClick={() => setGraphShowEdgeFilter(!graph_show_edge_filter)}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                graph_show_edge_filter ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              <Filter size={12} />
              关系类型
              {graph_edge_filters.size > 0 && (
                <span className="ml-0.5 bg-white text-indigo-600 rounded-full w-4 h-4 text-[10px] flex items-center justify-center">{graph_edge_filters.size}</span>
              )}
            </button>
            {graph_show_edge_filter && (
              <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-20 min-w-[120px]">
                {(Object.entries(EDGE_TYPE_LABELS) as [EdgeType, string][]).map(([type, label]) => (
                  <label key={type} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-50 cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={graph_edge_filters.has(type)}
                      onChange={() => toggleGraphEdgeFilter(type)}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-gray-700">{label}</span>
                  </label>
                ))}
                {graph_edge_filters.size > 0 && (
                  <button
                    className="w-full text-xs text-indigo-600 hover:text-indigo-700 mt-1 pt-1 border-t border-gray-100"
                    onClick={() => clearGraphEdgeFilters()}
                  >
                    清除筛选
                  </button>
                )}
              </div>
            )}
          </div>

          <GraphSearchBar
            nodes={rfNodes}
            onNodeSelect={(nodeId) => {
              setSearchParams((prev) => { prev.set('focus', nodeId); return prev })
              setGraphSelectedNode(nodeId)
              setGraphSidebarOpen(true)
            }}
          />
        </div>

        {/* 30-node limit warning */}
        {totalNodeCount > 30 && (
          <div className="absolute bottom-4 left-4 z-10 flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertTriangle size={14} className="text-amber-500" />
            <span className="text-xs text-amber-700">
              节点共 {totalNodeCount} 个，已折叠 {collapsedCount} 个支线节点。切换到"全图"视图查看全部。
            </span>
          </div>
        )}

        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodeClick={handleNodeClick}
          onNodeDoubleClick={handleNodeDoubleClick}
          onEdgeMouseEnter={handleEdgeMouseEnter}
          onEdgeMouseLeave={handleEdgeMouseLeave}
          nodeTypes={nodeTypes}
          fitView
          className="bg-gray-50"
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls />
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
          />
        </ReactFlow>

        {edgeTooltip && (
          <div
            className="fixed z-50 px-2 py-1 text-xs bg-gray-900 text-white rounded shadow-lg pointer-events-none"
            style={{ left: edgeTooltip.x + 12, top: edgeTooltip.y - 8 }}
          >
            {edgeTooltip.text}
          </div>
        )}
      </div>

      {/* Sidebar */}
      {graph_sidebar_open && graph_selected_node_id && (
        <div className="w-80 border-l border-gray-200 bg-white overflow-auto">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">节点详情</h3>
            <button onClick={() => setGraphSidebarOpen(false)} className="text-gray-400 hover:text-gray-600" aria-label="关闭详情面板">
              <X size={16} />
            </button>
          </div>
          <div className="p-4">
            {selectedNodeDetail ? (
              <div className="space-y-4">
                <h4 className="text-base font-bold text-gray-900">{selectedNodeDetail.node.name}</h4>
                <p className="text-sm text-gray-600">{selectedNodeDetail.node.summary}</p>
                {selectedNodeDetail.node.why_it_matters && (
                  <p className="text-xs text-indigo-600 bg-indigo-50 rounded px-2 py-1">{selectedNodeDetail.node.why_it_matters}</p>
                )}
                <div className="flex items-center gap-2">
                  <Badge variant={selectedNodeDetail.node.status === 'mastered' ? 'success' : selectedNodeDetail.node.status === 'learning' ? 'info' : 'default'}>
                    {selectedNodeDetail.node.status}
                  </Badge>
                  <span className="text-xs text-gray-400">重要度 {selectedNodeDetail.node.importance}/5</span>
                </div>
                {selectedNodeAbility && (
                  <AbilityBars ability={selectedNodeAbility} />
                )}
                {selectedNodeDetail.prerequisites.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">前置节点</p>
                    {selectedNodeDetail.prerequisites.map((p) => (
                      <p key={p.node_id} className="text-xs text-gray-600">{p.name}</p>
                    ))}
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    onClick={() => navigate(`/topic/${topicId}/learn?nodeId=${graph_selected_node_id}`)}
                  >
                    <BookOpen size={14} />
                    学习
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => navigate(`/topic/${topicId}/practice?nodeId=${graph_selected_node_id}`)}
                  >
                    <PenTool size={14} />
                    练习
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const sourceNodeId = focusNodeId || currentNodeId || graph_selected_node_id
                      navigate(`/topic/${topicId}/learn?nodeId=${graph_selected_node_id}&deferFrom=${sourceNodeId}`)
                    }}
                  >
                    <Clock size={14} />
                    稍后学
                  </Button>
                  <button
                    onClick={() => toggleGraphCollapsedNode(graph_selected_node_id)}
                    className="p-1.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
                    aria-label={graph_collapsed_node_ids.has(graph_selected_node_id) ? '展开子节点' : '折叠子节点'}
                    title={graph_collapsed_node_ids.has(graph_selected_node_id) ? '展开子节点' : '折叠子节点'}
                  >
                    {graph_collapsed_node_ids.has(graph_selected_node_id) ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                  </button>
                </div>
              </div>
            ) : (
              <LoadingSkeleton lines={4} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
