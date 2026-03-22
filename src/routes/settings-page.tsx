import { useMemo, useState } from 'react'
import { Settings, Save, RotateCcw, Monitor, Cpu, Database, AlertTriangle, Key, Globe, Bot, Download } from 'lucide-react'

import {
  useSettingsQuery,
  useUpdateSettingsMutation,
  useHealthQuery,
  useSystemCapabilitiesQuery,
  useExportTopicMutation,
  useResolvedTopicContext,
  useTopicListQuery,
} from '../hooks'
import { Card, Button, LoadingSkeleton, ErrorState } from '../components/shared'
import { useToast } from '../components/ui/toast'
import { sortTopicsByUpdatedAtDesc } from '../lib/navigation-context'
import type { LearningIntent, TopicMode, Settings as SettingsType } from '../types'

export function SettingsPage() {
  const {
    data: settings,
    isLoading,
    error: settingsError,
    refetch: refetchSettings,
  } = useSettingsQuery()
  const { data: health } = useHealthQuery()
  const { data: capabilities } = useSystemCapabilitiesQuery()
  const { topicId: resolvedTopicId } = useResolvedTopicContext()
  const { data: topics = [] } = useTopicListQuery({ status: 'active' })
  const activeTopics = useMemo(() => sortTopicsByUpdatedAtDesc(topics), [topics])
  const updateMutation = useUpdateSettingsMutation()
  const toast = useToast()

  const [exportFormat, setExportFormat] = useState<'markdown' | 'json' | 'anki'>('markdown')
  const [manualExportTopicId, setManualExportTopicId] = useState<string | null>(null)
  const [formOverride, setFormOverride] = useState<Partial<SettingsType>>({})
  const form = settings ? { ...settings, ...formOverride } : null
  const exportTopicId = useMemo(() => {
    if (manualExportTopicId && activeTopics.some((topic) => topic.topic_id === manualExportTopicId)) {
      return manualExportTopicId
    }

    if (resolvedTopicId) {
      return resolvedTopicId
    }

    return activeTopics[0]?.topic_id || ''
  }, [activeTopics, manualExportTopicId, resolvedTopicId])

  const exportMutation = useExportTopicMutation(exportTopicId)

  const handleSave = async () => {
    if (!form) return

    // Validate openai_base_url format
    const baseUrl = form.openai_base_url?.trim()
    if (baseUrl && !baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
      toast({ message: 'Base URL 必须以 http:// 或 https:// 开头', type: 'warning' })
      return
    }

    try {
      await updateMutation.mutateAsync(form)
      toast({ message: '设置已保存', type: 'success' })
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : '保存失败，请稍后重试', type: 'error' })
    }
  }

  const handleExport = async () => {
    if (!exportTopicId) {
      toast({ message: '当前没有可导出的主题', type: 'warning' })
      return
    }

    try {
      const res = await exportMutation.mutateAsync({ export_type: exportFormat })
      const blob = new Blob([res.content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      // Sanitize filename: strip path separators to prevent path traversal
      const safeName = res.filename.replace(/[/\\]/g, '_').replace(/\.\./g, '')
      anchor.download = safeName || 'export'
      anchor.click()
      URL.revokeObjectURL(url)
      toast({ message: `已导出 ${res.filename}`, type: 'success' })
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : '导出失败，请稍后重试', type: 'error' })
    }
  }

  const handleReset = () => {
    setFormOverride({})
    setManualExportTopicId(null)
  }

  if (isLoading) return <div className="p-6"><LoadingSkeleton lines={5} /></div>
  if (settingsError) {
    return (
      <div className="p-6">
        <ErrorState
          message={settingsError instanceof Error ? settingsError.message : '设置加载失败'}
          onRetry={() => { void refetchSettings() }}
        />
      </div>
    )
  }
  if (!form) return null

  const isApiKeyMasked = (value: string) => value && value.includes('••••')

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <Settings size={24} className="text-gray-500" />
        设置
      </h1>

      {health && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <Monitor size={14} />
            服务状态
          </h2>
          <div className="grid grid-cols-3 gap-3">
            <StatusDot label="API" ok={health.services.api} />
            <StatusDot label="SQLite" ok={health.services.sqlite} />
            <StatusDot label="Neo4j" ok={health.services.neo4j} />
            <StatusDot label="LanceDB" ok={health.services.lancedb} />
            <StatusDot label="模型" ok={health.services.model_provider} />
            <StatusDot label="Ollama" ok={health.services.ollama} />
          </div>
        </Card>
      )}

      {capabilities && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
            <Cpu size={14} />
            功能可用性
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <StatusDot label="AI Provider" ok={capabilities.ai_provider !== null} />
            <StatusDot label="Ollama" ok={capabilities.ollama_enabled} />
          </div>
          {!capabilities.ai_provider && (
            <p className="text-xs text-amber-600 mt-3">
              未配置 AI Provider，AI 功能将使用降级模式
            </p>
          )}
          {capabilities.ai_model && (
            <p className="text-xs text-gray-500 mt-2">
              当前模型: {capabilities.ai_model}
            </p>
          )}
        </Card>
      )}

      <Card>
        <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
          <Key size={14} />
          API 配置
        </h2>
        <p className="text-xs text-gray-500 mb-4">配置 AI 模型提供商，支持 OpenAI 官方或中转站。保存后立即生效。</p>
        <div className="space-y-4">
          <div>
            <label htmlFor="settings-openai-api-key" className="block text-xs text-gray-600 mb-1">API Key</label>
            <input
              id="settings-openai-api-key"
              name="openai_api_key"
              type="password"
              placeholder={isApiKeyMasked(form.openai_api_key) ? '已配置，留空保持不变' : 'sk-...'}
              value={isApiKeyMasked(form.openai_api_key) ? '' : form.openai_api_key}
              onChange={(event) => setFormOverride((current) => ({ ...current, openai_api_key: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              autoComplete="new-password"
            />
            {isApiKeyMasked(form.openai_api_key) && (
              <p className="text-xs text-green-600 mt-1">API Key 已配置，留空则保持不变。</p>
            )}
          </div>
          <div>
            <label htmlFor="settings-openai-base-url" className="block text-xs text-gray-600 mb-1 flex items-center gap-1">
              <Globe size={12} />
              Base URL
            </label>
            <input
              id="settings-openai-base-url"
              name="openai_base_url"
              type="text"
              placeholder="https://api.openai.com/v1"
              autoComplete="off"
              value={form.openai_base_url}
              onChange={(event) => setFormOverride((current) => ({ ...current, openai_base_url: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="text-xs text-gray-500 mt-1">OpenAI 官方填写 `https://api.openai.com/v1`，中转站填写对应地址。</p>
          </div>
          <div>
            <label htmlFor="settings-openai-model-default" className="block text-xs text-gray-600 mb-1 flex items-center gap-1">
              <Bot size={12} />
              默认模型
            </label>
            <input
              id="settings-openai-model-default"
              name="openai_model_default"
              type="text"
              placeholder="gpt-4o"
              autoComplete="off"
              value={form.openai_model_default}
              onChange={(event) => setFormOverride((current) => ({ ...current, openai_model_default: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label htmlFor="settings-openai-embed-model" className="block text-xs text-gray-600 mb-1">Embedding 模型</label>
            <input
              id="settings-openai-embed-model"
              name="openai_embed_model"
              type="text"
              placeholder="text-embedding-3-small"
              autoComplete="off"
              value={form.openai_embed_model}
              onChange={(event) => setFormOverride((current) => ({ ...current, openai_embed_model: event.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-gray-700 mb-4">学习设置</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="settings-default-learning-intent" className="block text-xs text-gray-600 mb-1">默认学习意图</label>
            <select
              id="settings-default-learning-intent"
              name="default_learning_intent"
              value={form.default_learning_intent}
              onChange={(event) => setFormOverride((current) => ({ ...current, default_learning_intent: event.target.value as LearningIntent }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="build_system">构建体系</option>
              <option value="fix_gap">弥补短板</option>
              <option value="solve_task">解决任务</option>
              <option value="prepare_expression">准备表达</option>
              <option value="prepare_interview">面试准备</option>
            </select>
          </div>
          <div>
            <label htmlFor="settings-default-mode" className="block text-xs text-gray-600 mb-1">默认模式</label>
            <select
              id="settings-default-mode"
              name="default_mode"
              value={form.default_mode}
              onChange={(event) => setFormOverride((current) => ({ ...current, default_mode: event.target.value as TopicMode }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="full_system">完整体系</option>
              <option value="shortest_path">最短路径</option>
            </select>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-gray-700 mb-4">图谱设置</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="settings-max-graph-depth" className="block text-xs text-gray-600 mb-1">最大图谱深度</label>
            <input
              id="settings-max-graph-depth"
              name="max_graph_depth"
              type="number"
              min={1}
              max={5}
              value={form.max_graph_depth}
              autoComplete="off"
              onChange={(event) => setFormOverride((current) => ({ ...current, max_graph_depth: Math.min(Math.max(Number(event.target.value), 1), 5) }))}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-gray-700 mb-4">练习设置</h2>
        <div className="space-y-4">
          <ToggleRow
            id="settings-auto-start-practice"
            name="auto_start_practice"
            title="自动开始练习"
            description="完成节点学习后自动进入练习"
            checked={form.auto_start_practice}
            onChange={(checked) => setFormOverride((current) => ({ ...current, auto_start_practice: checked }))}
          />
          <ToggleRow
            id="settings-auto-generate-summary"
            name="auto_generate_summary"
            title="自动生成总结"
            description="结束会话时自动生成学习总结"
            checked={form.auto_generate_summary}
            onChange={(checked) => setFormOverride((current) => ({ ...current, auto_generate_summary: checked }))}
          />
          <ToggleRow
            id="settings-ollama-enabled"
            name="ollama_enabled"
            title="启用 Ollama 本地回退"
            description="当远程模型不可用时使用本地 Ollama"
            checked={form.ollama_enabled}
            onChange={(checked) => setFormOverride((current) => ({ ...current, ollama_enabled: checked }))}
          />
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
          <Database size={14} />
          数据管理
        </h2>
        <div className="space-y-3">
          <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg">
            <AlertTriangle size={14} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-xs text-amber-700 font-medium">数据目录</p>
              <p className="text-xs text-amber-600 mt-1">
                应用数据存储在本地 data/ 目录下，包括 SQLite、LanceDB 和 Neo4j 相关数据，请勿手动修改。
              </p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">应用版本</span>
            <span className="text-xs text-gray-700 font-medium">AxonClone MVP v0.1.0</span>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 space-y-3">
            <p className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1.5">
              <Download size={12} />
              导出主题
            </p>
            {activeTopics.length > 0 ? (
              <>
                <div>
                  <label htmlFor="settings-export-topic" className="block text-xs text-gray-600 mb-1">导出目标</label>
                  <select
                    id="settings-export-topic"
                    name="export_topic_id"
                    value={exportTopicId}
                    onChange={(event) => setManualExportTopicId(event.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    {activeTopics.map((topic) => (
                      <option key={topic.topic_id} value={topic.topic_id}>
                        {topic.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <label htmlFor="settings-export-format" className="sr-only">导出格式</label>
                  <select
                    id="settings-export-format"
                    name="export_format"
                    value={exportFormat}
                    onChange={(event) => setExportFormat(event.target.value as typeof exportFormat)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="markdown">Markdown</option>
                    <option value="json">JSON</option>
                    <option value="anki">Anki (TXT)</option>
                  </select>
                  <Button size="sm" onClick={handleExport} loading={exportMutation.isPending}>
                    <Download size={14} />
                    导出
                  </Button>
                </div>
              </>
            ) : (
              <p className="text-xs text-gray-500">当前没有可导出的活跃主题。</p>
            )}
          </div>
        </div>
      </Card>

      <div className="flex items-center gap-3 pb-8">
        <Button onClick={handleSave} loading={updateMutation.isPending}>
          <Save size={16} />
          保存设置
          {Object.keys(formOverride).length > 0 && (
            <span className="ml-1.5 inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
              {Object.keys(formOverride).length} 项未保存
            </span>
          )}
        </Button>
        <Button variant="ghost" onClick={handleReset}>
          <RotateCcw size={16} />
          重置
        </Button>
      </div>
    </div>
  )
}

function StatusDot({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-xs text-gray-600">{label}</span>
    </div>
  )
}

function ToggleRow(args: {
  id: string
  name: string
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <label htmlFor={args.id} className="min-w-0">
        <p className="text-sm text-gray-700">{args.title}</p>
        <p className="text-xs text-gray-500">{args.description}</p>
      </label>
      <label htmlFor={args.id} className="relative inline-flex items-center cursor-pointer">
        <input
          id={args.id}
          name={args.name}
          type="checkbox"
          checked={args.checked}
          onChange={(event) => args.onChange(event.target.checked)}
          className="sr-only peer"
        />
        <div className="w-9 h-5 bg-gray-200 rounded-full peer peer-checked:bg-indigo-600 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
      </label>
    </div>
  )
}
