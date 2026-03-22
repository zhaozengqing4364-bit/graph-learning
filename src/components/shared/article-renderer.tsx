import {
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

interface ConceptInfo {
  node_id?: string
  name: string
  summary?: string
  appearance?: 'confirmed' | 'candidate' | 'plain'
}

interface ArticleRendererProps {
  articleId?: string
  body: string
  conceptMap: Record<string, ConceptInfo>
  onConceptClick?: (concept: ConceptInfo) => void
  onMarkConcept?: (selectedText: string) => void
}

const WIKI_LINK_RE = /\[\[(.+?)\]\]/g

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function renderFormattedText(
  articleId: string | undefined,
  text: string,
  renderInline: (value: string) => ReactNode[],
): ReactNode[] {
  const blocks = text.split(/\n\n+/)

  return blocks.map((block, blockIndex) => {
    if (!block.trim()) return null

    const trimmed = block.trim()

    if (trimmed.startsWith('```')) {
      const lines = trimmed.split('\n')
      const code = lines.slice(1, lines.length - (lines[lines.length - 1].trim() === '```' ? 1 : 0)).join('\n')
      return (
        <pre
          key={blockIndex}
          id={articleId ? `${articleId}:paragraph:${blockIndex}` : undefined}
          className="mb-5 overflow-x-auto rounded-3xl border border-[color:var(--border)] bg-[color:var(--card)] p-4 font-mono text-xs leading-6 text-[color:var(--foreground)] shadow-sm"
        >
          {code}
        </pre>
      )
    }

    if (/^#{1,3}\s/.test(trimmed)) {
      const level = trimmed.match(/^(#{1,3})/)?.[1].length || 2
      const content = trimmed.replace(/^#{1,3}\s*/, '')
      const className = level === 1
        ? 'text-3xl'
        : level === 2
          ? 'text-2xl'
          : 'text-xl'
      return (
        <h2
          key={blockIndex}
          id={articleId ? `${articleId}:paragraph:${blockIndex}` : undefined}
          className={`mt-8 mb-4 font-serif ${className} leading-tight text-[color:var(--foreground)]`}
        >
          {renderInline(content)}
        </h2>
      )
    }

    if (/^>\s/.test(trimmed)) {
      const content = trimmed.split('\n').map((line) => line.replace(/^>\s*/, '')).join('\n')
      return (
        <blockquote
          key={blockIndex}
          id={articleId ? `${articleId}:paragraph:${blockIndex}` : undefined}
          className="mb-5 border-l-2 border-[color:var(--accent)]/40 pl-4 text-base italic leading-7 text-[color:var(--muted-foreground)]"
        >
          {renderInline(content)}
        </blockquote>
      )
    }

    if (/^[-*]\s/.test(trimmed)) {
      const items = trimmed.split(/\n/).filter(Boolean)
      return (
        <ul
          key={blockIndex}
          id={articleId ? `${articleId}:paragraph:${blockIndex}` : undefined}
          className="mb-5 space-y-2 pl-5 text-base leading-7 text-[color:var(--foreground)]"
        >
          {items.map((item, itemIndex) => (
            <li key={itemIndex} className="list-disc">
              {renderInline(item.replace(/^[-*]\s*/, ''))}
            </li>
          ))}
        </ul>
      )
    }

    if (/^\d+\.\s/.test(trimmed)) {
      const items = trimmed.split(/\n/).filter(Boolean)
      return (
        <ol
          key={blockIndex}
          id={articleId ? `${articleId}:paragraph:${blockIndex}` : undefined}
          className="mb-5 space-y-2 pl-5 text-base leading-7 text-[color:var(--foreground)]"
        >
          {items.map((item, itemIndex) => (
            <li key={itemIndex} className="list-decimal">
              {renderInline(item.replace(/^\d+\.\s*/, ''))}
            </li>
          ))}
        </ol>
      )
    }

    return (
      <p
        key={blockIndex}
        id={articleId ? `${articleId}:paragraph:${blockIndex}` : undefined}
        className="mb-5 text-[1.03rem] leading-8 text-[color:var(--foreground)]"
      >
        {renderInline(trimmed)}
      </p>
    )
  })
}

function highlightClass(appearance: ConceptInfo['appearance']) {
  if (appearance === 'confirmed') {
    return 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)] ring-1 ring-[color:var(--accent)]/30'
  }

  if (appearance === 'candidate') {
    return 'bg-[color:var(--accent-soft)]/70 text-[color:var(--accent-strong)]/90 ring-1 ring-[color:var(--accent)]/15'
  }

  return 'bg-[color:var(--card)] text-[color:var(--muted-foreground)] ring-1 ring-[color:var(--border)]'
}

export function ArticleRenderer({
  articleId,
  body,
  conceptMap,
  onConceptClick,
  onMarkConcept,
}: ArticleRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectionState, setSelectionState] = useState<{ text: string; x: number; y: number } | null>(null)

  // Dismiss floating button on scroll
  useEffect(() => {
    const onScroll = () => setSelectionState(null)
    window.addEventListener('scroll', onScroll, true)
    return () => window.removeEventListener('scroll', onScroll, true)
  }, [])

  const conceptNames = useMemo(
    () => Object.keys(conceptMap).sort((left, right) => right.length - left.length),
    [conceptMap],
  )

  const conceptRegex = useMemo(() => {
    if (conceptNames.length === 0) {
      return null
    }

    return new RegExp(`(${conceptNames.map(escapeRegExp).join('|')})`, 'g')
  }, [conceptNames])

  function renderConceptSegment(value: string, prefix: string): ReactNode[] {
    if (!conceptRegex) {
      return [value]
    }

    const parts = value.split(conceptRegex)
    return parts.map((part, index) => {
      if (!part) {
        return null
      }

      const info = conceptMap[part]

      if (!info) {
        return part
      }

      const appearance = info.appearance || (info.node_id ? 'candidate' : 'plain')

      return (
        <button
          key={`${prefix}:candidate:${index}:${part}`}
          type="button"
          aria-label={`查看概念：${part}`}
          className={`mx-0.5 inline-flex rounded-md px-1.5 py-0.5 text-left text-[0.95em] transition hover:opacity-90 ${highlightClass(appearance)}`}
          onClick={() => onConceptClick?.(info)}
        >
          {part}
        </button>
      )
    })
  }

  function renderInline(value: string): ReactNode[] {
    const boldParts = value.split(/(\*\*[^*]+\*\*)/g)

    return boldParts.flatMap((part, partIndex) => {
      if (!part) {
        return []
      }

      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={`bold:${partIndex}`} className="font-semibold text-[color:var(--foreground)]">
            {renderInline(part.slice(2, -2))}
          </strong>
        )
      }

      const segments = part.split(WIKI_LINK_RE)
      return segments.flatMap((segment, segmentIndex) => {
        if (!segment) {
          return []
        }

        if (segmentIndex % 2 === 1) {
          const info = conceptMap[segment] || { name: segment, appearance: 'candidate' as const }
          const appearance = info.appearance || (info.node_id ? 'confirmed' : 'candidate')

          return (
            <button
              key={`wiki:${partIndex}:${segmentIndex}:${segment}`}
              type="button"
              aria-label={`查看概念：${segment}`}
              className={`mx-0.5 inline-flex rounded-md px-1.5 py-0.5 text-left text-[0.95em] transition hover:opacity-90 ${highlightClass(appearance)}`}
              onClick={() => onConceptClick?.(info)}
            >
              {segment}
            </button>
          )
        }

        return renderConceptSegment(segment, `segment:${partIndex}:${segmentIndex}`)
      })
    })
  }

  const handleMouseUp = useCallback((event: ReactMouseEvent<HTMLDivElement>) => {
    if (!onMarkConcept) {
      return
    }

    const selection = window.getSelection()
    const selectedText = selection?.toString().trim() || ''

    if (!selection || !selectedText || !containerRef.current?.contains(event.target as Node)) {
      setSelectionState(null)
      return
    }

    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null
    const rect = range?.getBoundingClientRect()

    if (!rect) {
      setSelectionState(null)
      return
    }

    setSelectionState({
      text: selectedText,
      x: rect.left + rect.width / 2,
      y: rect.top - 12,
    })
  }, [onMarkConcept])

  if (!body) return null

  return (
    <div ref={containerRef} className="relative" onMouseUp={handleMouseUp}>
      <div className="article-renderer">
        {renderFormattedText(articleId, body, renderInline)}
      </div>

      {selectionState ? (
        <button
          type="button"
          className="fixed z-40 rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-3 py-1.5 text-xs font-medium text-[color:var(--foreground)] shadow-lg"
          style={{
            left: selectionState.x,
            top: selectionState.y,
            transform: 'translate(-50%, -100%)',
          }}
          onClick={() => {
            onMarkConcept?.(selectionState.text)
            setSelectionState(null)
            window.getSelection()?.removeAllRanges()
          }}
        >
          标记概念
        </button>
      ) : null}
    </div>
  )
}
