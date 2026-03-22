import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Home, BookOpen, GitBranch, BarChart3, RefreshCw, Settings, ChevronLeft, ChevronRight, Star } from 'lucide-react'

import { useResolvedTopicContext } from '../hooks'
import { buildLearnRoute } from '../lib/navigation-context'
import { useAppStore } from '../stores'
import { Topbar } from '../components/shared/topbar'

const navItems = [
  { to: '/', icon: Home, label: '首页' },
  { to: '/stats', icon: BarChart3, label: '统计' },
  { to: '/reviews', icon: RefreshCw, label: '复习' },
  { to: '/settings', icon: Settings, label: '设置' },
]

export function AppLayout() {
  const location = useLocation()
  const sidebarCollapsed = useAppStore((s) => s.sidebar_collapsed)
  const setSidebarCollapsed = useAppStore((s) => s.setSidebarCollapsed)
  const { topicId: currentTopicId, nodeId: currentNodeId, sessionId } = useResolvedTopicContext()

  if (/^\/topic\/[^/]+\/learn/.test(location.pathname)) {
    return <Outlet />
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={`${sidebarCollapsed ? 'w-14' : 'w-56'} border-r border-gray-200 bg-white flex flex-col transition-all duration-200`}>
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          {!sidebarCollapsed && (
            <h1 className="text-lg font-bold text-indigo-600">AxonClone</h1>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            title={sidebarCollapsed ? '展开侧栏' : '收起侧栏'}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                } ${sidebarCollapsed ? 'justify-center' : ''}`
              }
              title={sidebarCollapsed ? item.label : undefined}
            >
              <item.icon size={18} />
              {!sidebarCollapsed && item.label}
            </NavLink>
          ))}
        </nav>

        {/* Current topic quick nav */}
        {currentTopicId && (
          <div className="border-t border-gray-200 p-2 space-y-1">
            {!sidebarCollapsed && (
              <p className="px-3 text-[10px] text-gray-500 uppercase tracking-wider font-medium">当前主题</p>
            )}
            <NavLink
              to={buildLearnRoute(currentTopicId || '', { nodeId: currentNodeId, sessionId })}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                } ${sidebarCollapsed ? 'justify-center' : ''}`
              }
              title={sidebarCollapsed ? '学习' : undefined}
            >
              <BookOpen size={18} />
              {!sidebarCollapsed && '学习'}
            </NavLink>
            <NavLink
              to={`/topic/${currentTopicId}/graph`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                } ${sidebarCollapsed ? 'justify-center' : ''}`
              }
              title={sidebarCollapsed ? '图谱' : undefined}
            >
              <GitBranch size={18} />
              {!sidebarCollapsed && '图谱'}
            </NavLink>
            <NavLink
              to={`/topic/${currentTopicId}/assets`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                } ${sidebarCollapsed ? 'justify-center' : ''}`
              }
              title={sidebarCollapsed ? '资产' : undefined}
            >
              <Star size={18} />
              {!sidebarCollapsed && '资产'}
            </NavLink>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto flex flex-col">
        <Topbar />
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
