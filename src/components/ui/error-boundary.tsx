import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  /** Called when user clicks "重试渲染" — useful for parent state reset */
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.warn('[ErrorBoundary] Uncaught error:', error?.message, errorInfo)
  }

  private handleReset = () => {
    this.props.onReset?.()
    this.setState({ hasError: false, error: null })
  }

  private handleReload = () => {
    window.location.reload()
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      const isRecoverable = !this._isFatal(this.state.error)

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] px-4 text-center">
          <div className={`mb-4 ${isRecoverable ? 'text-amber-400' : 'text-red-400'}`}>
            <AlertTriangle size={48} />
          </div>
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            {isRecoverable ? '加载遇到了问题' : '页面出现了意外错误'}
          </h2>
          <p className="text-sm text-gray-500 max-w-md mb-1">
            {isRecoverable
              ? (this.state.error?.message ?? '数据加载失败，请稍后重试')
              : '发生了未知错误'}
          </p>
          <p className="text-xs text-gray-400 max-w-md mb-6">
            {isRecoverable ? '点击重试或刷新页面' : '请尝试刷新页面，或返回首页继续操作'}
          </p>
          <div className="flex gap-3">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
            >
              重试渲染
            </button>
            <button
              onClick={this.handleReload}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw size={14} />
              刷新页面
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }

  /** Heuristic: errors from API/network are recoverable; render crashes are fatal. */
  private _isFatal(error: Error | null): boolean {
    if (!error) return true
    // Recoverable: network errors, API errors, chunk loading failures
    const recoverablePatterns = /NETWORK_ERROR|Failed to fetch|chunk|Loading chunk|timeout/i
    return !recoverablePatterns.test(error.message) && !error.message.includes('加载')
  }
}
