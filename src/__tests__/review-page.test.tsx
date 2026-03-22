import React from 'react'
import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ReviewPage } from '../routes/review-page'

const routerMocks = vi.hoisted(() => ({
  useNavigate: vi.fn(),
}))

const queryClientMocks = vi.hoisted(() => ({
  invalidateQueries: vi.fn(),
}))

const hookMocks = vi.hoisted(() => ({
  useReviewListQuery: vi.fn(),
  useReviewDetailQuery: vi.fn(),
  useSubmitReviewMutation: vi.fn(),
  useSkipReviewMutation: vi.fn(),
  useSnoozeReviewMutation: vi.fn(),
  useTopicListQuery: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: routerMocks.useNavigate,
  }
})

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query')
  return {
    ...actual,
    useQueryClient: () => queryClientMocks,
  }
})

vi.mock('../hooks', () => ({
  useReviewListQuery: hookMocks.useReviewListQuery,
  useReviewDetailQuery: hookMocks.useReviewDetailQuery,
  useSubmitReviewMutation: hookMocks.useSubmitReviewMutation,
  useSkipReviewMutation: hookMocks.useSkipReviewMutation,
  useSnoozeReviewMutation: hookMocks.useSnoozeReviewMutation,
  useTopicListQuery: hookMocks.useTopicListQuery,
}))

vi.mock('../services', () => ({
  generateReviewQueue: vi.fn(),
}))

vi.mock('../components/ui/toast', () => ({
  useToast: () => vi.fn(),
}))

vi.mock('../components/shared', () => ({
  Card: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  Button: ({
    children,
    onClick,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children?: React.ReactNode; loading?: boolean }) => (
    <button type="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
  Badge: ({ children }: { children?: React.ReactNode }) => <span>{children}</span>,
  LoadingSkeleton: () => <div>loading</div>,
  EmptyState: ({ title, action }: { title: string; action?: React.ReactNode }) => <div>{title}{action}</div>,
  ErrorState: ({ message }: { message: string }) => <div>{message}</div>,
}))

function makeMutation() {
  return {
    mutateAsync: vi.fn(),
    isPending: false,
  }
}

describe('ReviewPage', () => {
  let container: HTMLDivElement
  let root: Root

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    routerMocks.useNavigate.mockReturnValue(vi.fn())
    hookMocks.useReviewListQuery.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    hookMocks.useReviewDetailQuery.mockReturnValue({ data: null })
    hookMocks.useSubmitReviewMutation.mockReturnValue(makeMutation())
    hookMocks.useSkipReviewMutation.mockReturnValue(makeMutation())
    hookMocks.useSnoozeReviewMutation.mockReturnValue(makeMutation())
    hookMocks.useTopicListQuery.mockReturnValue({ data: [] })
  })

  afterEach(async () => {
    await act(async () => {
      root.unmount()
    })
    container.remove()
    vi.clearAllMocks()
  })

  it('requests enough review and topic rows to avoid silently truncating the queue surface', async () => {
    await act(async () => {
      root.render(<ReviewPage />)
    })

    expect(hookMocks.useReviewListQuery).toHaveBeenCalledWith({ status: 'pending', limit: 200 })
    expect(hookMocks.useTopicListQuery).toHaveBeenCalledWith({ limit: 200 })
  })
})
