import { useState, useEffect } from 'react'
import {
  ShieldAlert, CheckCircle2, XCircle, ArrowUpRight,
  Clock, Bot, Activity, FileText, Check, Play,
  Mail, AlertTriangle, Tag, Target, TrendingUp, Loader2
} from 'lucide-react'

function classifyKind(proposed: any) {
  if (!proposed) return 'unknown'
  if (proposed.action_kind) return proposed.action_kind
  if (proposed.proposed_email) return 'send_email'
  if (proposed.proposed_order) return 'create_order'
  if (proposed.proposed_flag) return 'flag_customer'
  if (proposed.proposed_tasks) return 'create_tasks'
  return 'unknown'
}

function priorityColor(p: string | undefined) {
  if (!p) return 'bg-panelHover text-muted border-border'
  const lp = p.toLowerCase()
  if (lp === 'high' || lp === 'urgent') return 'bg-danger/10 text-danger border-danger/30'
  if (lp === 'medium' || lp === 'normal') return 'bg-warning/10 text-warning border-warning/30'
  return 'bg-success/10 text-success border-success/30'
}

function confidenceColor(c: number) {
  if (c >= 75) return 'text-success'
  if (c >= 50) return 'text-warning'
  return 'text-danger'
}

function ProposedActionView({ proposed }: { proposed: any }) {
  if (!proposed) return <p className="text-sm text-muted">No proposed action details.</p>
  const prepared = proposed.prepared_result || {}
  const proposedEmail = proposed.proposed_email || prepared.proposed_email || {}
  const classification = prepared.classification || {}
  const gaps = prepared.gaps || []
  const confidence = prepared.confidence
  const summary = prepared.summary
  const kind = classifyKind(proposed)

  const to = proposedEmail.to || proposed.to
  const subject = proposedEmail.subject || proposed.subject
  const body = proposedEmail.body || proposed.response_draft || prepared.response_draft

  return (
    <div className="space-y-4">
      {/* Summary */}
      {summary && (
        <div>
          <p className="text-xs uppercase text-muted mb-1">Summary</p>
          <p className="text-sm text-white">{summary}</p>
        </div>
      )}

      {/* Classification badges */}
      {(classification.category || classification.priority) && (
        <div className="flex flex-wrap gap-2">
          {classification.category && (
            <span className="text-xs px-2 py-1 rounded border bg-accent/10 text-accent border-accent/30 flex items-center gap-1">
              <Tag className="w-3 h-3" /> {classification.category}
            </span>
          )}
          {classification.priority && (
            <span className={`text-xs px-2 py-1 rounded border flex items-center gap-1 ${priorityColor(classification.priority)}`}>
              <AlertTriangle className="w-3 h-3" /> {classification.priority} priority
            </span>
          )}
          {typeof confidence === 'number' && (
            <span className={`text-xs px-2 py-1 rounded border bg-background border-border flex items-center gap-1 ${confidenceColor(confidence)}`}>
              <TrendingUp className="w-3 h-3" /> {confidence}% confidence
            </span>
          )}
        </div>
      )}

      {/* Proposed email */}
      {kind === 'send_email' && (
        <div className="bg-background border border-border rounded-lg overflow-hidden">
          <div className="px-3 py-2 border-b border-border bg-background flex items-center gap-2">
            <Mail className="w-4 h-4 text-accent" />
            <span className="text-xs font-semibold text-white uppercase tracking-wider">Email Draft</span>
          </div>
          <div className="p-3 space-y-2">
            {to && (
              <div className="flex gap-2 text-xs">
                <span className="text-muted w-16 shrink-0">To:</span>
                <span className="text-white font-mono break-all">{to}</span>
              </div>
            )}
            {subject && (
              <div className="flex gap-2 text-xs">
                <span className="text-muted w-16 shrink-0">Subject:</span>
                <span className="text-white">{subject}</span>
              </div>
            )}
            {proposed.thread_id && (
              <div className="flex gap-2 text-xs">
                <span className="text-muted w-16 shrink-0">Thread:</span>
                <span className="text-white font-mono">{proposed.thread_id}</span>
              </div>
            )}
            {body && (
              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted mb-1">Body:</p>
                <pre className="text-sm text-white whitespace-pre-wrap font-sans leading-relaxed max-h-64 overflow-y-auto">
{body}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Proposed tasks */}
      {(proposed.proposed_tasks || prepared.proposed_tasks) && (
        <div className="bg-background border border-border rounded-lg p-3">
          <p className="text-xs uppercase text-muted mb-2">Proposed Tasks</p>
          <ul className="space-y-1 text-sm text-white">
            {(proposed.proposed_tasks || prepared.proposed_tasks).map((t: any, i: number) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-accent mt-0.5">â€¢</span>
                <span>{typeof t === 'string' ? t : (t.title || t.subject || JSON.stringify(t))}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Gaps / warnings */}
      {gaps.length > 0 && (
        <div className="bg-warning/10 border border-warning/30 rounded-lg p-3">
          <p className="text-xs uppercase text-warning mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Gaps to review
          </p>
          <ul className="space-y-1 text-xs text-warning/90">
            {gaps.map((g: string, i: number) => <li key={i}>â€¢ {g}</li>)}
          </ul>
        </div>
      )}

      {/* Fallback JSON for unknown shapes */}
      {kind === 'unknown' && (
        <details>
          <summary className="text-xs text-accent cursor-pointer hover:underline">Raw proposed action</summary>
          <pre className="mt-2 p-3 bg-background border border-border rounded-lg text-xs text-muted overflow-x-auto">
{JSON.stringify(proposed, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}

export function MissionControl() {
  const [approvals, setApprovals] = useState<any[]>([])
  const [selected, setSelected] = useState<any | null>(null)
  const [detail, setDetail] = useState<any | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const token = () => localStorage.getItem('nexora_token')

  const fetchApprovals = async () => {
    try {
      const res = await fetch('/api/v1/approvals?status=pending', {
        headers: { Authorization: 'Bearer ' + token() },
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

  // Fetch detail whenever selection changes
  useEffect(() => {
    if (!selected?.id) { setDetail(null); return }
    let cancelled = false
    async function fetchDetail() {
      setDetailLoading(true)
      try {
        const res = await fetch(`/api/v1/approvals/${selected!.id}`, {
          headers: { Authorization: 'Bearer ' + token() },
        })
        if (!cancelled && res.ok) setDetail(await res.json())
      } catch (err) {
        console.error(err)
      } finally {
        if (!cancelled) setDetailLoading(false)
      }
    }
    fetchDetail()
    return () => { cancelled = true }
  }, [selected?.id])

  const handleAction = async (action: 'approve' | 'reject') => {
    if (!selected) return
    setActionLoading(true)
    try {
      const res = await fetch(`/api/v1/approvals/${selected.id}/${action}`, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ note: action === 'reject' ? 'Operator rejected via Mission Control' : 'Approved via Mission Control' }),
      })
      if (!res.ok) throw new Error('Action failed')
      setToast(`Successfully ${action}d the action.`)
      setTimeout(() => setToast(null), 3000)
      setSelected(null)
      fetchApprovals()
    } catch (err: any) {
      setToast(`Error: ${err.message}`)
      setTimeout(() => setToast(null), 3000)
    } finally {
      setActionLoading(false)
    }
  }

  const proposed = detail?.proposed_action || null

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col bg-background">
      <div className="mb-6 shrink-0">
        <h1 className="text-2xl font-bold text-white mb-1">Agent Mission Control</h1>
        <p className="text-sm text-muted">Run, govern, replay, and audit AI agents like a real product team.</p>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Left: Pending Approvals */}
        <div className="w-80 shrink-0 bg-background border border-border rounded-xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-background flex items-center justify-between">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Pending Approvals</span>
            <span className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded font-semibold">{approvals.length}</span>
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
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-white">#{a.id.slice(0, 8)}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-warning/10 text-warning border border-warning/20">pending</span>
                  </div>
                  <p className="text-xs text-gray-300 line-clamp-2">{a.reason}</p>
                  <p className="text-[10px] text-muted mt-1 capitalize">{a.agent_type} agent</p>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Center: Operator Brief */}
        <div className="flex-1 flex flex-col min-w-0 bg-background border border-border rounded-xl overflow-hidden">
          {selected ? (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-bold text-white mb-1">Operator Brief</h2>
                  <p className="text-sm text-muted">Approval #{selected.id.slice(0, 8)}</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg">
                  <Clock className="w-4 h-4 text-muted" />
                  <span className="text-xs text-muted">{new Date(selected.created_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Recommended Next Step */}
              <div className="bg-accent/5 border border-accent/20 rounded-xl p-4">
                <p className="text-xs font-semibold text-accent uppercase tracking-wider mb-1">Recommended Next Step</p>
                <p className="text-sm text-white">Review the proposed action and approve if it aligns with policy.</p>
                <div className="flex gap-4 mt-2 text-xs text-muted">
                  <span>Risk: <span className="text-warning">Low</span></span>
                  <span>Policy: <span className="text-success">Validated</span></span>
                </div>
              </div>

              {/* What Happened */}
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">What Happened</h3>
                <div className="bg-background border border-border rounded-xl p-5">
                  <p className="text-sm text-white mb-3">{selected.task_description}</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-[10px] text-muted uppercase mb-1">Status</p>
                      <p className="text-sm font-medium text-warning">Pending</p>
                    </div>
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-[10px] text-muted uppercase mb-1">Agent</p>
                      <p className="text-sm font-medium text-white capitalize">{selected.agent_type}</p>
                    </div>
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-[10px] text-muted uppercase mb-1">Reason</p>
                      <p className="text-sm font-medium text-white truncate" title={selected.reason}>{selected.reason}</p>
                    </div>
                  {selected.decided_reason && (
                    <div className="bg-background p-3 rounded-lg border border-border">
                      <p className="text-[10px] text-muted uppercase mb-1">Decision Reason</p>
                      <p className="text-sm font-medium text-white">{selected.decided_reason}</p>
                    </div>
                  )}
                  </div>
                </div>
              </div>

              {/* Proposed Action */}
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">Proposed Action</h3>
                <div className="bg-background border border-border rounded-xl p-5">
                  {detailLoading ? (
                    <div className="flex items-center gap-2 text-sm text-muted">
                      <Loader2 className="w-4 h-4 animate-spin" /> Loading details...
                    </div>
                  ) : (
                    <ProposedActionView proposed={proposed} />
                  )}
                </div>
              </div>

              {/* Execution Timeline */}
              <div>
                <h3 className="text-sm font-semibold text-white mb-3">Execution Timeline</h3>
                <div className="bg-background border border-border rounded-xl p-5">
                  <div className="relative border-l border-border ml-3 space-y-6 pb-2">
                    <div className="relative pl-6">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-success" />
                      <p className="text-xs text-muted mb-1">Step 1 Â· Task Assigned</p>
                      <p className="text-sm text-white">{selected.task_description}</p>
                      <p className="text-xs text-muted mt-1">Task #{selected.task_id} Â· {selected.agent_type} agent</p>
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-success" />
                      <p className="text-xs text-muted mb-1">Step 2 Â· Draft Prepared</p>
                      <p className="text-sm text-white">{selected.agent_type} agent prepared the action</p>
                      <p className="text-xs text-muted mt-1">Requested {new Date(selected.created_at).toLocaleString()}</p>
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-warning" />
                      <p className="text-xs text-muted mb-1">Step 3 Â· Policy Gate</p>
                      <p className="text-sm text-white">Awaiting human approval</p>
                      <p className="text-xs text-muted mt-1">{selected.reason}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted flex-col">
              <ShieldAlert className="w-10 h-10 mb-2 opacity-40" />
              <p className="text-sm">No pending action selected</p>
              <p className="text-xs mt-2 opacity-70">Choose an item from the left to review</p>
            </div>
          )}
        </div>

        {/* Right: Action Console */}
        <div className="w-72 shrink-0 bg-background border border-border rounded-xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-background">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Action Console</span>
          </div>
          <div className="p-4 flex-1">
            {selected ? (
              <div className="space-y-3">
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Final Decision</p>
                  <p className="text-sm font-semibold text-warning">Pending</p>
                </div>
                <p className="text-xs text-muted">
                  Review the proposed action and approve, reject, or request changes.
                </p>
                <div className="space-y-2 pt-2">
                  <button
                    onClick={() => handleAction('approve')}
                    disabled={actionLoading}
                    className="w-full bg-success text-white py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    Approve
                  </button>
                  <button
                    onClick={() => handleAction('reject')}
                    disabled={actionLoading}
                    className="w-full bg-danger/10 text-danger border border-danger/30 py-2 rounded-lg text-sm font-medium hover:bg-danger/20 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted text-center py-6">Select an approval to act on</p>
            )}
          </div>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-background border border-border rounded-lg px-4 py-3 shadow-lg z-50 text-sm text-white">
          {toast}
        </div>
      )}
    </div>
  )
}
