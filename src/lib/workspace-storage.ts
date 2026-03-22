import type { ConceptNoteRecord, ReadingStateRecord, SourceArticleRecord } from '../types'
import { upsertSourceArticle } from './article-workspace'

function keyFor(topicId: string, scope: 'articles' | 'notes' | 'reading') {
  return `article-workspace:${topicId}:${scope}`
}

function loadJson<T>(key: string, fallback: T): T {
  const raw = window.localStorage.getItem(key)
  if (!raw) {
    return fallback
  }

  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function saveJson<T>(key: string, value: T): boolean {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch (e) {
    console.warn(`[workspace-storage] Failed to save ${key}:`, e)
    return false
  }
}

export function loadSourceArticles(topicId: string): SourceArticleRecord[] {
  return loadJson<SourceArticleRecord[]>(keyFor(topicId, 'articles'), [])
}

export function upsertSourceArticleRecord(topicId: string, nextArticle: SourceArticleRecord): SourceArticleRecord[] {
  const updated = upsertSourceArticle(loadSourceArticles(topicId), nextArticle)
  saveJson(keyFor(topicId, 'articles'), updated)
  return updated
}

export function loadConceptNotes(topicId: string): ConceptNoteRecord[] {
  return loadJson<ConceptNoteRecord[]>(keyFor(topicId, 'notes'), [])
}

export function upsertConceptNote(topicId: string, nextNote: ConceptNoteRecord): ConceptNoteRecord[] {
  const existing = loadConceptNotes(topicId)
  const index = existing.findIndex((note) => note.note_id === nextNote.note_id)
  const updated = index === -1
    ? [...existing, nextNote]
    : existing.map((note, noteIndex) => (noteIndex === index ? nextNote : note))

  saveJson(keyFor(topicId, 'notes'), updated)
  return updated
}

export function loadReadingState(topicId: string): ReadingStateRecord | null {
  return loadJson<ReadingStateRecord | null>(keyFor(topicId, 'reading'), null)
}

export function saveReadingState(topicId: string, nextState: ReadingStateRecord): ReadingStateRecord {
  saveJson(keyFor(topicId, 'reading'), nextState)
  return nextState
}

export function clearWorkspaceTopicState(topicId: string) {
  window.localStorage.removeItem(keyFor(topicId, 'articles'))
  window.localStorage.removeItem(keyFor(topicId, 'notes'))
  window.localStorage.removeItem(keyFor(topicId, 'reading'))
}
