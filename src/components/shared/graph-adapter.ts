import type { Node, Edge } from '@xyflow/react'
import type { GraphData, GraphNode, GraphEdge, EdgeType } from '../../types'

const RELATION_COLORS: Record<EdgeType, string> = {
  PREREQUISITE: '#6366f1',
  CONTRASTS: '#f59e0b',
  VARIANT_OF: '#8b5cf6',
  APPLIES_IN: '#10b981',
  EXTENDS: '#3b82f6',
  MISUNDERSTOOD_AS: '#ef4444',
  EVIDENCED_BY: '#94a3b8',
}

const NODE_STATUS_COLORS: Record<string, string> = {
  unseen: '#e2e8f0',
  browsed: '#93c5fd',
  learning: '#818cf8',
  practiced: '#6ee7b7',
  review_due: '#fbbf24',
  mastered: '#34d399',
}

function edgeIdWithFallback(edge: GraphEdge, index: number) {
  const explicitId = edge.edge_id?.trim() || ''
  if (explicitId) {
    return explicitId
  }

  return `fallback:${edge.source_node_id}:${edge.relation_type}:${edge.target_node_id}:${index}`
}

export function graphToReactFlow(data: GraphData & { meta?: { current_node_id?: string } }, currentNodeId?: string): { nodes: Node[]; edges: Edge[] } {
  const metaCurrentNodeId = data.meta?.current_node_id
  const nodes: Node[] = data.nodes.map((gn: GraphNode) => ({
    id: gn.node_id,
    position: { x: 0, y: 0 }, // will be laid out by dagre or react flow
    data: {
      label: gn.name,
      status: gn.status,
      importance: gn.importance,
      is_mainline: gn.is_mainline,
      is_current: gn.node_id === currentNodeId || gn.node_id === metaCurrentNodeId,
      is_collapsed: gn.is_collapsed,
      collapsed_count: gn.collapsed_count,
    },
    style: {
      background: gn.is_collapsed ? '#f1f5f9' : NODE_STATUS_COLORS[gn.status] || '#e2e8f0',
      border: gn.node_id === currentNodeId || gn.node_id === metaCurrentNodeId
        ? '2px solid #4f46e5'
        : '1px solid #d1d5db',
      borderRadius: 8,
      padding: '6px 12px',
      fontSize: 12,
      fontWeight: gn.is_mainline ? 600 : 400,
      opacity: gn.is_mainline ? 1 : 0.75,
      width: 'auto',
      maxWidth: 160,
      textAlign: 'center' as const,
    },
    type: gn.is_collapsed ? 'collapsedGroup' : 'knowledgeNode',
  }))

  const edges: Edge[] = data.edges.map((ge: GraphEdge, index) => ({
    id: edgeIdWithFallback(ge, index),
    source: ge.source_node_id,
    target: ge.target_node_id,
    type: ge.is_misunderstood ? 'smoothstep' : 'default',
    animated: ge.relation_type === 'MISUNDERSTOOD_AS',
    style: {
      stroke: RELATION_COLORS[ge.relation_type] || '#9ca3af',
      strokeWidth: ge.is_misunderstood ? 2 : 1.5,
      strokeDasharray: ge.relation_type === 'MISUNDERSTOOD_AS' ? '5 3' : undefined,
    },
    label: relationTypeLabel(ge.relation_type),
    data: { tooltip: relationTypeDescription(ge.relation_type) },
    labelStyle: { fontSize: 10, fill: '#9ca3af' },
    labelBgStyle: { fill: '#fff', fillOpacity: 0.8 },
    labelBgPadding: [2, 4] as [number, number],
    labelBgBorderRadius: 2,
  }))

  return { nodes, edges }
}

function relationTypeLabel(t: EdgeType): string {
  const map: Record<EdgeType, string> = {
    PREREQUISITE: '前置',
    CONTRASTS: '对比',
    VARIANT_OF: '变体',
    APPLIES_IN: '应用',
    EXTENDS: '扩展',
    MISUNDERSTOOD_AS: '误解',
    EVIDENCED_BY: '证据',
  }
  return map[t] || t
}

function relationTypeDescription(t: EdgeType): string {
  const map: Record<EdgeType, string> = {
    PREREQUISITE: '前置依赖 — 需要先学习此节点',
    CONTRASTS: '对比关系 — 与此节点形成对比',
    VARIANT_OF: '变体 — 此节点的变体形式',
    APPLIES_IN: '应用场景 — 此节点可应用于此领域',
    EXTENDS: '扩展 — 在此节点基础上延伸',
    MISUNDERSTOOD_AS: '常见误解 — 容易与此节点混淆',
    EVIDENCED_BY: '证据 — 有证据支持此关系',
  }
  return map[t] || t
}

export { RELATION_COLORS, NODE_STATUS_COLORS, relationTypeLabel }
