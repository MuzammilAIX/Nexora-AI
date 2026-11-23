import { useState, useEffect, useMemo } from 'react'
import { CheckCircle2, XCircle, Clock, Loader2, Search, ChevronRight, AlertCircle } from 'lucide-react'

interface Run {
  id: string
  user_request: string
  status: string
  created_at: string
  completed_at?: string | null
}

interface TaskResult {
  task_id: string
  agent_type: string
  status: string
  result?: any
  approval_id?: string
  reason?: string
}

interface PlannedTask {
  task_id: string
  description: string
  agent_type: string
  dependencies?: string[]
  requires_approval?: boolean
  approval_reason?: string | null
}

interface RunDetail {
  id: string
  user_request: string
  status: string
  created_at: string
  completed_at: string | null
  state: {
    analysis?: { intent?: string; goal?: string; requirements?: string[]; constraints?: string[] }
    tasks?: PlannedTask[]
    task_results?: TaskResult[]
    execution_notes?: string[]
    status?: string
    error?: string
  } | null
}

function statusIcon(status: string) {
  const s = status?.toLowerCase() || ''
  if (s === 'completed' || s === 'done' || s === 'executed' || s === 'success') {
    return <CheckCircle2 className="w-4 h-4 text-success" />
  }
  if (s === 'failed' || s === 'error') {
    return <XCircle className="w-4 h-4 text-danger" />
  }
  if (s === 'pending_approval' || s === 'paused' || s === 'awaiting_approval') {
    return <Clock className="w-4 h-4 text-warning" />
  }
  if (s === 'running' || s === 'in_progress') {
    return <Loader2 className="w-4 h-4 text-accent animate-spin" />
  }
  return <AlertCircle className="w-4 h-4 text-muted" />
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    completed: 'Completed', done: 'Completed', executed: 'Executed', success: 'Success',
    failed: 'Failed', error: 'Error',
    pending_approval: 'Awaiting Approval', paused: 'Paused', awaiting_approval: 'Awaiting Approval',
    running: 'Running', in_progress: 'In Progress',
  }
  return map[(status || '').toLowerCase()] || status || 'Unknown'
}

function statusBadgeClass(status: string) {
  const s = (status || '').toLowerCase()
  if (['completed', 'done', 'executed', 'success'].includes(s)) return 'bg-success/10 text-success border-success/20'
  if (['failed', 'error'].includes(s)) return 'bg-danger/10 text-danger border-danger/20'
  if (['pending_approval', 'paused', 'awaiting_approval'].includes(s)) return 'bg-warning/10 text-warning border-warning/20'
  if (['running', 'in_progress'].includes(s)) return 'bg-accent/10 text-accent border-accent/20'
  return 'bg-panelHover text-muted border-border'
}

function duration(run: Run) {
  if (!run.completed_at) return '—'
  const ms = new Date(run.completed_at).getTime() - new Date(run.created_at).getTime()
  if (ms < 0 || isNaN(ms)) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
}

export function Executions() {
  const [runs, setRuns] = useState<Run[]>([])
  const [selectedRun, setSelectedRun] = useState<Run | null>(null)
  const [trace, setTrace] = useState<RunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [traceLoading, setTraceLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const token = () => localStorage.getItem('nexora_token')
  const headers = () => ({ Authorization: 'Bearer ' + token() })

  useEffect(() => {
    async function fetchRuns() {
      try {
        const res = await fetch('/api/v1/orchestrator/runs', { headers: headers() })
        if (!res.ok) throw new Error('Failed to load runs')
        const data = await res.json()
        setRuns(Array.isArray(data) ? data : (data.runs || []))
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchRuns()
  }, [])

  const filtered = useMemo(() => {
    return runs.filter((r) => {
      const matchStatus = statusFilter === 'all' || (r.status || '').toLowerCase() === statusFilter
      const q = search.toLowerCase().trim()
      const matchSearch = !q || (r.id || '').toLowerCase().includes(q) || (r.user_request || '').toLowerCase().includes(q)
      return matchStatus && matchSearch
    })
  }, [runs, search, statusFilter])

  async function handleSelectRun(run: Run) {
    setSelectedRun(run)
    setTrace(null)
    setTraceLoading(true)
    try {
      const res = await fetch(`/api/v1/orchestrator/runs/${run.id}`, { headers: headers() })
      if (!res.ok) throw new Error('Failed to load trace')
      const data = await res.json()
      setTrace(data)
    } catch (err) {
      console.error(err)
    } finally {
      setTraceLoading(false)
    }
  }

  // Join tasks with results by task_id
  const joinedTasks = useMemo(() => {
    if (!trace?.state) return []
    const planned = trace.state.tasks || []
    const results = trace.state.task_results || []
    return planned.map((p) => {
      const r = results.find((x) => x.task_id === p.task_id)
      return { plan: p, result: r }
    })
  }, [trace])

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col bg-background">
      <div className="mb-6 shrink-0">
        <h2 className="text-2xl font-bold text-white mb-1">Executions</h2>
        <p className="text-sm text-muted">Step-by-step agent traces from the orchestrator</p>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Left: run list */}
        <div className="w-2/5 bg-background border border-border rounded-xl flex flex-col overflow-hidden">
          <div className="p-3 border-b border-border bg-background space-y-2">
            <div className="relative">
              <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search runs by ID or request..."
                className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50"
              />
            </div>
            <div className="flex gap-1 text-xs">
              {['all', 'completed', 'pending_approval', 'failed'].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-2 py-1 rounded transition-colors ${
                    statusFilter === s ? 'bg-accent text-white' : 'text-muted hover:bg-panelHover'
                  }`}
                >
                  {s === 'all' ? 'All' : statusLabel(s)}
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 space-y-3">
                {[1,2,3].map(i => (
                  <div key={i} className="animate-pulse">
                    <div className="h-3 bg-border rounded w-1/3 mb-2"></div>
                    <div className="h-3 bg-border rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-border rounded w-1/2"></div>
                  </div>
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="p-6 text-center text-muted text-sm">
                {runs.length === 0 ? 'No runs yet. Try the AI Assistant or Test Agent.' : 'No runs match your filter.'}
              </div>
            ) : (
              filtered.map((run) => (
                <button
                  key={run.id}
                  onClick={() => handleSelectRun(run)}
                  className={`w-full text-left p-4 border-b border-border transition-colors ${
                    selectedRun?.id === run.id ? 'bg-accent/10' : 'hover:bg-panelHover'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-mono text-white">#{run.id.slice(0, 8)}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border ${statusBadgeClass(run.status)}`}>
                      {statusLabel(run.status)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-300 truncate mb-1">{run.user_request}</div>
                  <div className="flex items-center justify-between text-[11px] text-muted">
                    <span>{new Date(run.created_at).toLocaleString()}</span>
                    <span>{duration(run)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right: trace detail */}
        <div className="flex-1 bg-background border border-border rounded-xl overflow-y-auto">
          {!selectedRun ? (
            <div className="h-full flex items-center justify-center text-muted text-sm">
              <div className="text-center">
                <ChevronRight className="w-8 h-8 mx-auto mb-2 opacity-30" />
                Select a run to view its agent trace
              </div>
            </div>
          ) : traceLoading ? (
            <div className="p-8 text-center text-muted text-sm">
              <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
              Loading trace...
            </div>
          ) : !trace?.state ? (
            <div className="p-8 text-center text-muted text-sm">No state data for this run.</div>
          ) : (
            <div className="p-6 space-y-5">
              {/* Header */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-lg font-semibold text-white">Run #{selectedRun.id.slice(0, 8)}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded border ${statusBadgeClass(trace.status)}`}>
                    {statusLabel(trace.status)}
                  </span>
                </div>
                <p className="text-sm text-gray-300 mb-1">{trace.user_request}</p>
                <p className="text-xs text-muted">
                  Started {new Date(trace.created_at).toLocaleString()}
                  {trace.completed_at && ` · Duration ${duration(trace as any)}`}
                </p>
              </div>

              {/* Analysis */}
              {trace.state.analysis && (
                <div className="bg-background border border-border rounded-lg p-4">
                  <h4 className="text-xs uppercase text-muted mb-2">Analysis</h4>
                  {trace.state.analysis.intent && (
                    <p className="text-sm text-white mb-1"><span className="text-muted">Intent: </span>{trace.state.analysis.intent}</p>
                  )}
                  {trace.state.analysis.goal && (
                    <p className="text-sm text-gray-300 mb-2"><span className="text-muted">Goal: </span>{trace.state.analysis.goal}</p>
                  )}
                  {trace.state.analysis.requirements && trace.state.analysis.requirements.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-muted mb-1">Requirements:</p>
                      <ul className="text-xs text-gray-300 list-disc list-inside space-y-0.5">
                        {trace.state.analysis.requirements.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Task Timeline */}
              <div>
                <h4 className="text-xs uppercase text-muted mb-3">Task Timeline</h4>
                <div className="space-y-3">
                  {joinedTasks.length === 0 ? (
                    <div className="text-sm text-muted">No tasks in this run.</div>
                  ) : joinedTasks.map((item, i) => {
                    const { plan, result } = item
                    const status = result?.status || (plan.requires_approval ? 'pending_approval' : 'not_started')
                    return (
                      <div key={plan.task_id || i} className="flex gap-3">
                        <div className="flex flex-col items-center pt-0.5">
                          {statusIcon(status)}
                          {i < joinedTasks.length - 1 && <div className="w-px flex-1 bg-border my-1 min-h-[20px]" />}
                        </div>
                        <div className="flex-1 pb-4">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-xs font-mono text-muted">#{plan.task_id}</span>
                            <span className="text-sm font-medium text-white">{plan.agent_type}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${statusBadgeClass(status)}`}>
                              {statusLabel(status)}
                            </span>
                          </div>
                          <p className="text-xs text-gray-300 mb-2">{plan.description}</p>

                          {result?.reason && (
                            <div className="bg-warning/10 border border-warning/30 rounded p-2 text-xs text-warning mb-2">
                              {result.reason}
                            </div>
                          )}

                          {result?.approval_id && (
                            <div className="text-xs text-muted mb-2 font-mono">
                              Approval: {result.approval_id.slice(0, 8)}...
                            </div>
                          )}

                          {result?.result && (
                            <details className="mt-2">
                              <summary className="text-xs text-accent cursor-pointer hover:underline">
                                View result
                              </summary>
                              <pre className="mt-2 p-3 bg-background border border-border rounded-lg text-xs text-gray-300 overflow-x-auto max-h-64">
{JSON.stringify(result.result, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Execution notes */}
              {trace.state.execution_notes && trace.state.execution_notes.length > 0 && (
                <div className="bg-background border border-border rounded-lg p-4">
                  <h4 className="text-xs uppercase text-muted mb-2">Execution Notes</h4>
                  <ul className="text-xs text-gray-300 list-disc list-inside space-y-1">
                    {trace.state.execution_notes.map((n, i) => <li key={i}>{n}</li>)}
                  </ul>
                </div>
              )}

              {/* Error */}
              {trace.state.error && (
                <div className="bg-danger/10 border border-danger/30 rounded-lg p-3 text-sm text-danger">
                  {trace.state.error}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}