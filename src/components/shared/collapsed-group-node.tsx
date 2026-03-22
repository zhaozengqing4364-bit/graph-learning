import { memo } from 'react'
import { Handle, Position, useReactFlow, type NodeProps } from '@xyflow/react'
import { useAppStore } from '../../stores'

export function CollapsedGroupNode({ id, data }: NodeProps) {
  const { fitView } = useReactFlow()
  const toggleGraphCollapsedNode = useAppStore((s) => s.toggleGraphCollapsedNode)
  const collapsedCount = (data as { collapsed_count?: number } | undefined)?.collapsed_count

  const handleClick = () => {
    toggleGraphCollapsedNode(id)
    // After expanding, fit view to show the newly visible nodes
    setTimeout(() => fitView({ duration: 300 }), 50)
  }

  return (
    <div
      className="flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-gray-100 border border-gray-300 border-dashed cursor-pointer hover:bg-gray-200 hover:border-gray-400 transition-colors"
      style={{ minWidth: 60 }}
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick() } }}
      title={`点击展开 ${collapsedCount ?? ''} 个隐藏节点`}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#9ca3af', width: 6, height: 6 }} />
      <span className="text-xs text-gray-500 font-medium">
        +{collapsedCount ?? '...'}
      </span>
      <Handle type="source" position={Position.Right} style={{ background: '#9ca3af', width: 6, height: 6 }} />
    </div>
  )
}

export default memo(CollapsedGroupNode)
