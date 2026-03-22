import type { PracticeType, FeedbackLevel } from '../types'

export const PRACTICE_LABELS: Record<string, string> = {
  define: '定义',
  example: '举例',
  contrast: '对比',
  apply: '应用',
  teach_beginner: '教新手',
  compress: '压缩',
  explain: '解释',
  spaced: '间隔复习',
  recall: '回忆复习',
}

/** Alias for backward compatibility. Prefer PRACTICE_LABELS in new code. */
export const PRACTICE_TYPE_LABELS: Record<string, string> = PRACTICE_LABELS

export const LEVEL_COLORS: Record<FeedbackLevel, string> = {
  good: 'text-green-600',
  medium: 'text-amber-600',
  weak: 'text-red-600',
}

export const PRACTICE_SEQUENCE: PracticeType[] = [
  'define',
  'example',
  'contrast',
  'apply',
  'teach_beginner',
  'compress',
]
