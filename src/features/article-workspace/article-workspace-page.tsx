import {
  startTransition,
  useDeferredValue,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  BookOpenText,
  CheckCircle2,
  FilePenLine,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Search,
} from 'lucide-react'

import { ArticleRenderer } from '../../components/shared/article-renderer'
import { useToast } from '../../components/ui/toast'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/shared'
import { Textarea } from '../../components/ui/textarea'
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../../components/ui/command'
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '../../components/ui/drawer'
import {
  Sheet,
  SheetContent,
} from '../../components/ui/sheet'
import { useIsMobile } from '../../hooks/use-mobile'
import {
  useBacklinksQuery,
  useEntryNodeQuery,
  useGraphQuery,
  useMainlineQuery,
  useNodeDetailQuery,
  useSettingsQuery,
  useTopicQuery,
  useWorkspaceBundleQuery,
  useWorkspaceSearchQuery,
} from '../../hooks/use-queries'
import {
  useCompleteSessionMutation,
  useConfirmConceptCandidateMutation,
  useCreateConceptCandidateMutation,
  useCreateSourceArticleMutation,
  useGenerateArticleMutation,
  useIgnoreConceptCandidateMutation,
  useSaveReadingStateMutation,
  useStartSessionMutation,
  useUpdateSourceArticleMutation,
  useUpsertConceptNoteMutation,
  useVisitNodeMutation,
} from '../../hooks/use-mutations'
import type {
  ConceptCandidateRecord,
  ConceptCandidateStatus,
  ConceptNoteRecord,
  RelatedNode,
  SourceArticleMutationResult,
  SourceArticleRecord,
} from '../../types'
import {
  articleStatusLabel,
  buildArticleLibrarySections,
  buildCommandPaletteGroups,
  buildConceptArticles,
  buildGuideArticle,
  buildSourceWorkspaceArticles,
  pickNextArticleRecommendation,
  pushBreadcrumb,
  resolveConceptAppearance,
  type WorkspaceArticle,
  type WorkspaceArticleKind,
  type WorkspaceBreadcrumbItem,
} from '../../lib/article-workspace'
import { clearWorkspaceTopicState } from '../../lib/workspace-storage'
import { validateWikiLinks } from '../../lib/article-workspace'
import { buildPracticeRoute } from '../../lib/navigation-context'
import {
  buildReadingStatePayload,
  readingStatePayloadEquals,
  type ReadingStatePayload,
} from './workspace-helpers'
import { ArticleFooterPanel } from './article-footer-panel'
import { ArticleHeader } from './article-header'
import { ArticleLibrarySidebar } from './article-library-sidebar'
import { ConceptDrawerContent } from './concept-drawer-content'
import {
  resolveArticleCompletionAction,
  resolveLearningSessionPlan,
} from './session-flow'

interface ConceptPanelState {
  name: string
  node_id?: string
  summary?: string
  candidate_id?: string
  concept_key?: string
  status?: ConceptCandidateStatus
}

function normalizeText(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ')
}

function articleKindFromId(articleId: string): WorkspaceArticleKind {
  if (articleId.startsWith('concept:')) return 'concept'
  if (articleId.startsWith('guide:')) return 'guide'
  return 'source'
}

function breadcrumbFromArticle(article: WorkspaceArticle): WorkspaceBreadcrumbItem {
  return {
    article_id: article.article_id,
    kind: article.kind,
    title: article.title,
    node_id: article.node_id,
  }
}

function readingTrailToBreadcrumb(trail: { article_id: string; title: string }[]): WorkspaceBreadcrumbItem[] {
  return trail.map((entry) => ({
    article_id: entry.article_id,
    title: entry.title,
    kind: articleKindFromId(entry.article_id),
    node_id: entry.article_id.startsWith('concept:') ? entry.article_id.slice('concept:'.length) : undefined,
  }))
}

function relationshipItems(nodes: RelatedNode[]) {
  return nodes.map((node) => ({ name: node.name, node_id: node.node_id }))
}

function relationshipNames(nodes: RelatedNode[]) {
  return nodes.map((node) => node.name).filter(Boolean)
}

function buildKnowledgeMap(args: {
  article: WorkspaceArticle
  activeConceptDetail: ReturnType<typeof useNodeDetailQuery>['data'] | undefined
  knownConceptNames: string[]
  knownConceptIds: Map<string, string>
}) {
  if (args.article.kind === 'concept' && args.activeConceptDetail) {
    const groups = [
      { title: '前置概念', items: relationshipItems(args.activeConceptDetail.prerequisites) },
      { title: '对比概念', items: relationshipItems(args.activeConceptDetail.contrasts) },
      { title: '应用场景', items: relationshipItems(args.activeConceptDetail.applications) },
      { title: '相关概念', items: relationshipItems(args.activeConceptDetail.related) },
    ].filter((group) => group.items.length > 0)

    return groups.length > 0 ? groups : [{
      title: '相关概念',
      items: args.knownConceptNames.slice(0, 6).map((name) => ({
        name,
        node_id: args.knownConceptIds.get(name),
      })),
    }]
  }

  return args.knownConceptNames.length > 0
    ? [{
      title: '相关概念',
      items: args.knownConceptNames.slice(0, 8).map((name) => ({
        name,
        node_id: args.knownConceptIds.get(name),
      })),
    }]
    : []
}

function conceptKeyPoints(detail?: ReturnType<typeof useNodeDetailQuery>['data']) {
  if (!detail) {
    return []
  }

  const points = [
    detail.node.summary,
    detail.why_now,
    detail.prerequisites[0] ? `前置概念：${detail.prerequisites[0].name}` : '',
    detail.applications[0] ? `应用场景：${detail.applications[0].name}` : '',
  ].filter(Boolean)

  return points.slice(0, 3)
}

function buildAnalysisNotice(analysis: SourceArticleMutationResult['analysis']) {
  const parts = []

  if (analysis.added_mentions > 0) {
    parts.push(`新增 ${analysis.added_mentions} 处提及`)
  }
  if (analysis.removed_mentions > 0) {
    parts.push(`移除 ${analysis.removed_mentions} 处提及`)
  }
  if (analysis.candidate_count > 0) {
    parts.push(`发现 ${analysis.candidate_count} 个候选概念`)
  }

  return parts.length > 0 ? `已重新分析：${parts.join('，')}` : '已重新分析：概念提及无变化'
}

export function ArticleWorkspacePage() {
  const { topicId = '' } = useParams<{ topicId: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const isMobile = useIsMobile()

  const [libraryOpen, setLibraryOpen] = useState(true)
  const [commandOpen, setCommandOpen] = useState(false)
  const [trail, setTrail] = useState<WorkspaceBreadcrumbItem[]>([])
  const [completedArticleIds, setCompletedArticleIds] = useState<string[]>([])
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({})
  const [conceptPanel, setConceptPanel] = useState<ConceptPanelState | null>(null)
  const [conceptPanelOpen, setConceptPanelOpen] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [sourceDraft, setSourceDraft] = useState('')
  const [commandQuery, setCommandQuery] = useState('')
  const [analysisNotice, setAnalysisNotice] = useState<string | null>(null)

  const readerRef = useRef<HTMLDivElement>(null)
  const requestedGenerationsRef = useRef<Set<string>>(new Set())
  const failedGenerationsRef = useRef<Set<string>>(new Set())
  const initializedTopicRef = useRef<string | null>(null)
  const readingSaveTimeoutRef = useRef<number | null>(null)
  const restoringScrollRef = useRef(false)
  const serverReadingStateRef = useRef<ReadingStatePayload | null>(null)
  const lastQueuedReadingStateRef = useRef<ReadingStatePayload | null>(null)
  const noteSaveTimeoutRef = useRef<number | null>(null)
  const sessionInitRef = useRef<string | null>(null)
  const visitedSessionNodeKeysRef = useRef<Set<string>>(new Set())
  const [visitedSessionNodeCount, setVisitedSessionNodeCount] = useState(0)

  const { data: topic, isLoading: topicLoading, error: topicError } = useTopicQuery(topicId)
  const { data: settings } = useSettingsQuery()
  const { data: entryNode } = useEntryNodeQuery(topicId)
  const { data: fullGraph } = useGraphQuery(topicId, { view: 'full' })
  const { data: mainlineGraph } = useMainlineQuery(topicId)
  const {
    data: workspace,
    isLoading: workspaceLoading,
    error: workspaceError,
    refetch: refetchWorkspace,
  } = useWorkspaceBundleQuery(topicId)
  const deferredCommandQuery = useDeferredValue(commandQuery.trim())
  const { data: workspaceSearchResults } = useWorkspaceSearchQuery(topicId, deferredCommandQuery)

  const articleIdFromLegacyNode = searchParams.get('nodeId')
    ? `concept:${searchParams.get('nodeId')}`
    : null
  const activeArticleId = searchParams.get('article') || articleIdFromLegacyNode
  const activeAnchorId = searchParams.get('anchor')
  const sessionId = searchParams.get('sessionId')?.trim() || ''

  // Session timer
  const [sessionElapsed, setSessionElapsed] = useState(0)
  useEffect(() => {
    if (!sessionId) return
    const timer = setInterval(() => setSessionElapsed((t) => t + 1), 60_000)
    return () => clearInterval(timer)
  }, [sessionId])
  const sessionMinutes = Math.floor(sessionElapsed / 60)
  const sessionSeconds = sessionElapsed % 60
  const activeConceptNodeId = activeArticleId?.startsWith('concept:')
    ? activeArticleId.slice('concept:'.length)
    : null
  const panelConceptNodeId = conceptPanel?.node_id || null

  const {
    data: activeConceptDetail,
    refetch: refetchActiveConcept,
  } = useNodeDetailQuery(topicId, activeConceptNodeId || '')
  const {
    data: panelConceptDetail,
    refetch: refetchPanelConcept,
  } = useNodeDetailQuery(
    topicId,
    panelConceptNodeId && panelConceptNodeId !== activeConceptNodeId ? panelConceptNodeId : '',
  )
  const { data: backlinks = [] } = useBacklinksQuery(topicId, activeConceptNodeId)

  const createSourceArticleMutation = useCreateSourceArticleMutation(topicId)
  const updateSourceArticleMutation = useUpdateSourceArticleMutation(topicId)
  const upsertConceptNoteMutation = useUpsertConceptNoteMutation(topicId)
  const { mutate: saveReadingState } = useSaveReadingStateMutation(topicId)
  const startSessionMutation = useStartSessionMutation(topicId)
  const visitNodeMutation = useVisitNodeMutation(topicId, sessionId)
  const completeSessionMutation = useCompleteSessionMutation(topicId, sessionId)
  const createConceptCandidateMutation = useCreateConceptCandidateMutation(topicId)
  const confirmConceptCandidateMutation = useConfirmConceptCandidateMutation(topicId)
  const ignoreConceptCandidateMutation = useIgnoreConceptCandidateMutation(topicId)

  const generationTargetId = conceptPanelOpen && panelConceptNodeId
    ? panelConceptNodeId
    : activeConceptNodeId
  const generateArticleMutation = useGenerateArticleMutation(topicId)

  const sourceArticles = useMemo<SourceArticleRecord[]>(
    () => workspace?.source_articles || [],
    [workspace?.source_articles],
  )
  const conceptNotes = useMemo<ConceptNoteRecord[]>(
    () => workspace?.concept_notes || [],
    [workspace?.concept_notes],
  )
  const conceptCandidates = useMemo<ConceptCandidateRecord[]>(
    () => workspace?.concept_candidates || [],
    [workspace?.concept_candidates],
  )
  const readingState = workspace?.reading_state || null

  useEffect(() => {
    const serverReadingState = readingState
      ? buildReadingStatePayload({
          articleId: readingState.article_id,
          scrollTop: readingState.scroll_top,
          trail: readingState.trail,
          completedArticleIds: readingState.completed_article_ids || [],
        })
      : null

    serverReadingStateRef.current = serverReadingState
    lastQueuedReadingStateRef.current = serverReadingState
  }, [readingState])

  const queueReadingStateSave = useCallback((scrollTop: number) => {
    if (!activeArticleId) {
      return
    }

    const nextPayload = buildReadingStatePayload({
      articleId: activeArticleId,
      scrollTop,
      trail,
      completedArticleIds,
    })

    if (readingStatePayloadEquals(lastQueuedReadingStateRef.current, nextPayload)) {
      return
    }

    lastQueuedReadingStateRef.current = nextPayload
    saveReadingState(nextPayload, {
      onError: () => {
        lastQueuedReadingStateRef.current = serverReadingStateRef.current
      },
    })
  }, [activeArticleId, completedArticleIds, saveReadingState, trail])

  const conceptCatalog = useMemo(
    () => (fullGraph?.nodes || []).map((node) => ({
      node_id: node.node_id,
      name: node.name,
      summary: '',
      importance: node.importance,
      status: node.status,
      topic_id: topicId,
      article_body: '',
      created_at: topic?.created_at || '',
      updated_at: topic?.updated_at || '',
    })),
    [fullGraph?.nodes, topic?.created_at, topic?.updated_at, topicId],
  )
  const conceptNotesByKey = useMemo(() => (
    new Map(conceptNotes.map((note) => [note.concept_key, note]))
  ), [conceptNotes])
  const candidateByNormalizedText = useMemo(() => {
    const map = new Map<string, ConceptCandidateRecord>()

    for (const candidate of conceptCandidates) {
      map.set(candidate.normalized_text, candidate)

      if (candidate.matched_concept_name) {
        map.set(normalizeText(candidate.matched_concept_name), candidate)
      }
    }

    return map
  }, [conceptCandidates])
  const confirmedCandidateNodeIds = useMemo(() => new Set(
    conceptCandidates
      .filter((candidate) => candidate.status === 'confirmed' && candidate.matched_node_id)
      .map((candidate) => candidate.matched_node_id as string),
  ), [conceptCandidates])

  const guideArticle = useMemo(() => {
    if (!topic) {
      return null
    }

    const mainlineConcepts = (mainlineGraph?.nodes || []).map((node) => ({
      node_id: node.node_id,
      name: node.name,
      summary: '',
      importance: node.importance,
      status: node.status,
    }))

    return buildGuideArticle(topic, entryNode, mainlineConcepts.slice(0, 5))
  }, [entryNode, mainlineGraph?.nodes, topic])

  const sourceWorkspaceArticles = useMemo(
    () => buildSourceWorkspaceArticles(sourceArticles),
    [sourceArticles],
  )

  const conceptWorkspaceArticles = useMemo(
    () => buildConceptArticles(conceptCatalog),
    [conceptCatalog],
  )

  const librarySections = useMemo(() => {
    if (!guideArticle) {
      return []
    }

    return buildArticleLibrarySections({
      guide: guideArticle,
      sourceArticles: sourceWorkspaceArticles,
      conceptArticles: conceptWorkspaceArticles,
    })
  }, [conceptWorkspaceArticles, guideArticle, sourceWorkspaceArticles])

  const activeArticle = useMemo(() => {
    if (!guideArticle || !activeArticleId) {
      return guideArticle
    }

    if (activeArticleId === guideArticle.article_id) {
      return guideArticle
    }

    const sourceArticle = sourceWorkspaceArticles.find((article) => article.article_id === activeArticleId)
    if (sourceArticle) {
      return sourceArticle
    }

    if (activeConceptDetail?.node && activeConceptNodeId === activeConceptDetail.node.node_id) {
      return buildConceptArticles([activeConceptDetail.node])[0]
    }

    return conceptWorkspaceArticles.find((article) => article.article_id === activeArticleId) || guideArticle
  }, [
    activeArticleId,
    activeConceptDetail,
    activeConceptNodeId,
    conceptWorkspaceArticles,
    guideArticle,
    sourceWorkspaceArticles,
  ])

  const panelDetail = panelConceptNodeId && panelConceptNodeId === activeConceptNodeId
    ? activeConceptDetail
    : panelConceptDetail

  const explicitLinks = useMemo(
    () => new Set(validateWikiLinks(activeArticle?.body || '', conceptCatalog).valid_links),
    [activeArticle?.body, conceptCatalog],
  )

  const knownConceptNames = useMemo(() => {
    const names = new Set<string>()

    for (const concept of conceptCatalog) {
      if (activeArticle?.body?.includes(concept.name)) {
        names.add(concept.name)
      }
    }

    for (const candidate of conceptCandidates) {
      if (candidate.status === 'ignored') {
        continue
      }

      const displayName = candidate.matched_concept_name || candidate.concept_text
      if (displayName && activeArticle?.body?.includes(displayName)) {
        names.add(displayName)
      }
    }

    return [...names]
  }, [activeArticle?.body, conceptCandidates, conceptCatalog])

  const conceptMap = useMemo(() => {
    const map: Record<string, {
      node_id?: string
      name: string
      summary?: string
      appearance?: 'confirmed' | 'candidate' | 'plain'
      candidate_id?: string
      concept_key?: string
      status?: ConceptCandidateStatus
    }> = {}

    for (const concept of conceptCatalog) {
      const noteForConcept = conceptNotes.find((note) => note.concept_key === concept.node_id)
      map[concept.name] = {
        node_id: concept.node_id,
        name: concept.name,
        summary: concept.summary,
        concept_key: concept.node_id,
        appearance: resolveConceptAppearance({
          isRecognized: true,
          isConfirmed: explicitLinks.has(concept.name)
            || confirmedCandidateNodeIds.has(concept.node_id)
            || Boolean(noteForConcept),
        }),
      }
    }

    for (const candidate of conceptCandidates) {
      if (candidate.status === 'ignored') {
        continue
      }

      const displayName = candidate.matched_concept_name || candidate.concept_text
      if (!displayName || map[displayName]) {
        continue
      }

      map[displayName] = {
        node_id: candidate.matched_node_id || undefined,
        name: displayName,
        summary: candidate.status === 'confirmed'
          ? `${displayName} 已经进入正式图谱。`
          : '候选概念，等待你确认后生成稳定专文。',
        candidate_id: candidate.candidate_id,
        concept_key: candidate.matched_node_id || `candidate:${candidate.candidate_id}`,
        status: candidate.status,
        appearance: candidate.status === 'confirmed' ? 'confirmed' : 'candidate',
      }
    }

    return map
  }, [conceptCandidates, conceptCatalog, conceptNotes, confirmedCandidateNodeIds, explicitLinks])

  const knownConceptIds = useMemo(() => {
    const map = new Map<string, string>()
    for (const concept of conceptCatalog) {
      map.set(concept.name, concept.node_id)
    }
    return map
  }, [conceptCatalog])

  const knowledgeMap = useMemo(() => (
    activeArticle
      ? buildKnowledgeMap({
          article: activeArticle,
          activeConceptDetail,
          knownConceptNames,
          knownConceptIds,
        })
      : []
  ), [activeArticle, activeConceptDetail, knownConceptIds, knownConceptNames])

  const recommendation = useMemo(() => {
    if (!activeArticle) {
      return null
    }

    if (activeArticle.kind === 'concept' && activeConceptDetail) {
      const next = pickNextArticleRecommendation({
        currentArticle: activeArticle,
        conceptRelations: {
          prerequisites: activeConceptDetail.prerequisites.map((item) => ({
            ...item,
            summary: item.summary || '',
            importance: 5,
          })),
          related: activeConceptDetail.related.map((item) => ({
            ...item,
            summary: item.summary || '',
            importance: 3,
          })),
        },
        visitedArticleIds: trail.map((item) => item.article_id),
      })

      if (next) {
        return next
      }
    }

    const unreadMainline = (mainlineGraph?.nodes || []).find(
      (node) => !trail.some((item) => item.article_id === `concept:${node.node_id}`),
    )

    if (unreadMainline) {
      return {
        article_id: `concept:${unreadMainline.node_id}`,
        title: unreadMainline.name,
        reason: '这是当前主题主干里尚未展开的一篇关键文章。',
        node_id: unreadMainline.node_id,
      }
    }

    return null
  }, [activeArticle, activeConceptDetail, mainlineGraph?.nodes, trail])

  const commandGroups = useMemo(() => (
    buildCommandPaletteGroups({
      query: commandQuery,
      sections: librarySections,
      conceptMatches: conceptCatalog,
      conceptNotes: conceptNotes.map((note) => ({
        node_id: note.concept_key,
        name: note.title,
        preview: note.body.slice(0, 36) || '概念笔记',
      })),
      recentArticles: [...trail].reverse().slice(0, 5),
      searchResults: deferredCommandQuery ? workspaceSearchResults : null,
    })
  ), [commandQuery, conceptCatalog, conceptNotes, deferredCommandQuery, librarySections, trail, workspaceSearchResults])

  const panelGenerationState = panelConceptNodeId
    ? panelDetail?.node?.article_body
      ? 'ready'
      : generateArticleMutation.isPending && generateArticleMutation.variables?.nodeId === panelConceptNodeId
        ? 'generating'
        : failedGenerationsRef.current.has(panelConceptNodeId)
          ? 'failed'
          : 'idle'
    : 'idle'

  const panelRelations = useMemo(() => {
    if (!panelDetail) {
      return {
        title: '相关概念',
        items: [],
      }
    }

    if (panelDetail.prerequisites.length > 0) {
      return { title: '前置概念', items: relationshipNames(panelDetail.prerequisites).slice(0, 6) }
    }

    if (panelDetail.contrasts.length > 0) {
      return { title: '对比概念', items: relationshipNames(panelDetail.contrasts).slice(0, 6) }
    }

    if (panelDetail.applications.length > 0) {
      return { title: '应用场景', items: relationshipNames(panelDetail.applications).slice(0, 6) }
    }

    return { title: '相关概念', items: relationshipNames(panelDetail.related).slice(0, 6) }
  }, [panelDetail])

  const currentConceptNote = useMemo(() => {
    if (!conceptPanel) {
      return null
    }

    const lookupKeys = [
      conceptPanel.node_id,
      conceptPanel.concept_key,
      conceptPanel.candidate_id ? `candidate:${conceptPanel.candidate_id}` : undefined,
      conceptPanel.name,
    ].filter(Boolean) as string[]

    for (const key of lookupKeys) {
      const note = conceptNotesByKey.get(key)
      if (note) {
        return note
      }
    }

    return null
  }, [conceptNotesByKey, conceptPanel])
  const currentConceptKey = currentConceptNote?.concept_key
    || conceptPanel?.concept_key
    || conceptPanel?.node_id
    || (conceptPanel?.candidate_id ? `candidate:${conceptPanel.candidate_id}` : undefined)
    || conceptPanel?.name
    || ''
  const currentConceptNoteValue = currentConceptKey
    ? noteDrafts[currentConceptKey] ?? currentConceptNote?.body ?? ''
    : ''

  useEffect(() => {
    if (!topicId) {
      return
    }

    initializedTopicRef.current = null
    startTransition(() => {
      setTrail([])
      setCompletedArticleIds([])
      setNoteDrafts({})
      setConceptPanel(null)
      setConceptPanelOpen(false)
      setEditMode(false)
      setAnalysisNotice(null)
    })
    requestedGenerationsRef.current.clear()
    serverReadingStateRef.current = null
    lastQueuedReadingStateRef.current = null
    sessionInitRef.current = null
    visitedSessionNodeKeysRef.current.clear()
    startTransition(() => {
      setVisitedSessionNodeCount(0)
    })
  }, [topicId])

  useEffect(() => {
    visitedSessionNodeKeysRef.current.clear()
    startTransition(() => {
      setVisitedSessionNodeCount(0)
    })
  }, [sessionId])

  useEffect(() => {
    if (!topicId || !workspace || initializedTopicRef.current === topicId) {
      return
    }

    startTransition(() => {
      setTrail(readingTrailToBreadcrumb(readingState?.trail || []))
      setCompletedArticleIds(readingState?.completed_article_ids || [])
    })
    initializedTopicRef.current = topicId
  }, [readingState, topicId, workspace])

  useEffect(() => {
    if (!topicId || !topic || !workspace || activeArticleId) {
      return
    }

    const nextArticleId = readingState?.article_id || `guide:${topicId}`
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('article', nextArticleId)
    nextParams.delete('nodeId')
    setSearchParams(nextParams, { replace: true })
  }, [activeArticleId, readingState?.article_id, searchParams, setSearchParams, topic, topicId, workspace])

  useEffect(() => {
    if (!topicId || !activeArticle) {
      return
    }

    startTransition(() => {
      setTrail((previous) => {
        const guideCrumb = guideArticle ? breadcrumbFromArticle(guideArticle) : null
        const nextBreadcrumb = breadcrumbFromArticle(activeArticle)

        if (previous.length === 0) {
          if (guideCrumb && nextBreadcrumb.article_id !== guideCrumb.article_id) {
            return [guideCrumb, nextBreadcrumb]
          }
          return [nextBreadcrumb]
        }

        const existingIndex = previous.findIndex((item) => item.article_id === nextBreadcrumb.article_id)
        if (existingIndex >= 0) {
          return existingIndex === previous.length - 1
            ? previous
            : previous.slice(0, existingIndex + 1)
        }

        return pushBreadcrumb(previous, nextBreadcrumb)
      })
    })
  }, [activeArticle, guideArticle, topicId])

  useEffect(() => {
    if (!topicId || !activeArticleId || initializedTopicRef.current !== topicId) {
      return
    }

    if (readingSaveTimeoutRef.current) {
      window.clearTimeout(readingSaveTimeoutRef.current)
    }

    readingSaveTimeoutRef.current = window.setTimeout(() => {
      queueReadingStateSave(readerRef.current?.scrollTop || 0)
    }, 240)
  }, [activeArticleId, completedArticleIds, queueReadingStateSave, topicId, trail])

  useEffect(() => {
    if (!topicId || !topic || !workspace || startSessionMutation.isPending) {
      return
    }

    const plan = resolveLearningSessionPlan({
      entryNodeId: entryNode?.node_id || topic.current_node_id || topic.entry_node_id,
      sessionId,
      activeArticleId,
      activeConceptNodeId,
      lastVisitedNodeId: null,
    })

    if (!plan.shouldStartSession || !plan.startPayload) {
      return
    }

    const initKey = `${topicId}:${plan.startPayload.entry_node_id}`
    if (sessionInitRef.current === initKey) {
      return
    }

    sessionInitRef.current = initKey
    void startSessionMutation.mutateAsync(plan.startPayload)
      .then((session) => {
        const nextSessionId = String(session.session_id || '').trim()
        if (!nextSessionId) {
          sessionInitRef.current = null
          return
        }

        const nextParams = new URLSearchParams(searchParams)
        nextParams.set('sessionId', nextSessionId)
        setSearchParams(nextParams, { replace: true })
      })
      .catch(() => {
        sessionInitRef.current = null
        toast({ message: '学习会话启动失败，练习追踪和收束总结可能受限', type: 'warning' })
      })
  }, [
    activeArticleId,
    activeConceptNodeId,
    entryNode?.node_id,
    searchParams,
    sessionId,
    setSearchParams,
    startSessionMutation,
    topic,
    topicId,
    workspace,
    toast,
  ])

  useEffect(() => {
    if (!topicId || !sessionId || !activeConceptNodeId) {
      return
    }

    const lastVisitedNodeId = [...visitedSessionNodeKeysRef.current]
      .filter((key) => key.startsWith(`${sessionId}:`))
      .map((key) => key.split(':').slice(1).join(':'))
      .at(-1) || null
    const plan = resolveLearningSessionPlan({
      entryNodeId: entryNode?.node_id || topic?.current_node_id || topic?.entry_node_id,
      sessionId,
      activeArticleId,
      activeConceptNodeId,
      lastVisitedNodeId,
    })

    if (!plan.visitPayload) {
      return
    }

    const visitKey = `${sessionId}:${plan.visitPayload.node_id}`
    if (visitedSessionNodeKeysRef.current.has(visitKey)) {
      return
    }

    visitedSessionNodeKeysRef.current.add(visitKey)
    void visitNodeMutation.mutateAsync(plan.visitPayload)
      .then(() => {
        setVisitedSessionNodeCount(
          [...visitedSessionNodeKeysRef.current].filter((key) => key.startsWith(`${sessionId}:`)).length,
        )
      })
      .catch(() => {
        visitedSessionNodeKeysRef.current.delete(visitKey)
      })
  }, [activeArticleId, activeConceptNodeId, entryNode?.node_id, sessionId, topic?.current_node_id, topic?.entry_node_id, topicId, visitNodeMutation])

  useEffect(() => {
    const element = readerRef.current
    if (!element || !topicId || !activeArticleId) {
      return
    }

    const handleScroll = () => {
      if (restoringScrollRef.current) {
        return
      }

      if (readingSaveTimeoutRef.current) {
        window.clearTimeout(readingSaveTimeoutRef.current)
      }

      readingSaveTimeoutRef.current = window.setTimeout(() => {
        queueReadingStateSave(element.scrollTop)
      }, 320)
    }

    element.addEventListener('scroll', handleScroll)
    return () => element.removeEventListener('scroll', handleScroll)
  }, [activeArticleId, queueReadingStateSave, topicId])

  useEffect(() => {
    if (!topicId || !activeArticleId) {
      return
    }

    const restoreScrollTop = readingState?.article_id === activeArticleId
      ? readingState.scroll_top
      : 0

    restoringScrollRef.current = true
    requestAnimationFrame(() => {
      if (!readerRef.current) {
        restoringScrollRef.current = false
        return
      }

      readerRef.current.scrollTop = restoreScrollTop

      if (activeAnchorId) {
        document.getElementById(activeAnchorId)?.scrollIntoView({
          block: 'center',
          behavior: 'instant',
        })
      }

      requestAnimationFrame(() => {
        restoringScrollRef.current = false
      })
    })
  }, [activeAnchorId, activeArticleId, readingState?.article_id, readingState?.scroll_top, topicId])

  useEffect(() => () => {
    if (readingSaveTimeoutRef.current) {
      window.clearTimeout(readingSaveTimeoutRef.current)
    }
    if (noteSaveTimeoutRef.current) {
      window.clearTimeout(noteSaveTimeoutRef.current)
    }
  }, [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen((open) => !open)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    if (!generationTargetId) {
      return
    }

    const detail = generationTargetId === panelConceptNodeId ? panelDetail : activeConceptDetail
    if (!detail || detail.node.article_body || requestedGenerationsRef.current.has(generationTargetId)) {
      return
    }

    requestedGenerationsRef.current.add(generationTargetId)
    failedGenerationsRef.current.delete(generationTargetId)
    generateArticleMutation.mutate({ nodeId: generationTargetId }, {
      onSuccess: async () => {
        failedGenerationsRef.current.delete(generationTargetId)
        if (activeConceptNodeId === generationTargetId) {
          await refetchActiveConcept()
        }
        if (panelConceptNodeId === generationTargetId) {
          await refetchPanelConcept()
        }
      },
      onError: () => {
        failedGenerationsRef.current.add(generationTargetId)
      },
    })
  }, [
    activeConceptDetail,
    activeConceptNodeId,
    generateArticleMutation,
    generationTargetId,
    panelConceptNodeId,
    panelDetail,
    refetchActiveConcept,
    refetchPanelConcept,
  ])

  useEffect(() => {
    if (!activeArticle || activeArticle.kind !== 'source') {
      startTransition(() => {
        setEditMode(false)
      })
      return
    }

    startTransition(() => {
      setSourceDraft(activeArticle.body)
    })
  }, [activeArticle])

  const openArticle = useCallback((articleId: string, options?: { anchorId?: string }) => {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('article', articleId)
    nextParams.delete('nodeId')
    if (options?.anchorId) {
      nextParams.set('anchor', options.anchorId)
    } else {
      nextParams.delete('anchor')
    }

    setSearchParams(nextParams)
    setConceptPanelOpen(false)
    setEditMode(false)
  }, [searchParams, setSearchParams])

  const openConceptPanel = useCallback((concept: ConceptPanelState) => {
    setConceptPanel(concept)
    setConceptPanelOpen(true)
  }, [])

  const handleCreateSourceArticle = useCallback(() => {
    createSourceArticleMutation.mutate(
      {
        title: `新源文章 ${sourceArticles.length + 1}`,
        body: '',
      },
      {
        onSuccess: (result) => {
          openArticle(result.article.article_id)
          setEditMode(true)
          setSourceDraft(result.article.body)
          setAnalysisNotice(buildAnalysisNotice(result.analysis))
        },
      },
    )
  }, [createSourceArticleMutation, openArticle, sourceArticles.length])

  const handleSaveSourceArticle = useCallback(() => {
    if (!activeArticle || activeArticle.kind !== 'source') {
      return
    }

    updateSourceArticleMutation.mutate(
      {
        articleId: activeArticle.article_id,
        body: {
          title: activeArticle.title,
          body: sourceDraft,
        },
      },
      {
        onSuccess: (result) => {
          setEditMode(false)
          setSourceDraft(result.article.body)
          startTransition(() => {
            setAnalysisNotice(buildAnalysisNotice(result.analysis))
          })
        },
      },
    )
  }, [activeArticle, sourceDraft, updateSourceArticleMutation])

  const handleRefreshConceptArticle = useCallback(() => {
    if (!activeConceptNodeId) {
      return
    }

    generateArticleMutation.mutate(
      {
        nodeId: activeConceptNodeId,
        force: true,
      },
      {
        onSuccess: async () => {
          await refetchActiveConcept()
          if (panelConceptNodeId === activeConceptNodeId) {
            await refetchPanelConcept()
          }
          toast({ message: '已根据最新源文章刷新概念专文。', type: 'success' })
        },
      },
    )
  }, [
    activeConceptNodeId,
    generateArticleMutation,
    panelConceptNodeId,
    refetchActiveConcept,
    refetchPanelConcept,
    toast,
  ])

  const handleRetryPanelGeneration = useCallback(() => {
    if (!panelConceptNodeId) return
    failedGenerationsRef.current.delete(panelConceptNodeId)
    requestedGenerationsRef.current.delete(panelConceptNodeId)
    generateArticleMutation.mutate(
      { nodeId: panelConceptNodeId, force: true },
      {
        onSuccess: async () => {
          failedGenerationsRef.current.delete(panelConceptNodeId)
          await refetchPanelConcept()
        },
        onError: () => {
          failedGenerationsRef.current.add(panelConceptNodeId)
        },
      },
    )
  }, [generateArticleMutation, panelConceptNodeId, refetchPanelConcept])

  const handleMarkComplete = useCallback(async () => {
    if (!activeArticle) {
      return
    }

    const completion = resolveArticleCompletionAction({
      topicId,
      activeArticleId: activeArticle.article_id,
      activeConceptNodeId: activeArticle.node_id || activeConceptNodeId,
      sessionId,
      completedArticleIds,
      autoStartPractice: settings?.auto_start_practice ?? false,
      autoGenerateSummary: settings?.auto_generate_summary ?? true,
    })

    setCompletedArticleIds(completion.completedArticleIds)
    toast({ message: '已标记为完成', type: 'success' })

    if (completion.practiceRoute) {
      navigate(completion.practiceRoute)
      return
    }

    if (completion.shouldCompleteSession && completion.completeSessionRequest) {
      try {
        const summary = await completeSessionMutation.mutateAsync(completion.completeSessionRequest)
        if (completion.summaryRoute) {
          navigate(completion.summaryRoute, { state: { summary } })
        }
      } catch (error) {
        toast({
          message: error instanceof Error ? error.message : '结束会话失败，请稍后重试',
          type: 'error',
        })
      }
    }
  }, [
    activeArticle,
    activeConceptNodeId,
    completedArticleIds,
    completeSessionMutation,
    navigate,
    sessionId,
    settings?.auto_generate_summary,
    settings?.auto_start_practice,
    toast,
    topicId,
  ])

  const handleConceptNoteChange = useCallback((value: string) => {
    if (!conceptPanel || !currentConceptKey) {
      return
    }

    setNoteDrafts((previous) => ({
      ...previous,
      [currentConceptKey]: value,
    }))

    if (noteSaveTimeoutRef.current) {
      window.clearTimeout(noteSaveTimeoutRef.current)
    }

    noteSaveTimeoutRef.current = window.setTimeout(() => {
      upsertConceptNoteMutation.mutate({
        conceptKey: currentConceptKey,
        body: {
          title: conceptPanel.name,
          body: value,
        },
      }, {
        onError: () => toast({ message: '笔记保存失败，请稍后重试', type: 'error' }),
      })
    }, 360)
  }, [conceptPanel, currentConceptKey, toast, upsertConceptNoteMutation])

  const handleConfirmConcept = useCallback(() => {
    if (!conceptPanel) {
      return
    }

    if (conceptPanel.node_id && !conceptPanel.candidate_id) {
      toast({ message: '该概念已存在，可直接打开专文。', type: 'info' })
      return
    }

    const confirmById = (candidateId: string) => {
      confirmConceptCandidateMutation.mutate(
        { candidateId },
        {
          onSuccess: (candidate) => {
            setConceptPanel((previous) => previous
              ? {
                  ...previous,
                  candidate_id: candidate.candidate_id,
                  node_id: candidate.matched_node_id || previous.node_id,
                  concept_key: candidate.matched_node_id || `candidate:${candidate.candidate_id}`,
                  status: candidate.status,
                }
              : previous)
            toast({ message: '已确认概念并加入图谱。', type: 'success' })
          },
          onError: () => toast({ message: '确认概念失败，请重试', type: 'error' }),
        },
      )
    }

    if (conceptPanel.candidate_id) {
      confirmById(conceptPanel.candidate_id)
      return
    }

    createConceptCandidateMutation.mutate(
      {
        concept_text: conceptPanel.name,
        source_article_id: activeArticle?.kind === 'source' ? activeArticle.article_id : undefined,
        origin: 'manual',
      },
      {
        onSuccess: (candidate) => {
          confirmById(candidate.candidate_id)
        },
        onError: () => toast({ message: '创建概念失败，请重试', type: 'error' }),
      },
    )
  }, [
    activeArticle,
    conceptPanel,
    confirmConceptCandidateMutation,
    createConceptCandidateMutation,
    toast,
  ])

  const handleIgnoreConcept = useCallback(() => {
    if (!conceptPanel) {
      return
    }

    if (conceptPanel.candidate_id) {
      ignoreConceptCandidateMutation.mutate(conceptPanel.candidate_id, {
        onSuccess: () => {
          setConceptPanelOpen(false)
          toast({ message: '已忽略该候选概念。', type: 'info' })
        },
        onError: () => toast({ message: '忽略概念失败，请重试', type: 'error' }),
      })
      return
    }

    if (conceptPanel.node_id) {
      setConceptPanelOpen(false)
      return
    }

    createConceptCandidateMutation.mutate(
      {
        concept_text: conceptPanel.name,
        source_article_id: activeArticle?.kind === 'source' ? activeArticle.article_id : undefined,
        origin: 'manual',
      },
      {
        onSuccess: (candidate) => {
          ignoreConceptCandidateMutation.mutate(candidate.candidate_id, {
            onSuccess: () => {
              setConceptPanelOpen(false)
            },
          })
        },
        onError: () => toast({ message: '创建概念失败，请重试', type: 'error' }),
      },
    )
  }, [
    activeArticle,
    conceptPanel,
    createConceptCandidateMutation,
    ignoreConceptCandidateMutation,
    toast,
  ])

  const handleManualConceptMark = useCallback((selectedText: string) => {
    const normalized = selectedText.trim()
    if (!normalized) {
      return
    }

    const matched = conceptCatalog.find((concept) => (
      concept.name === normalized
      || concept.name.includes(normalized)
      || normalized.includes(concept.name)
    ))

    if (matched) {
      openConceptPanel({
        name: matched.name,
        node_id: matched.node_id,
        summary: matched.summary,
        concept_key: matched.node_id,
      })
      return
    }

    const existingCandidate = candidateByNormalizedText.get(normalizeText(normalized))
    if (existingCandidate) {
      openConceptPanel({
        name: existingCandidate.matched_concept_name || existingCandidate.concept_text,
        node_id: existingCandidate.matched_node_id || undefined,
        summary: existingCandidate.status === 'confirmed'
          ? '该概念已经确认，可以继续生成或打开专文。'
          : '手动标记的候选概念，等待确认。',
        candidate_id: existingCandidate.candidate_id,
        concept_key: existingCandidate.matched_node_id || `candidate:${existingCandidate.candidate_id}`,
        status: existingCandidate.status,
      })
      return
    }

    createConceptCandidateMutation.mutate(
      {
        concept_text: normalized,
        source_article_id: activeArticle?.kind === 'source' ? activeArticle.article_id : undefined,
        origin: 'manual',
      },
      {
        onSuccess: (candidate) => {
          openConceptPanel({
            name: candidate.concept_text,
            summary: '手动标记的候选概念，等待确认。',
            candidate_id: candidate.candidate_id,
            concept_key: `candidate:${candidate.candidate_id}`,
            status: candidate.status,
          })
        },
        onError: () => toast({ message: '标记概念失败，请重试', type: 'error' }),
      },
    )
  }, [activeArticle, candidateByNormalizedText, conceptCatalog, createConceptCandidateMutation, openConceptPanel, toast])

  const handleCommandSelect = useCallback((item: {
    kind: 'article' | 'concept' | 'note' | 'recent' | 'action'
    article_id?: string
    node_id?: string
    label: string
    action_id?: 'new-source-article' | 'return-guide' | 'open-library' | 'recent-history'
  }) => {
    setCommandOpen(false)
    setCommandQuery('')

    if (item.kind === 'article' || item.kind === 'recent') {
      if (item.article_id) {
        openArticle(item.article_id)
      }
      return
    }

    if (item.kind === 'concept' || item.kind === 'note') {
      openConceptPanel({
        name: item.label,
        node_id: item.node_id?.startsWith('nd_') ? item.node_id : undefined,
        concept_key: item.node_id,
      })
      return
    }

    switch (item.action_id) {
      case 'new-source-article':
        handleCreateSourceArticle()
        break
      case 'return-guide':
        openArticle(`guide:${topicId}`)
        break
      case 'open-library':
        setLibraryOpen(true)
        break
      case 'recent-history':
        toast({ message: '最近访问已在命令面板中展开', type: 'info' })
        break
    }
  }, [handleCreateSourceArticle, openArticle, openConceptPanel, toast, topicId])

  if (topicLoading || workspaceLoading || !guideArticle || !activeArticle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[color:var(--workspace-bg)]">
        <div className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--card)] px-6 py-5 text-sm text-[color:var(--muted-foreground)] shadow-sm">
          正在展开文章工作台…
        </div>
      </div>
    )
  }

  if (topicError || workspaceError || !topic) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[color:var(--workspace-bg)] px-6">
        <div className="max-w-md rounded-3xl border border-[color:var(--border)] bg-[color:var(--card)] p-6 shadow-sm">
          <h1 className="font-serif text-2xl text-[color:var(--foreground)]">加载失败</h1>
          <p className="mt-3 text-sm leading-6 text-[color:var(--muted-foreground)]">
            {topicError instanceof Error
              ? topicError.message
              : workspaceError instanceof Error
                ? workspaceError.message
                : '当前主题无法加载。'}
          </p>
          <div className="mt-4 flex gap-2">
            <Button onClick={() => clearWorkspaceTopicState(topicId)}>清理本地状态</Button>
            <Button variant="outline" onClick={() => refetchWorkspace()}>重试</Button>
          </div>
        </div>
      </div>
    )
  }

  const conceptArticleNeedsAttention = Boolean(
    activeArticle.kind === 'concept'
    && backlinks.length > 0
    && activeConceptDetail?.node.updated_at
    && sourceArticles.some((article) => article.updated_at > activeConceptDetail.node.updated_at),
  )
  const isRefreshingConceptArticle = Boolean(
    activeConceptNodeId
    && generateArticleMutation.isPending
    && generateArticleMutation.variables?.nodeId === activeConceptNodeId,
  )
  const practiceRoute = activeConceptNodeId
    ? buildPracticeRoute(topicId, activeConceptNodeId, { sessionId })
    : null

  const shellClass = 'mx-auto grid h-screen max-w-[1600px] grid-cols-[minmax(0,280px)_minmax(0,1fr)] gap-0 px-4 py-4 lg:px-6'

  return (
    <div className="min-h-screen bg-[color:var(--workspace-bg)] text-[color:var(--foreground)]">
      <div className={shellClass}>
        {libraryOpen ? (
          <div className="hidden overflow-hidden rounded-l-[28px] border border-[color:var(--border)] shadow-sm lg:block">
            <ArticleLibrarySidebar
              currentArticleId={activeArticle.article_id}
              library={librarySections}
              onSelectArticle={(article) => openArticle(article.article_id)}
              onCreateSourceArticle={handleCreateSourceArticle}
            />
          </div>
        ) : (
          <div className="hidden border-y border-l border-[color:var(--border)] bg-[color:var(--sidebar)] lg:flex lg:w-16 lg:flex-col lg:items-center lg:justify-start lg:rounded-l-[28px] lg:py-4">
            <button
              type="button"
              onClick={() => setLibraryOpen(true)}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--card)] p-2 text-[color:var(--foreground)] shadow-sm"
              aria-label="展开文章库"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="flex min-h-0 flex-col overflow-hidden rounded-[28px] border border-[color:var(--border)] bg-[color:var(--background)] shadow-sm">
          <div className="flex flex-col gap-3 border-b border-[color:var(--border)] px-4 py-3 sm:flex-row sm:items-start sm:justify-between lg:px-6">
            <div className="flex items-start gap-2 min-w-0">
              <Button variant="ghost" size="icon-sm" className="lg:hidden" aria-label="展开文章库" onClick={() => setLibraryOpen((open) => !open)}>
                <Menu className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon-sm" className="hidden lg:inline-flex" aria-label="切换文章库" onClick={() => setLibraryOpen((open) => !open)}>
                {libraryOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
              </Button>
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
                  文章优先工作台
                </p>
                <div className="flex items-center gap-2">
                  <p className="text-sm text-[color:var(--foreground)] break-words">{topic.title}</p>
                  <span className="shrink-0 inline-flex items-center rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-2 py-0.5 text-[10px] text-[color:var(--muted-foreground)]">
                    {{ build_system: '构建体系', fix_gap: '弥补短板', solve_task: '解决任务', prepare_expression: '准备表达', prepare_interview: '准备面试' }[topic.learning_intent] || topic.learning_intent}
                  </span>
                  {sessionId && (
                    <span className="shrink-0 inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-2 py-0.5 text-[10px] text-[color:var(--muted-foreground)]">
                      {sessionMinutes > 0 && `${sessionMinutes}:${String(sessionSeconds).padStart(2, '0')}`}
                      {visitedSessionNodeCount > 0 && ` · ${visitedSessionNodeCount} 节点`}
                    </span>
                  )}
                  {sessionId && mainlineGraph?.nodes && mainlineGraph.nodes.length > 0 && (
                    <div className="shrink-0 w-20">
                      <Progress value={visitedSessionNodeCount} max={mainlineGraph.nodes.length} size="sm" className="h-1.5" />
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 sm:justify-end">
              {practiceRoute ? (
                <Button variant="outline" size="sm" onClick={() => navigate(practiceRoute)}>
                  <BookOpenText className="h-4 w-4" />
                  去练习
                </Button>
              ) : null}
              <Button variant="outline" size="sm" onClick={() => setCommandOpen(true)}>
                <Search className="h-4 w-4" />
                搜索
              </Button>
              <Button variant="outline" size="sm" onClick={handleCreateSourceArticle}>
                <FilePenLine className="h-4 w-4" />
                新建源文章
              </Button>
              <Button size="sm" onClick={handleMarkComplete}>
                <CheckCircle2 className="h-4 w-4" />
                标记完成
              </Button>
            </div>
          </div>

          {libraryOpen && isMobile ? (
            <div className="border-b border-[color:var(--border)] lg:hidden">
              <ArticleLibrarySidebar
                currentArticleId={activeArticle.article_id}
                library={librarySections}
                onSelectArticle={(article) => openArticle(article.article_id)}
                onCreateSourceArticle={handleCreateSourceArticle}
              />
            </div>
          ) : null}

          <div ref={readerRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-5 lg:px-8 lg:py-8">
            <div className="mx-auto max-w-4xl space-y-8">
              <div className="flex flex-wrap items-center gap-2 text-sm text-[color:var(--muted-foreground)]">
                {trail.map((item, index) => (
                  <div key={item.article_id} className="flex items-center gap-2">
                    {index > 0 ? <span>/</span> : null}
                    <button
                      type="button"
                      className={item.article_id === activeArticle.article_id ? 'text-[color:var(--foreground)]' : 'hover:text-[color:var(--foreground)]'}
                      onClick={() => openArticle(item.article_id)}
                    >
                      {item.title}
                    </button>
                  </div>
                ))}
              </div>

              <ArticleHeader
                article={{
                  ...activeArticle,
                  description: activeArticle.description,
                }}
                sourceLabel={activeArticle.source_label}
                statusLabel={articleStatusLabel(activeArticle.article_id, activeArticle.article_id, trail, completedArticleIds)}
              />

              {analysisNotice ? (
                <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--card)] px-4 py-3 text-sm text-[color:var(--muted-foreground)] shadow-sm">
                  {analysisNotice}
                </div>
              ) : null}

              {conceptArticleNeedsAttention ? (
                <div className="flex flex-col gap-3 rounded-2xl border border-[color:var(--accent)]/25 bg-[color:var(--accent-soft)] px-4 py-3 text-sm text-[color:var(--foreground)] md:flex-row md:items-center md:justify-between">
                  <p>有新材料可更新：最近的源文章里出现了这篇概念的新提及。</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="self-start md:self-auto"
                    onClick={handleRefreshConceptArticle}
                    disabled={isRefreshingConceptArticle}
                  >
                    <RefreshCw className={isRefreshingConceptArticle ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />
                    {isRefreshingConceptArticle ? '刷新中' : '立即刷新专文'}
                  </Button>
                </div>
              ) : null}

              {activeArticle.kind === 'source' ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Button
                      variant={editMode ? 'outline' : 'default'}
                      size="sm"
                      onClick={() => setEditMode(false)}
                    >
                      <BookOpenText className="h-4 w-4" />
                      阅读
                    </Button>
                    <Button
                      variant={editMode ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setEditMode(true)}
                    >
                      <FilePenLine className="h-4 w-4" />
                      编辑
                    </Button>
                    {editMode ? (
                      <Button size="sm" onClick={handleSaveSourceArticle}>
                        保存并重新分析
                      </Button>
                    ) : null}
                  </div>

                  {editMode ? (
                    <div className="rounded-[28px] border border-[color:var(--border)] bg-[color:var(--card)] p-5 shadow-sm">
                      <Textarea
                        value={sourceDraft}
                        onChange={(event) => setSourceDraft(event.target.value)}
                        className="min-h-[420px] border-none bg-transparent px-0 py-0 text-[1.02rem] leading-8 shadow-none focus-visible:ring-0"
                      />
                    </div>
                  ) : (
                    <ArticleRenderer
                      articleId={activeArticle.article_id}
                      body={activeArticle.body}
                      conceptMap={conceptMap}
                      onConceptClick={(concept) => openConceptPanel(concept)}
                      onMarkConcept={handleManualConceptMark}
                    />
                  )}
                </div>
              ) : (
                <>
                  {activeArticle.kind === 'concept' ? (
                    <div className="rounded-[28px] border border-[color:var(--border)] bg-[color:var(--card)] p-5 shadow-sm">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
                        摘要与关键点
                      </p>
                      <p className="mt-3 text-base leading-7 text-[color:var(--foreground)]">
                        {activeConceptDetail?.node.summary || activeArticle.description}
                      </p>
                      <ul className="mt-4 space-y-2 text-sm leading-6 text-[color:var(--muted-foreground)]">
                        {conceptKeyPoints(activeConceptDetail).map((point) => (
                          <li key={point}>• {point}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <ArticleRenderer
                    articleId={activeArticle.article_id}
                    body={activeArticle.body}
                    conceptMap={conceptMap}
                    onConceptClick={(concept) => openConceptPanel(concept)}
                    onMarkConcept={handleManualConceptMark}
                  />
                </>
              )}

              {activeArticle.kind === 'concept' && backlinks.length > 0 ? (
                <details className="rounded-[28px] border border-[color:var(--border)] bg-[color:var(--card)] p-5 shadow-sm">
                  <summary className="cursor-pointer text-sm font-medium text-[color:var(--foreground)]">
                    被这些文章提及
                  </summary>
                  <div className="mt-4 space-y-3">
                    {backlinks.map((backlink) => (
                      <button
                        key={`${backlink.article_id}:${backlink.anchor_id}`}
                        type="button"
                        onClick={() => openArticle(backlink.article_id, { anchorId: backlink.anchor_id })}
                        className="block w-full rounded-2xl border border-[color:var(--border)] px-4 py-3 text-left hover:bg-[color:var(--background)]"
                      >
                        <p className="text-sm font-medium text-[color:var(--foreground)]">{backlink.title}</p>
                        <p className="mt-1 text-sm leading-6 text-[color:var(--muted-foreground)]">{backlink.snippet}</p>
                      </button>
                    ))}
                  </div>
                </details>
              ) : null}

              <ArticleFooterPanel
                recommendation={recommendation}
                knowledgeMap={knowledgeMap}
                onOpenArticle={openArticle}
              />
            </div>
          </div>
        </div>
      </div>

      <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
        <Command>
          <CommandInput
            value={commandQuery}
            onValueChange={setCommandQuery}
            placeholder="搜索文章、概念、笔记或动作…"
          />
          <CommandList>
            <CommandEmpty>没有匹配结果。</CommandEmpty>
            {commandGroups.map((group) => (
              <CommandGroup key={group.key} heading={group.title}>
                {group.items.map((item) => (
                  <CommandItem
                    key={item.id}
                    value={`${item.label} ${item.subtitle}`}
                    onSelect={() => handleCommandSelect(item)}
                  >
                    <div>
                      <p>{item.label}</p>
                      <p className="text-xs text-[color:var(--muted-foreground)]">{item.subtitle}</p>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </CommandDialog>

      {conceptPanel ? (
        isMobile ? (
          <Drawer open={conceptPanelOpen} onOpenChange={setConceptPanelOpen}>
            <DrawerContent>
              <DrawerHeader className="sr-only">
                <DrawerTitle>{conceptPanel.name}</DrawerTitle>
              </DrawerHeader>
              <ConceptDrawerContent
                concept={{
                  name: panelDetail?.node.name || conceptPanel.name,
                  summary: panelDetail?.node.summary || conceptPanel.summary || '候选概念，等待你确认。',
                  relations: panelRelations,
                }}
                generationState={panelGenerationState}
                noteValue={currentConceptNoteValue}
                onNoteChange={handleConceptNoteChange}
                onOpenArticle={() => conceptPanel.node_id && openArticle(`concept:${conceptPanel.node_id}`)}
                onRetryGeneration={handleRetryPanelGeneration}
                onConfirmConcept={handleConfirmConcept}
                onIgnoreConcept={handleIgnoreConcept}
              />
            </DrawerContent>
          </Drawer>
        ) : (
          <Sheet open={conceptPanelOpen} onOpenChange={setConceptPanelOpen}>
            <SheetContent className="w-[420px] max-w-[420px] border-l border-[color:var(--border)] bg-[color:var(--background)] p-0" showCloseButton={false}>
              <ConceptDrawerContent
                concept={{
                  name: panelDetail?.node.name || conceptPanel.name,
                  summary: panelDetail?.node.summary || conceptPanel.summary || '候选概念，等待你确认。',
                  relations: panelRelations,
                }}
                generationState={panelGenerationState}
                noteValue={currentConceptNoteValue}
                onNoteChange={handleConceptNoteChange}
                onOpenArticle={() => conceptPanel.node_id && openArticle(`concept:${conceptPanel.node_id}`)}
                onRetryGeneration={handleRetryPanelGeneration}
                onConfirmConcept={handleConfirmConcept}
                onIgnoreConcept={handleIgnoreConcept}
              />
            </SheetContent>
          </Sheet>
        )
      ) : null}
    </div>
  )
}
