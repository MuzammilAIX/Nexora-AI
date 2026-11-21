import { useState, useEffect } from 'react'
import { Activity, CheckCircle2, XCircle, Clock, Cpu } from 'lucide-react'

export function Executions() {
  const [runs, setRuns] = useState<any[]>([])
  const [selectedRun, setSelectedRun] = useState<any | null>(null)
  const [trace, setTrace] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [traceLoading, setTraceLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    async function fetchRuns() {
      try {
        const token = localStorage.getItem('nexora_token')
        const res = await fetch('/api/v1/orchestrator/runs', {
          headers: { 'Authorization': 'Bearer ' + token }
        })
        const data = await res.json()
        setRuns(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchRuns()
  }, [])

  const handleSelectRun = async (run: any) => {
    setSelectedRun(run)
    setTraceLoading(true)
    try {
      const token = localStorage.getItem('nexora_token')
      const res = await fetch(`/api/v1/orchestrator/runs/${run.id}`, {
        headers: { 'Authorization': 'Bearer ' + token }
      })
      const data = await res.json()
      setTrace(data)
    } catch (err) {
      console.error(err)
    } finally {
      setTraceLoading(false)
    }
  }

  const filteredRuns = runs.filter(r => {
    const req = r.state_json?.user_request || r.user_request || ''
    return req.toLowerCase().includes(search.toLowerCase()) || r.id.includes(search)
  })

  // Safely extract state to handle different backend response shapes
  const state = trace?.state_json || trace?.state || trace || {}
  
  // If tasks aren't in state, but task_results has the agents, we can synthesize tasks
  let tasks = state.tasks || []
  const results = state.task_results || []
  
  if (tasks.length === 0 && results.length > 0) {
    tasks = results.map((r: any) => ({
      task_id: r.task_id,
      agent_type: r.agent_type,
      description: r.description || `Execute ${r.agent_type} task`,
      requires_approval: r.status === 'pending_approval'
    }))
  }

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col bg-background">
      <div className="mb-6 shrink-0">
        <h2 className="text-2xl font-bold text-white mb-1">Executions</h2>
        <p className="text-sm text-muted">Step-by-step agent traces</p>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Left List */}
        <div className="w-1/3 bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
          <div className="p-3 border-b border-border bg-[#111827]">
            <input 
              type="text" 
              placeholder="Search runs..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50" 
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-muted text-sm">Loading runs...</div>
            ) : filteredRuns.length === 0 ? (
              <div className="p-4 text-center text-muted text-sm">No runs found.</div>
            ) : (
              filteredRuns.map((run) => (
                <button
                  key={run.id}
                  onClick={() => handleSelectRun(run)}
                  className={`w-full text-left p-4 border-b border-border transition-colors ${selectedRun?.id === run.id ? 'bg-accent/10' : 'hover:bg-panelHover'}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-muted">#{run.id.slice(0, 8)}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase ${run.status === 'completed' ? 'bg-success/10 text-success' : run.status === 'pending_approval' ? 'bg-warning/10 text-warning' : 'bg-danger/10 text-danger'}`}>
                      {run.status}
                    </span>
                  </div>
                  <p className="text-sm text-white truncate">{run.state_json?.user_request || run.user_request || 'Unknown request'}</p>
                  <p className="text-xs text-muted mt-1">{new Date(run.created_at).toLocaleString()}</p>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Trace */}
        <div className="flex-1 bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
          {selectedRun ? (
            traceLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted">
                <Clock className="w-8 h-8 mb-4 animate-spin opacity-50" />
                <p>Loading trace...</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">Execution Trace #{selectedRun.id.slice(0, 8)}</h3>
                    <p className="text-sm text-muted">{selectedRun.state_json?.user_request || selectedRun.user_request || 'Unknown request'}</p>
                  </div>
                  <div className="flex gap-4">
                    <div><p className="text-xs text-muted">Status</p><p className="text-sm font-medium text-white capitalize">{selectedRun.status}</p></div>
                    <div><p className="text-xs text-muted">Started</p><p className="text-sm font-medium text-white">{new Date(selectedRun.created_at).toLocaleTimeString()}</p></div>
                  </div>
                </div>

                {/* Timeline */}
                <div>
                  <h4 className="text-sm font-semibold text-white mb-4">Agent Timeline</h4>
                  <div className="space-y-4">
                    {/* Intake */}
                    <div className="flex gap-4">
                      <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0"><Cpu className="w-4 h-4 text-blue-400" /></div>
                      <div className="flex-1 bg-[#111827] border border-border rounded-lg p-3">
                        <div className="flex justify-between"><span className="text-sm font-medium text-white">Intake & Classification</span><span className="text-xs text-muted">system</span></div>
                        <p className="text-xs text-muted mt-1">Parsed user request and prepared orchestrator state.</p>
                      </div>
                    </div>

                    {/* Tasks */}
                    {tasks.length === 0 && <p className="text-sm text-muted italic ml-12">No task details recorded for this run.</p>}
                    {tasks.map((task: any, i: number) => {
                      const result = results.find((r: any) => r.task_id === task.task_id) || {};
                      const isDone = result.status === 'completed' || result.status === 'done';
                      const isFailed = result.status === 'failed';
                      return (
                        <div key={i} className="flex gap-4">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${isFailed ? 'bg-danger/20' : isDone ? 'bg-success/20' : 'bg-warning/20'}`}>
                            {isFailed ? <XCircle className="w-4 h-4 text-danger" /> : isDone ? <CheckCircle2 className="w-4 h-4 text-success" /> : <Clock className="w-4 h-4 text-warning" />}
                          </div>
                          <div className="flex-1 bg-[#111827] border border-border rounded-lg p-3">
                            <div className="flex justify-between">
                              <span className="text-sm font-medium text-white capitalize">{task.agent_type} Agent</span>
                              <span className={`text-xs capitalize ${isFailed ? 'text-danger' : isDone ? 'text-success' : 'text-warning'}`}>{result.status || 'pending'}</span>
                            </div>
                            <p className="text-xs text-muted mt-1">{task.description}</p>
                            {result.error && <div className="mt-2 text-xs text-danger bg-danger/10 p-2 rounded border border-danger/20 font-mono whitespace-pre-wrap">{result.error}</div>}
                            {result.result && (
                              <details className="mt-2">
                                <summary className="text-xs text-accent cursor-pointer hover:text-accent/80">View Output</summary>
                                <pre className="mt-1 text-[10px] text-gray-400 bg-background p-3 rounded-lg overflow-x-auto border border-border">{JSON.stringify(result.result, null, 2)}</pre>
                              </details>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted">
              <Activity className="w-12 h-12 mb-4 opacity-50" />
              <p>Select an execution to view the trace</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
