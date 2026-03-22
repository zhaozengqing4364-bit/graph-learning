import { BookOpen, Check, CircleOff, Sparkles } from 'lucide-react'

import { Button } from '../../components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { Textarea } from '../../components/ui/textarea'

interface ConceptDrawerContentProps {
  concept: {
    name: string
    summary: string
    relations: {
      title: string
      items: string[]
    }
  }
  generationState: 'idle' | 'generating' | 'ready' | 'failed'
  noteValue: string
  onNoteChange: (value: string) => void
  onOpenArticle: () => void
  onRetryGeneration?: () => void
  onConfirmConcept: () => void
  onIgnoreConcept: () => void
}

export function ConceptDrawerContent({
  concept,
  generationState,
  noteValue,
  onNoteChange,
  onOpenArticle,
  onRetryGeneration,
  onConfirmConcept,
  onIgnoreConcept,
}: ConceptDrawerContentProps) {
  return (
    <div className="flex h-full flex-col gap-5 bg-[color:var(--background)] p-5">
      <header className="space-y-3 border-b border-[color:var(--border)] pb-5">
        <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)] shadow-sm">
          <Sparkles className="h-3.5 w-3.5" />
          概念抽屉
        </div>
        <div className="space-y-2">
          <h2 className="font-serif text-3xl leading-tight text-[color:var(--foreground)]">
            {concept.name}
          </h2>
          <p className="text-sm leading-6 text-[color:var(--muted-foreground)]">
            {concept.summary}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={onConfirmConcept}>
            <Check className="h-4 w-4" />
            确认概念
          </Button>
          <Button variant="ghost" size="sm" onClick={onIgnoreConcept}>
            <CircleOff className="h-4 w-4" />
            忽略
          </Button>
          {generationState === 'ready' ? (
            <Button size="sm" onClick={onOpenArticle}>
              <BookOpen className="h-4 w-4" />
              打开专文
            </Button>
          ) : generationState === 'failed' ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs text-amber-700">
              生成失败
              {onRetryGeneration && (
                <button type="button" className="underline hover:text-amber-900" onClick={onRetryGeneration}>重试</button>
              )}
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full border border-[color:var(--border)] px-3 py-1 text-xs text-[color:var(--muted-foreground)]">
              {generationState === 'generating' ? '后台生成中' : '等待生成'}
            </span>
          )}
        </div>
      </header>

      <Tabs defaultValue="overview" className="min-h-0 flex-1">
        <TabsList variant="line">
          <TabsTrigger value="overview">概念</TabsTrigger>
          <TabsTrigger value="notes">我的笔记</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 pt-4">
          {concept.relations.items.length > 0 && (
          <section className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--card)] p-4 shadow-sm">
            <p className="text-xs uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
              {concept.relations.title}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {concept.relations.items.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-[color:var(--border)] px-2.5 py-1 text-xs text-[color:var(--foreground)]"
                >
                  {item}
                </span>
              ))}
            </div>
          </section>
          )}
        </TabsContent>

        <TabsContent value="notes" className="pt-4">
          <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--card)] p-4 shadow-sm">
            <Textarea
              value={noteValue}
              onChange={(event) => onNoteChange(event.target.value)}
              placeholder="把你对这个概念的理解、疑惑和例子记在这里。"
              className="min-h-40 border-none bg-transparent px-0 py-0 text-sm leading-6 shadow-none focus-visible:ring-0"
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
