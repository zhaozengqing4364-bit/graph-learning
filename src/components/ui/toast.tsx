/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

type ToastVariant = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (message: string, variant?: ToastVariant) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let toastCounter = 0

// Module-level toast for use outside React components (e.g. mutations)
let _addToast: ((message: string, variant: ToastVariant) => void) | null = null

export function showToast(message: string, variant: ToastVariant = 'info') {
  if (_addToast) {
    _addToast(message, variant)
  } else {
    console.warn(`[toast] ${variant}: ${message}`)
  }
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(
    (message: string, variant: ToastVariant = 'info') => {
      const id = `toast-${++toastCounter}`
      setToasts((prev) => [...prev, { id, message, variant }])
      setTimeout(() => removeToast(id), 4000)
    },
    [removeToast],
  )

  // Register module-level toast for use outside React components
  _addToast = addToast

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 animate-slide-up cursor-pointer min-w-[240px] ${
              t.variant === 'success'
                ? 'bg-green-600 text-white'
                : t.variant === 'error'
                  ? 'bg-red-600 text-white'
                  : t.variant === 'warning'
                    ? 'bg-amber-500 text-white'
                    : 'bg-gray-800 text-white'
            }`}
            onClick={() => removeToast(t.id)}
          >
            <span className="flex-1">{t.message}</span>
            <span className="opacity-60 text-xs">x</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return (opts: { message: string; type?: ToastVariant }) => {
    ctx.addToast(opts.message, opts.type)
  }
}
