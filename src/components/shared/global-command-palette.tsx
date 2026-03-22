import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTopicListQuery } from '../../hooks'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../ui/command'

interface CommandItemDef {
  id: string
  label: string
  subtitle: string
  action: () => void
}

export function GlobalCommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const { data: topics } = useTopicListQuery()

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Don't show when article workspace already has its own command palette
  if (/^\/topic\/[^/]+\/learn/.test(location.pathname)) {
    return null
  }

  const q = query.trim().toLowerCase()
  const navItems: CommandItemDef[] = [
    { id: 'nav-home', label: '首页', subtitle: '查看所有主题', action: () => navigate('/') },
    { id: 'nav-stats', label: '统计', subtitle: '学习数据与成长趋势', action: () => navigate('/stats') },
    { id: 'nav-reviews', label: '复习', subtitle: '间隔复习队列', action: () => navigate('/reviews') },
    { id: 'nav-settings', label: '设置', subtitle: '模型与偏好配置', action: () => navigate('/settings') },
  ]

  const topicItems: CommandItemDef[] = (topics || [])
    .filter((t) => !q || t.title.toLowerCase().includes(q))
    .slice(0, 8)
    .map((t) => ({
      id: `topic-${t.topic_id}`,
      label: t.title,
      subtitle: `${t.learning_intent} · ${t.total_nodes ?? 0} 节点`,
      action: () => navigate(`/topic/${t.topic_id}/learn`),
    }))

  const handleSelect = (item: CommandItemDef) => {
    item.action()
    setOpen(false)
    setQuery('')
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <Command shouldFilter={false}>
        <CommandInput
          value={query}
          onValueChange={setQuery}
          placeholder="搜索页面或主题…"
        />
        <CommandList>
          <CommandEmpty>没有匹配结果。</CommandEmpty>
          {topicItems.length > 0 && (
            <CommandGroup heading="主题">
              {topicItems.map((item) => (
                <CommandItem
                  key={item.id}
                  value={item.label}
                  onSelect={() => handleSelect(item)}
                >
                  <div>
                    <p>{item.label}</p>
                    <p className="text-xs text-gray-500">{item.subtitle}</p>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          <CommandGroup heading="导航">
            {navItems.map((item) => (
              <CommandItem
                key={item.id}
                value={item.label}
                onSelect={() => handleSelect(item)}
              >
                <div>
                  <p>{item.label}</p>
                  <p className="text-xs text-gray-500">{item.subtitle}</p>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
