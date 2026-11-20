import { useState, useEffect } from 'react'
import { 
  ShieldAlert, CheckCircle2, XCircle, ArrowUpRight, 
  Clock, Bot, Activity, FileText, Check, Play
} from 'lucide-react'

export function MissionControl() {
  const [approvals, setApprovals] = useState<any[]>([])
  const [selected, setSelected] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const fetchApprovals = async () => {
    try {
      const token = localStorage.getItem('nexora_token')
      const res = await fetch('/api/v1/approvals?status=pending', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await res.json()
      const arr = Array.isArray(data) ? data : []
      setApprovals(arr)
      if (arr.length > 0 && !selected) setSelected(arr[0])
      if (arr.length === 0) setSelected(null)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchApprovals() }, [])

  const handleAction = async (action: 'approve' | 'reject') => {
    if (!selected) return
    setActionLoading(true)
    try {
      const token = localStorage.getItem('nexora_token')
      const res = await fetch(`/api/v1/approvals/${selected.id}/${action}`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: action === 'reject' ? 'Operator rejected via Mission Control' : undefined })
      })
      if (!res.ok) throw new Error('Action failed')
      
      setToast(`Successfully ${action}d the action.`)
      setTimeout(() => setToast(null), 3000)
      setSelected(null)
      fetchApprovals() // Refresh list
    } catch (err: any) {
      setToast(`Error: ${err.message}`)
      setTimeout(() => setToast(null), 3000)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-[#0B0F19] overflow-hidden">
      
      {/* Top Banner */}
      <div className="bg-[#111827] border-b border-border p-6 flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Agent Mission Control</h1>
          <p className="text-sm text-muted">Run, govern, replay, and audit AI agents like a real product team.</p>
        </div>
        <div className="flex items-center gap-4 bg-background border border-border px-4 py-2 rounded-lg">
          <span className="text-xs text-muted uppercase tracking-wider">Active Runs</span>
          <span className="text-xl font-bold text-white">{approvals.length}</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Pending List */}
        <div className="w-80 border-r border-border bg-[#0B0F19] flex flex-col">
          <div className="p-3 border-b border-border bg-[#111827] flex justify-between items-center">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Pending Approvals</span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {loading ? (
              <div className="p-4 text-center text-muted text-sm">Loading...</div>
            ) : approvals.length === 0 ? (
              <div className="p-4 text-center text-muted text-sm">No pending approvals</div>
            ) : (
              approvals.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setSelected(a)}
                  className={`w-full text-left p-3 rounded-lg transition-colors border ${
                    selected?.id === a.id ? 'bg-accent/10 border-accent/30' : 'border-transparent hover:bg-panelHover'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-mono text-muted">#{a.id.split('-')[0]}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-warning/10 text-warning border border-warning/20 uppercase">Pending</span>
                  </div>
                  <p className="text-sm font-medium text-white truncate">{a.reason}</p>
                  <p className="text-xs text-muted mt-1">{a.agent_type} agent</p>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Center: Operator Brief */}
        <div className="flex-1 flex flex-col min-w-0">
          {selected ? (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-bold text-white mb-1">Operator Brief</h2>
                  <p className="text-sm text-muted">Run #{selected.id.split('-')[0]}</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg">
                  <Clock className="w-4 h-4 text-muted" />
                  <span className="text-xs text-muted">Awaiting review</span>
                </div>
              </div>

              {/* Recommended Next Step */}
              <div className="bg-[#111827] border border-border rounded-xl p-5 border-l-4 border-l-accent">
                <h3 className="text-sm font-semibold text-white mb-2">Recommended Next Step</h3>
                <p className="text-sm text-muted mb-3">Review the timeline and approve if the action aligns with business policy.</p>
                <div className="flex gap-4 text-xs">
                  <span className="text-muted">Risk: <strong className="text-success">Low</strong></span>
                  <span className="text-muted">Policy: <strong className="text-success">Validated</strong></span>
                </div>
              </div>

              {/* What Happened */}
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">What Happened</h3>
                <div className="bg-[#111827] border border-border rounded-xl p-5">
                  <p className="text-sm text-white mb-4">{selected.task_description || "Action paused for human approval."}</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-xs text-muted mb-1">Status</p>
                      <p className="text-sm font-medium text-warning">Paused</p>
                    </div>
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-xs text-muted mb-1">Agent</p>
                      <p className="text-sm font-medium text-white capitalize">{selected.agent_type}</p>
                    </div>
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-xs text-muted mb-1">Reason</p>
                      <p className="text-sm font-medium text-white truncate">{selected.reason}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Execution Timeline */}
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">Execution Timeline</h3>
                <div className="bg-[#111827] border border-border rounded-xl p-5">
                  <div className="relative border-l border-border ml-3 space-y-6 pb-2">
                    <div className="relative pl-6">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-success" />
                      <p className="text-xs text-muted mb-1">Step 1 | Input</p>
                      <p className="text-sm text-white">Customer escalation received</p>
                      <p className="text-xs text-muted mt-1">User requested a summarized response after internal review.</p>
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-success" />
                      <p className="text-xs text-muted mb-1">Step 2 | Agent Action</p>
                      <p className="text-sm text-white">{selected.agent_type} agent drafted the action</p>
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-warning" />
                      <p className="text-xs text-muted mb-1">Step 3 | Policy Gate</p>
                      <p className="text-sm text-white">Action paused for approval</p>
                      <p className="text-xs text-muted mt-1">{selected.reason}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted">
              <ShieldAlert className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-sm">No pending action selected</p>
              <p className="text-xs mt-2 opacity-70">Choose an item from the left to review</p>
            </div>
          )}
        </div>

        {/* Right Panel: Action Console */}
        <div className="w-80 border-l border-border bg-[#111827] flex flex-col">
          <div className="p-4 border-b border-border">
            <h3 className="text-sm font-semibold text-white">Action Console</h3>
            <p className="text-xs text-muted mt-1">Final decision required</p>
          </div>
          
          <div className="flex-1 p-4 space-y-4">
            <div className="bg-[#0B0F19] border border-border rounded-xl p-4">
              <p className="text-xs text-muted uppercase tracking-wider mb-2">Current Decision</p>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-white">No action required</span>
                <span className="text-xs px-2 py-0.5 rounded bg-warning/10 text-warning border border-warning/20">Paused</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                Review the timeline only if you need context or want to compare it against a stricter policy.
              </p>
            </div>

            {selected && (
              <div className="space-y-2">
                <button 
                  onClick={() => handleAction('approve')} 
                  disabled={actionLoading}
                  className="w-full py-2.5 bg-success text-white font-medium rounded-lg hover:bg-success/90 transition-colors flex justify-center items-center gap-2"
                >
                  <CheckCircle2 className="w-4 h-4" /> Approve
                </button>
                <button 
                  onClick={() => handleAction('reject')} 
                  disabled={actionLoading}
                  className="w-full py-2.5 bg-danger text-white font-medium rounded-lg hover:bg-danger/90 transition-colors flex justify-center items-center gap-2"
                >
                  <XCircle className="w-4 h-4" /> Reject
                </button>
                <button className="w-full py-2.5 bg-background border border-border text-white font-medium rounded-lg hover:bg-panelHover transition-colors flex justify-center items-center gap-2">
                  <ArrowUpRight className="w-4 h-4" /> Escalate
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-panel border border-border text-white px-4 py-3 rounded-lg shadow-2xl flex items-center gap-2">
          <Check className="w-4 h-4 text-success" /> {toast}
        </div>
      )}
    </div>
  )
}
