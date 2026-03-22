import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppLayout } from './app-layout'
import { LoadingSkeleton } from '../components/shared'
import { ErrorBoundary } from '../components/ui/error-boundary'
import { ToastProvider } from '../components/ui/toast'
import { GlobalCommandPalette } from '../components/shared/global-command-palette'

const HomePage = lazy(() => import('../routes/home-page').then(m => ({ default: m.HomePage })))
const LearningPage = lazy(() => import('../routes/learning-page').then(m => ({ default: m.LearningPage })))
const GraphPage = lazy(() => import('../routes/graph-page').then(m => ({ default: m.GraphPage })))
const PracticePage = lazy(() => import('../routes/practice-page').then(m => ({ default: m.PracticePage })))
const StatsPage = lazy(() => import('../routes/stats-page').then(m => ({ default: m.StatsPage })))
const ReviewPage = lazy(() => import('../routes/review-page').then(m => ({ default: m.ReviewPage })))
const SettingsPage = lazy(() => import('../routes/settings-page').then(m => ({ default: m.SettingsPage })))
const SummaryPage = lazy(() => import('../routes/summary-page').then(m => ({ default: m.SummaryPage })))
const AssetsPage = lazy(() => import('../routes/assets-page').then(m => ({ default: m.AssetsPage })))

function PageSuspense({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="p-6"><LoadingSkeleton lines={5} /></div>}>
      {children}
    </Suspense>
  )
}

export function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<PageSuspense><HomePage /></PageSuspense>} />
            <Route path="/topic/:topicId/learn" element={<PageSuspense><LearningPage /></PageSuspense>} />
            <Route path="/topic/:topicId/graph" element={<PageSuspense><GraphPage /></PageSuspense>} />
            <Route path="/topic/:topicId/practice" element={<PageSuspense><PracticePage /></PageSuspense>} />
            <Route path="/topic/:topicId/summary" element={<PageSuspense><SummaryPage /></PageSuspense>} />
            <Route path="/topic/:topicId/assets" element={<PageSuspense><AssetsPage /></PageSuspense>} />
            <Route path="/stats" element={<PageSuspense><StatsPage /></PageSuspense>} />
            <Route path="/reviews" element={<PageSuspense><ReviewPage /></PageSuspense>} />
            <Route path="/settings" element={<PageSuspense><SettingsPage /></PageSuspense>} />
            <Route path="*" element={
              <div className="flex flex-col items-center justify-center h-screen gap-4">
                <p className="text-6xl font-bold text-gray-300">404</p>
                <p className="text-sm text-gray-400">页面不存在</p>
                <a href="/" className="text-sm text-indigo-600 hover:text-indigo-700">返回首页</a>
              </div>
            } />
          </Route>
        </Routes>
      </ToastProvider>
      <GlobalCommandPalette />
    </ErrorBoundary>
  )
}
