import type { AbilityRecord } from '../../types'
import { ABILITY_DIMENSIONS } from '../../types'

interface AbilityRadarProps {
  ability: AbilityRecord | null
  size?: number
  className?: string
}

export function AbilityRadar({ ability, size = 200, className = '' }: AbilityRadarProps) {
  if (!ability) return <div className={`flex items-center justify-center text-xs text-gray-400 ${className}`}>暂无能力数据</div>
  const cx = size / 2
  const cy = size / 2
  const r = size / 2 - 30
  const levels = [0.2, 0.4, 0.6, 0.8, 1.0]
  const dims = ABILITY_DIMENSIONS
  const n = dims.length

  const getPoint = (index: number, fraction: number) => {
    const angle = (Math.PI * 2 * index) / n - Math.PI / 2
    return {
      x: cx + r * fraction * Math.cos(angle),
      y: cy + r * fraction * Math.sin(angle),
    }
  }

  const dataPoints = dims.map((d, i) => getPoint(i, Math.max(0.05, ability[d.key] / 100)))
  const dataPath = dataPoints.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ') + ' Z'

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className}>
      {/* Grid levels */}
      {levels.map((level) => (
        <polygon
          key={level}
          points={dims.map((_, i) => { const p = getPoint(i, level); return `${p.x},${p.y}` }).join(' ')}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="0.5"
        />
      ))}
      {/* Axis lines */}
      {dims.map((_, i) => {
        const p = getPoint(i, 1)
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e2e8f0" strokeWidth="0.5" />
      })}
      {/* Data polygon */}
      <path d={dataPath} fill="rgba(99, 102, 241, 0.15)" stroke="#6366f1" strokeWidth="1.5" />
      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#6366f1" />
      ))}
      {/* Labels */}
      {dims.map((d, i) => {
        const p = getPoint(i, 1.15)
        return (
          <text key={i} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle" className="text-[10px] fill-gray-500">
            {d.label}
          </text>
        )
      })}
    </svg>
  )
}

// Simple bar version for inline use
interface AbilityBarsProps {
  ability: AbilityRecord | null
  className?: string
}

export function AbilityBars({ ability, className = '' }: AbilityBarsProps) {
  if (!ability) return <div className={`text-xs text-gray-400 ${className}`}>暂无能力数据</div>
  return (
    <div className={`space-y-2 ${className}`}>
      {ABILITY_DIMENSIONS.map((d) => (
        <div key={d.key} className="flex items-center gap-2">
          <span className="text-xs text-gray-500 w-10 text-right shrink-0">{d.label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-2">
            <div
              className="bg-indigo-500 rounded-full h-full transition-all duration-300"
              style={{ width: `${Math.min(100, ability[d.key] || 0)}%` }}
            />
          </div>
          <span className="text-xs text-gray-400 w-7 text-right">{ability[d.key] || 0}</span>
        </div>
      ))}
    </div>
  )
}
