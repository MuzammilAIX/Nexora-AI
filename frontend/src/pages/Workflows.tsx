import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Play,
  Clock3,
  Loader2,
  Edit3,
  ArrowUpRight,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  Activity,
  AlertCircle,
  X,
  Save,
  Workflow as WorkflowIcon,
  CalendarClock,
  ListChecks,
  Filter,
} from 'lucide-react'

interface Execution {
  id: string
  status: string
  created_at?: string
  started_at?: string
  user_request?: string
  duration?: string | number
  duration_ms?: number
  error?: string
}

type StatusFilter = 'all' | 'completed' | 'failed' | 'running' | 'pending'

const DEFAULT_NAME = 'Lead Qualification'
const DEFAULT_DESCRIPTION =
  'Automated lead scoring and follow-up task preparation.'

const WORKFLOW_KEY = 'lead-qualification'
const STORAGE_KEY = 'nexora_workflow_display'

function formatDate(value?: string) {
  if (!value) return 'Not available'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return 'Not available'

  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatDuration(execution: Execution) {
  if (execution.duration) return String(execution.duration)

  if (typeof execution.duration_ms === 'number') {
    return `${(execution.duration_ms / 1000).toFixed(2)}s`
  }

  return '—'
}

function normalizeStatus(status: string) {
  const value = status?.toLowerCase() || 'pending'

  if (['success', 'completed', 'complete'].includes(value)) {
    return 'completed'
  }

  if (['failed', 'error'].includes(value)) return 'failed'

  if (['running', 'in_progress', 'processing'].includes(value)) {
    return 'running'
  }

  if (['queued', 'pending', 'waiting'].includes(value)) {
    return 'pending'
  }

  return value
}

function StatusBadge({ status }: { status: string }) {
  const normalized = normalizeStatus(status)

  const styles: Record<string, string> = {
    completed:
      'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    failed:
      'bg-red-500/10 text-red-600 dark:text-red-400',
    running:
      'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    pending:
      'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  }

  const icons: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 size={14} />,
    failed: <XCircle size={14} />,
    running: <Loader2 size={14} className="animate-spin" />,
    pending: <Clock3 size={14} />,
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${
        styles[normalized] || styles.pending
      }`}
    >
      {icons[normalized] || <Clock3 size={14} />}
      {normalized.replace('_', ' ')}
    </span>
  )
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  description: string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="bg-panel border border-border rounded-xl p-5 min-w-0">
      <div className="flex items-center justify-between gap-3 mb-4">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
          {label}
        </p>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={18} />
        </div>
      </div>

      <p className="text-2xl font-bold text-slate-900 dark:text-white">
        {value}
      </p>

      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
        {description}
      </p>
    </div>
  )
}

export function Workflows() {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [executing, setExecuting] = useState(false)

  const [editOpen, setEditOpen] = useState(false)
  const [executeOpen, setExecuteOpen] = useState(false)

  const [workflowName, setWorkflowName] = useState(DEFAULT_NAME)
  const [workflowDescription, setWorkflowDescription] =
    useState(DEFAULT_DESCRIPTION)

  const [editName, setEditName] = useState(DEFAULT_NAME)
  const [editDescription, setEditDescription] =
    useState(DEFAULT_DESCRIPTION)

  const [request, setRequest] = useState(
    'Qualify new leads and prepare follow-up tasks.'
  )

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>('all')

  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Restore locally saved display settings.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)

      if (saved) {
        const parsed = JSON.parse(saved)

        if (typeof parsed.name === 'string') {
          setWorkflowName(parsed.name)
          setEditName(parsed.name)
        }

        if (typeof parsed.description === 'string') {
          setWorkflowDescription(parsed.description)
          setEditDescription(parsed.description)
        }
      }
    } catch {
      console.warn('Could not restore workflow display settings.')
    }
  }, [])

  const fetchExecutions = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    setError('')

    try {
      const token = localStorage.getItem('nexora_token')

      if (!token) {
        throw new Error('Your session is missing. Please sign in again.')
      }

      const response = await fetch('/api/v1/orchestrator/runs', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error(
          `Unable to load executions (${response.status}).`
        )
      }

      const data = await response.json()

      const records = Array.isArray(data)
        ? data
        : Array.isArray(data?.runs)
          ? data.runs
          : []

      setExecutions(records)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred while loading executions.'
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchExecutions()
  }, [fetchExecutions])

  const stats = useMemo(() => {
    const completed = executions.filter(
      e => normalizeStatus(e.status) === 'completed'
    ).length

    const failed = executions.filter(
      e => normalizeStatus(e.status) === 'failed'
    ).length

    const running = executions.filter(
      e => normalizeStatus(e.status) === 'running'
    ).length

    const pending = executions.filter(
      e => normalizeStatus(e.status) === 'pending'
    ).length

    const finished = completed + failed

    return {
      total: executions.length,
      completed,
      failed,
      running,
      pending,
      successRate: finished
        ? Math.round((completed / finished) * 100)
        : 0,
    }
  }, [executions])

  const filteredExecutions = useMemo(() => {
    return executions.filter(execution => {
      const status = normalizeStatus(execution.status)

      const matchesStatus =
        statusFilter === 'all' || status === statusFilter

      const query = search.toLowerCase()

      const matchesSearch =
        !query ||
        execution.id?.toLowerCase().includes(query) ||
        execution.user_request?.toLowerCase().includes(query) ||
        status.includes(query)

      return matchesStatus && matchesSearch
    })
  }, [executions, search, statusFilter])

  function saveWorkflow() {
    if (!editName.trim() || !editDescription.trim()) {
      setError('Workflow name and description are required.')
      return
    }

    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          name: editName.trim(),
          description: editDescription.trim(),
        })
      )

      setWorkflowName(editName.trim())
      setWorkflowDescription(editDescription.trim())
      setEditOpen(false)
      setError('')
      setSuccessMessage(
        'Workflow display settings saved in this browser.'
      )
    } catch {
      setError('Unable to save workflow display settings.')
    }
  }

  async function handleExecute() {
    if (!request.trim()) {
      setError('Please enter a workflow request.')
      return
    }

    setExecuting(true)
    setError('')
    setSuccessMessage('')

    try {
      const token = localStorage.getItem('nexora_token')

      if (!token) {
        throw new Error('Your session is missing. Please sign in again.')
      }

      const response = await fetch('/api/v1/orchestrator/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_request: request.trim(),
          workflow_id: WORKFLOW_KEY,
        }),
      })

      const result = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(
          result?.detail ||
          result?.message ||
          `Workflow execution failed (${response.status}).`
        )
      }

      setExecuteOpen(false)
      setSuccessMessage(
        'Workflow request submitted successfully. Check execution history for its progress.'
      )

      await fetchExecutions(true)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to execute the workflow.'
      )
    } finally {
      setExecuting(false)
    }
  }

  function openEditor() {
    setEditName(workflowName)
    setEditDescription(workflowDescription)
    setError('')
    setEditOpen(true)
  }

  return (
    <div className="min-h-screen bg-background p-4 md:p-6 space-y-6">

      {/* PAGE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <WorkflowIcon
              size={21}
              className="text-accent"
            />
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              Workflows
            </h1>
          </div>

          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage, execute and monitor your business automation workflows.
          </p>
        </div>

        <button
          onClick={() => fetchExecutions(true)}
          disabled={refreshing || loading}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-panel text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-panelHover disabled:opacity-50 transition-colors"
        >
          <RefreshCw
            size={16}
            className={refreshing ? 'animate-spin' : ''}
          />
          Refresh data
        </button>
      </div>

      {/* NOTIFICATIONS */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-red-600 dark:text-red-400">
          <AlertCircle size={19} className="shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">{error}</div>
          <button
            onClick={() => setError('')}
            aria-label="Dismiss error"
          >
            <X size={17} />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="flex items-start gap-3 p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 size={18} className="shrink-0" />
          <p className="text-sm flex-1">{successMessage}</p>
          <button
            onClick={() => setSuccessMessage('')}
            aria-label="Dismiss message"
          >
            <X size={17} />
          </button>
        </div>
      )}

      {/* WORKFLOW OVERVIEW */}
      <section className="bg-panel border border-border rounded-xl p-5 md:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">

          <div className="flex items-start gap-4 min-w-0">
            <div className="p-3 rounded-xl bg-accent/10 text-accent shrink-0">
              <WorkflowIcon size={25} />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  {workflowName}
                </h2>

                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  Workflow template
                </span>
              </div>

              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
                {workflowDescription}
              </p>

              <div className="flex items-center gap-2 mt-3">
                <span className="text-xs text-slate-400">
                  Workflow key:
                </span>
                <code className="text-xs font-mono text-accent bg-accent/5 px-2 py-1 rounded">
                  {WORKFLOW_KEY}
                </code>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 shrink-0">
            <button
              onClick={openEditor}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-panel text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-panelHover transition-colors"
            >
              <Edit3 size={16} />
              Edit details
            </button>

            <button
              onClick={() => {
                setError('')
                setExecuteOpen(true)
              }}
              disabled={executing}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent text-white text-sm font-semibold hover:bg-accentHover disabled:opacity-50 transition-colors"
            >
              <Play size={16} />
              Execute workflow
            </button>
          </div>
        </div>
      </section>

      {/* EXECUTION METRICS */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Execution overview
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Calculated from the execution records currently returned by the API.
            </p>
          </div>
          <span className="text-xs text-slate-400">
            {loading ? 'Updating...' : 'Live API data'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <MetricCard
            label="Total executions"
            value={loading ? '—' : stats.total}
            description="Records returned by the API"
            icon={Activity}
            color="bg-violet-500/10 text-violet-500"
          />

          <MetricCard
            label="Successful runs"
            value={loading ? '—' : stats.completed}
            description="Completed executions"
            icon={CheckCircle2}
            color="bg-emerald-500/10 text-emerald-500"
          />

          <MetricCard
            label="Failed executions"
            value={loading ? '—' : stats.failed}
            description="Executions requiring investigation"
            icon={AlertCircle}
            color="bg-red-500/10 text-red-500"
          />

          <MetricCard
            label="Success rate"
            value={loading ? '—' : `${stats.successRate}%`}
            description="Completed / completed and failed"
            icon={ListChecks}
            color="bg-blue-500/10 text-blue-500"
          />
        </div>
      </section>

      {/* EXECUTION STATUS */}
      <section className="bg-panel border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-accent" />
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">
            Execution status
          </h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              label: 'Completed',
              value: stats.completed,
              color: 'bg-emerald-500',
            },
            {
              label: 'Failed',
              value: stats.failed,
              color: 'bg-red-500',
            },
            {
              label: 'Running',
              value: stats.running,
              color: 'bg-blue-500',
            },
            {
              label: 'Pending',
              value: stats.pending,
              color: 'bg-amber-500',
            },
          ].map(item => (
            <div
              key={item.label}
              className="flex items-center gap-3 p-3 rounded-lg bg-background border border-border"
            >
              <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
              <div>
                <p className="text-xl font-bold text-slate-900 dark:text-white">
                  {loading ? '—' : item.value}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {item.label}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* EXECUTION HISTORY */}
      <section className="bg-panel border border-border rounded-xl overflow-hidden">
        <div className="p-5 border-b border-border">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Execution history
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Review workflow activity and execution outcomes.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search executions..."
                  className="w-full sm:w-56 pl-9 pr-3 py-2.5 rounded-lg border border-border bg-background text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-accent"
                />
              </div>

              <div className="relative">
                <Filter
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
                />
                <select
                  value={statusFilter}
                  onChange={e =>
                    setStatusFilter(e.target.value as StatusFilter)
                  }
                  className="w-full sm:w-40 pl-9 pr-3 py-2.5 rounded-lg border border-border bg-background text-sm text-slate-900 dark:text-white focus:outline-none focus:border-accent appearance-none"
                >
                  <option value="all">All statuses</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="running">Running</option>
                  <option value="pending">Pending</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center">
            <Loader2 className="w-7 h-7 animate-spin text-accent mb-3" />
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Loading execution records...
            </p>
          </div>
        ) : executions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-14 h-14 rounded-full bg-accent/10 text-accent flex items-center justify-center mx-auto mb-4">
              <CalendarClock size={25} />
            </div>
            <h3 className="font-semibold text-slate-900 dark:text-white">
              No executions found
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
              Execute your first workflow to start tracking automation activity.
            </p>
            <button
              onClick={() => setExecuteOpen(true)}
              className="mt-4 inline-flex items-center gap-2 text-sm text-accent font-semibold hover:underline"
            >
              <Play size={15} />
              Execute workflow
            </button>
          </div>
        ) : filteredExecutions.length === 0 ? (
          <div className="p-10 text-center">
            <Search size={25} className="mx-auto text-slate-400 mb-3" />
            <p className="text-sm font-medium text-slate-900 dark:text-white">
              No matching executions
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Try another search term or status filter.
            </p>
            <button
              onClick={() => {
                setSearch('')
                setStatusFilter('all')
              }}
              className="text-sm text-accent mt-3 font-medium"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left min-w-[750px]">
                <thead>
                  <tr className="bg-background border-b border-border">
                    {[
                      'Execution ID',
                      'Status',
                      'Started at',
                      'Request',
                      'Duration',
                    ].map(label => (
                      <th
                        key={label}
                        className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
                      >
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {filteredExecutions.map(execution => (
                    <tr
                      key={execution.id}
                      className="border-b border-border last:border-0 hover:bg-panelHover transition-colors"
                    >
                      <td className="px-5 py-4">
                        <span className="font-mono text-xs text-accent">
                          #{execution.id?.slice(0, 8) || 'unknown'}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge status={execution.status} />
                      </td>

                      <td className="px-5 py-4 text-sm text-slate-600 dark:text-slate-300 whitespace-nowrap">
                        {formatDate(
                          execution.started_at || execution.created_at
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <p className="text-sm text-slate-800 dark:text-slate-200 max-w-sm truncate">
                          {execution.user_request || 'No request provided'}
                        </p>
                        {execution.error && (
                          <p className="text-xs text-red-500 mt-1 max-w-sm truncate">
                            {execution.error}
                          </p>
                        )}
                      </td>

                      <td className="px-5 py-4 text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {formatDuration(execution)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="px-5 py-3 border-t border-border flex flex-col sm:flex-row justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span>
                Showing {filteredExecutions.length} of {executions.length} loaded executions
              </span>
              <span>Data supplied by the execution API</span>
            </div>
          </>
        )}
      </section>

      {/* WORKFLOW INFORMATION */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <WorkflowIcon size={19} className="text-accent" />
            <h2 className="font-semibold text-slate-900 dark:text-white">
              Workflow information
            </h2>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                Template name
              </p>
              <p className="text-sm font-medium text-slate-900 dark:text-white">
                {workflowName}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                Description
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300">
                {workflowDescription}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                Workflow key
              </p>
              <code className="text-xs text-accent">
                {WORKFLOW_KEY}
              </code>
            </div>

            <button
              onClick={openEditor}
              className="text-sm text-accent font-semibold inline-flex items-center gap-2 hover:underline"
            >
              Edit workflow details
              <ArrowUpRight size={15} />
            </button>
          </div>
        </div>

        <div className="bg-panel border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={19} className="text-accent" />
            <h2 className="font-semibold text-slate-900 dark:text-white">
              Execution insights
            </h2>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                Successful executions
              </span>
              <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                {stats.completed}
              </span>
            </div>

            <div className="w-full h-2 rounded-full bg-background overflow-hidden">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all"
                style={{
                  width: `${stats.total ? (stats.completed / stats.total) * 100 : 0}%`,
                }}
              />
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                Failed executions
              </span>
              <span className="text-sm font-semibold text-red-500">
                {stats.failed}
              </span>
            </div>

            <div className="w-full h-2 rounded-full bg-background overflow-hidden">
              <div
                className="h-full rounded-full bg-red-500 transition-all"
                style={{
                  width: `${stats.total ? (stats.failed / stats.total) * 100 : 0}%`,
                }}
              />
            </div>

            <p className="text-xs text-slate-400 pt-1">
              These ratios represent the loaded execution records, not a system-wide health measurement.
            </p>
          </div>
        </div>
      </section>

      {/* EDIT WORKFLOW MODAL */}
      {editOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onMouseDown={e => {
            if (e.target === e.currentTarget) setEditOpen(false)
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-workflow-title"
            className="bg-panel border border-border rounded-xl shadow-2xl w-full max-w-lg overflow-hidden"
          >
            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3
                  id="edit-workflow-title"
                  className="text-lg font-bold text-slate-900 dark:text-white"
                >
                  Edit workflow details
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Update the displayed template information.
                </p>
              </div>

              <button
                onClick={() => setEditOpen(false)}
                className="p-2 rounded-lg hover:bg-panelHover text-slate-500"
                aria-label="Close editor"
              >
                <X size={19} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-800 dark:text-slate-200 mb-2">
                  Workflow name
                </label>
                <input
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                  maxLength={100}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-slate-900 dark:text-white focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-800 dark:text-slate-200 mb-2">
                  Description
                </label>
                <textarea
                  value={editDescription}
                  onChange={e => setEditDescription(e.target.value)}
                  rows={4}
                  maxLength={500}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-slate-900 dark:text-white resize-none focus:outline-none focus:border-accent"
                />
              </div>

              <p className="text-xs text-amber-600 dark:text-amber-400">
                These edits update the local display settings only. Server-side workflow definition editing requires a dedicated backend API.
              </p>
            </div>

            <div className="p-5 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => setEditOpen(false)}
                className="px-4 py-2.5 text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white"
              >
                Cancel
              </button>

              <button
                onClick={saveWorkflow}
                className="px-4 py-2.5 bg-accent hover:bg-accentHover text-white rounded-lg text-sm font-semibold flex items-center gap-2"
              >
                <Save size={16} />
                Save details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EXECUTE WORKFLOW MODAL */}
      {executeOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onMouseDown={e => {
            if (e.target === e.currentTarget && !executing) {
              setExecuteOpen(false)
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="execute-workflow-title"
            className="bg-panel border border-border rounded-xl shadow-2xl w-full max-w-lg overflow-hidden"
          >
            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3
                  id="execute-workflow-title"
                  className="text-lg font-bold text-slate-900 dark:text-white"
                >
                  Execute workflow
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Submit a business instruction to the orchestrator.
                </p>
              </div>

              <button
                onClick={() => setExecuteOpen(false)}
                disabled={executing}
                aria-label="Close execution dialog"
                className="p-2 rounded-lg hover:bg-panelHover text-slate-500 disabled:opacity-50"
              >
                <X size={19} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="p-3 rounded-lg bg-accent/5 border border-accent/10">
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                  Selected workflow
                </p>
                <p className="font-semibold text-sm text-slate-900 dark:text-white">
                  {workflowName}
                </p>
                <code className="text-xs text-accent">
                  {WORKFLOW_KEY}
                </code>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-800 dark:text-slate-200 mb-2">
                  What would you like the workflow to do?
                </label>
                <textarea
                  value={request}
                  onChange={e => setRequest(e.target.value)}
                  rows={5}
                  maxLength={5000}
                  placeholder="Describe the business task..."
                  disabled={executing}
                  className="w-full bg-background border border-border rounded-lg px-3 py-3 text-sm text-slate-900 dark:text-white resize-none focus:outline-none focus:border-accent disabled:opacity-50"
                />
                <p className="text-xs text-slate-400 text-right mt-1">
                  {request.length}/5000
                </p>
              </div>

              <div className="flex items-start gap-2 text-xs text-slate-500 dark:text-slate-400">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <p>
                  The request will be submitted to your existing orchestrator API. Actual execution and approval requirements depend on backend configuration.
                </p>
              </div>
            </div>

            <div className="p-5 border-t border-border flex justify-end gap-2">
              <button
                onClick={() => setExecuteOpen(false)}
                disabled={executing}
                className="px-4 py-2.5 text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                onClick={handleExecute}
                disabled={executing || !request.trim()}
                className="px-4 py-2.5 bg-accent hover:bg-accentHover text-white rounded-lg text-sm font-semibold flex items-center gap-2 disabled:opacity-50"
              >
                {executing ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Start execution
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
