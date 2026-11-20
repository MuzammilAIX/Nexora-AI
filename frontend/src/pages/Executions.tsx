import { useState, useEffect } from 'react'
import { Activity, CheckCircle2, XCircle, Clock, Play, Code2, Search } from 'lucide-react'

export function Executions() {
  const [runs, setRuns] = useState<any[]>([])
  const [selectedRun, setSelectedRun] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchRuns() {
      try {
        const token = localStorage.getItem('nexora_token')
        const res = await fetch('/api/v1/orchestrator/runs', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await res.json()
        const runsArray = Array.isArray(data) ? data : []
        setRuns(runsArray)
        if (runsArray.length > 0) setSelectedRun(runsArray[0])
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchRuns()
  }, [])

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">Executions</h2>
          <p className="text-sm text-muted">Step-by-step agent traces</p>
        </div>
      </div>

      <div className="flex-1 flex gap-6 min-h-0">
        <div className="w-80 bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border bg-panelHover/50">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input type="text" placeholder="Search runs..." className="w-full bg-background border border-border rounded-lg pl-9 pr-4 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loading ? (
              <div className="p-4 text-center text-muted text-sm">Loading...</div>
            ) : runs.length === 0 ? (
              <div className="p-4 text-center text-muted text-sm">No runs found.</div>
            ) : (
              runs.map((run) => (
                <button
                  key={run.id}
                  onClick={() => setSelectedRun(run)}
                  className={`w-full text-left p-3 rounded-lg transition-colors border ${selectedRun?.id === run.id ? 'bg-accent/10 border-accent/30' : 'border-transparent hover:bg-panelHover'}`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-mono text-muted">#{run.id.split('-')[0]}</span>
                    <StatusBadge status={run.status} />
                  </div>
                  <p className="text-sm text-white truncate mb-1">{run.user_request}</p>
                  <p className="text-xs text-muted">{new Date(run.created_at).toLocaleString()}</p>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="flex-1 bg-panel border border-border rounded-xl flex flex-col overflow-hidden">
          {selectedRun ? (
            <>
              <div className="p-5 border-b border-border flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">
                    Execution Trace <span className="text-muted text-sm font-mono ml-2">#{selectedRun.id.split('-')[0]}</span>
                  </h3>
                  <p className="text-sm text-muted">{selectedRun.user_request}</p>
                </div>
                <div className="flex gap-4 text-center">
                  <div>
                    <p className="text-xs text-muted uppercase tracking-wider mb-1">Status</p>
                    <StatusBadge status={selectedRun.status} />
                  </div>
                  <div>
                    <p className="text-xs text-muted uppercase tracking-wider mb-1">Started</p>
                    <p className="text-sm text-white">{new Date(selectedRun.created_at).toLocaleTimeString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted uppercase tracking-wider mb-1">Completed</p>
                    <p className="text-sm text-white">{selectedRun.completed_at ? new Date(selectedRun.completed_at).toLocaleTimeString() : 'Running...'}</p>
                  </div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-6">
                <TraceTimeline run={selectedRun} />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted">Select a run to view details</div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  let color = 'text-muted bg-muted/10 border-muted/20'
  let label = status
  if (status === 'completed') { color = 'text-success bg-success/10 border-success/20'; label = 'Completed' }
  else if (status === 'failed') { color = 'text-danger bg-danger/10 border-danger/20'; label = 'Failed' }
  else if (status === 'pending_approval') { color = 'text-warning bg-warning/10 border-warning/20'; label = 'Pending Approval' }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${color}`}>{label}</span>
}

function TraceTimeline({ run }: { run: any }) {
  const steps = [
    { name: 'Intake & Classification', type: 'system', status: 'success', duration: '120ms', icon: Play },
    { name: 'Planner Agent', type: 'agent', status: 'success', duration: '2.4s', icon: Activity, details: 'Decomposed goal into 3 tasks' },
    { name: 'Tool: Search CRM', type: 'tool', status: run.status === 'failed' ? 'error' : 'success', duration: '840ms', icon: Code2, details: 'Retrieved 5 leads' },
    { name: 'Writer Agent', type: 'agent', status: run.status === 'pending_approval' ? 'warning' : (run.status === 'failed' ? 'error' : 'success'), duration: '-', icon: Activity, details: 'Drafted follow-up emails' },
  ]

  return (
    <div className="space-y-6">
      <div className="relative border-l border-border ml-3 space-y-8 pb-8">
        {steps.map((step, idx) => (
          <div key={idx} className="relative pl-8">
            <div className={`absolute -left-3 top-1 w-6 h-6 rounded-full border-2 bg-panel flex items-center justify-center ${step.status === 'success' ? 'border-success text-success' : step.status === 'warning' ? 'border-warning text-warning' : step.status === 'error' ? 'border-danger text-danger' : 'border-border text-muted'}`}>
              {step.status === 'success' ? <CheckCircle2 className="w-3 h-3" /> : step.status === 'error' ? <XCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
            </div>
            <div className="bg-background border border-border rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <step.icon className="w-4 h-4 text-muted" />
                  <span className="text-sm font-medium text-white">{step.name}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-panelHover text-muted uppercase tracking-wider">{step.type}</span>
                </div>
                <span className="text-xs text-muted font-mono">{step.duration}</span>
              </div>
              {step.details && <p className="text-sm text-gray-400 mt-2">{step.details}</p>}
              {idx === 2 && (
                <div className="mt-3 bg-panel p-3 rounded border border-border font-mono text-xs text-gray-400 overflow-x-auto">
                  <div className="text-muted mb-1">{'// Request Payload'}</div>
                  {'{ "query": "high value leads", "limit": 5 }'}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
