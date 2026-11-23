import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  CheckCircle2, XCircle, Clock, Loader2, Search, RefreshCw,
  Download, ShieldCheck, AlertTriangle, X, Check, Eye, Bot
} from 'lucide-react'
import { ProposedActionView } from '../components/ProposedActionView'

interface Approval {
  id: string
  task_id: string
  agent_type: string
  status: string
  reason: string
  task_description: string
  created_at: string
  decided_at?: string | null
  decided_reason?: string | null
  execution_result?: any
}

const AGENT_COLORS: Record<string, string> = {
  support: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  lead: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  operations: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  reporting: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  analytics: 'bg-green-500/10 text-green-400 border-green-500/30',
  email: 'bg-pink-500/10 text-pink-400 border-pink-500/30',
  research: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
  review: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
}

function statusBadge(status: string): string {
  if (status === 'approved' || status === 'executed') return 'bg-success/10 text-success border-success/20'
  if (status === 'rejected') return 'bg-danger/10 text-danger border-danger/20'
  return 'bg-warning/10 text-warning border-warning/20'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = { pending: 'Pending', approved: 'Approved', rejected: 'Rejected', executed: 'Executed' }
  return map[status] || status
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60000) return 'just now'
  const min = Math.floor(ms / 60000)
  if (min < 60) return min + 'm ago'
  const h = Math.floor(min / 60)
  if (h < 24) return h + 'h ago'
  const d = Math.floor(h / 24)
  return d + 'd ago'
}

function isHighRisk(a: Approval): boolean {
  const t = (a.reason + ' ' + a.task_description).toLowerCase()
  return /high|risk|critical|escalat|exceeds|threshold/.test(t)
}

export function Approvals() {
  const [allApprovals, setAllApprovals] = useState<Approval[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [statusTab, setStatusTab] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')
  const [agentFilter, setAgentFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [detail, setDetail] = useState<any | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [rejectNote, setRejectNote] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  const [searchParams] = useSearchParams()
  const highlightId = searchParams.get('id')

  const token = () => localStorage.getItem('nexora_token')
  const authHeaders = () => ({ Authorization: 'Bearer ' + token(), 'Content-Type': 'application/json' })

  async function fetchAll() {
    const statuses = ['pending', 'approved', 'rejected']
    try {
      const results = await Promise.all(
        statuses.map((s) =>
          fetch('/api/v1/approvals?status=' + s, { headers: authHeaders() })
            .then((r) => (r.ok ? r.json() : []))
            .catch(() => [])
        )
      )
      const merged = (results.flat() as Approval[]).slice()
      merged.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      setAllApprovals(merged)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    async function init() {
      await fetchAll()
      setLoading(false)
    }
    init()
  }, [])

  useEffect(() => {
    if (highlightId && allApprovals.length > 0) {
      setTimeout(() => {
        const el = document.getElementById('approval-' + highlightId)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          el.classList.add('ring-2', 'ring-accent')
          setTimeout(() => el.classList.remove('ring-2', 'ring-accent'), 4000)
        }
      }, 400)
    }
  }, [highlightId, allApprovals])

  async function handleRefresh() {
    setRefreshing(true)
    await fetchAll()
    setRefreshing(false)
  }

  const agents = useMemo(() => {
    const set = new Set(allApprovals.map((a) => a.agent_type))
    return ['all', ...Array.from(set).sort()]
  }, [allApprovals])

  const counts = useMemo(() => ({
    all: allApprovals.length,
    pending: allApprovals.filter((a) => a.status === 'pending').length,
    approved: allApprovals.filter((a) => a.status === 'approved' || a.status === 'executed').length,
    rejected: allApprovals.filter((a) => a.status === 'rejected').length,
    highRisk: allApprovals.filter(isHighRisk).length,
  }), [allApprovals])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    return allApprovals.filter((a) => {
      if (statusTab !== 'all') {
        if (statusTab === 'approved' && !['approved', 'executed'].includes(a.status)) return false
        if (statusTab !== 'approved' && a.status !== statusTab) return false
      }
      if (agentFilter !== 'all' && a.agent_type !== agentFilter) return false
      if (q) {
        const hay = (a.id + ' ' + a.reason + ' ' + a.task_description).toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [allApprovals, statusTab, agentFilter, search])

  async function openDetail(a: Approval) {
    setDetail(a)
    setDetailLoading(true)
    setShowRejectForm(false)
    setRejectNote('')
    try {
      const res = await fetch('/api/v1/approvals/' + a.id, { headers: authHeaders() })
      if (res.ok) setDetail(await res.json())
    } catch (err) {
      console.error(err)
    } finally {
      setDetailLoading(false)
    }
  }

  async function decide(a: Approval, action: 'approve' | 'reject', note?: string) {
    setActionLoading(a.id + ':' + action)
    try {
      const res = await fetch('/api/v1/approvals/' + a.id + '/' + action, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ note: note || (action === 'approve' ? 'Approved via Approvals Center' : 'Rejected via Approvals Center') }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Action failed')
      }
      setToast({ kind: 'ok', msg: (action === 'approve' ? 'Approved' : 'Rejected') + ' successfully' })
      setTimeout(() => setToast(null), 3000)
      setDetail(null)
      await fetchAll()
    } catch (err: any) {
      setToast({ kind: 'err', msg: err.message })
      setTimeout(() => setToast(null), 4000)
    } finally {
      setActionLoading(null)
    }
  }

  function exportCSV() {
    const rows: string[][] = [['id', 'agent_type', 'status', 'reason', 'task_description', 'created_at', 'decided_at']]
    filtered.forEach((a) => rows.push([
      a.id, a.agent_type, a.status, a.reason.replace(/"/g, '""'),
      a.task_description.replace(/"/g, '""'), a.created_at, a.decided_at || ''
    ]))
    const csv = rows.map((r) => r.map((v) => '"' + v + '"').join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'approvals-' + new Date().toISOString().slice(0, 10) + '.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Approvals Center</h1>
          <p className="text-sm text-muted">
            {loading ? 'Loading...' : counts.all + ' total - ' + counts.pending + ' pending - ' + counts.approved + ' approved - ' + counts.rejected + ' rejected'}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={exportCSV} disabled={filtered.length === 0} className="bg-background border border-border text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-panelHover disabled:opacity-50 flex items-center gap-2">
            <Download className="w-4 h-4" /> Export CSV
          </button>
          <button onClick={handleRefresh} disabled={refreshing} className="bg-accent text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-accentHover disabled:opacity-50 flex items-center gap-2">
            <RefreshCw className={'w-4 h-4 ' + (refreshing ? 'animate-spin' : '')} /> Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Pending', value: counts.pending, icon: Clock, color: 'text-warning' },
          { label: 'Approved', value: counts.approved, icon: CheckCircle2, color: 'text-success' },
          { label: 'Rejected', value: counts.rejected, icon: XCircle, color: 'text-danger' },
          { label: 'High Risk', value: counts.highRisk, icon: AlertTriangle, color: 'text-orange-400' },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-background border border-border rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-muted mb-1">{kpi.label}</p>
              <p className="text-2xl font-bold text-white">{loading ? '...' : kpi.value}</p>
            </div>
            <kpi.icon className={'w-6 h-6 ' + kpi.color} />
          </div>
        ))}
      </div>

      <div className="bg-background border border-border rounded-xl p-4 mb-4 flex flex-wrap items-center gap-3">
        <div className="flex gap-1">
          {(['all', 'pending', 'approved', 'rejected'] as const).map((tab) => (
            <button key={tab} onClick={() => setStatusTab(tab)}
              className={'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ' + (statusTab === tab ? 'bg-accent text-white' : 'text-muted hover:bg-panelHover')}>
              {tab === 'all' ? 'All (' + counts.all + ')' : tab === 'approved' ? 'Approved (' + counts.approved + ')' : tab === 'pending' ? 'Pending (' + counts.pending + ')' : 'Rejected (' + counts.rejected + ')'}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)}
          className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50">
          {agents.map((a) => <option key={a} value={a}>{a === 'all' ? 'All agents' : a}</option>)}
        </select>
        <div className="relative">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search..." className="bg-background border border-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-white w-64 focus:outline-none focus:border-accent/50" />
        </div>
      </div>

      <div className="bg-background border border-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse flex gap-3">
                <div className="h-4 bg-border rounded w-24" />
                <div className="h-4 bg-border rounded w-20" />
                <div className="h-4 bg-border rounded flex-1" />
                <div className="h-4 bg-border rounded w-24" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <ShieldCheck className="w-10 h-10 text-muted mx-auto mb-3 opacity-40" />
            <p className="text-sm text-white mb-1">{allApprovals.length === 0 ? 'No approvals yet' : 'No approvals match your filter'}</p>
            <p className="text-xs text-muted">{allApprovals.length === 0 ? 'Agents will create approval requests when they need human review.' : 'Try changing the status tab, agent, or search.'}</p>
          </div>
        ) : (
          <table className="w-full text-left table-fixed">
              <colgroup>
                <col style={{ width: '90px' }} />
                <col style={{ width: '110px' }} />
                <col style={{ width: '110px' }} />
                <col />
                <col style={{ width: '90px' }} />
                <col style={{ width: '90px' }} />
                <col style={{ width: '190px' }} />
              </colgroup>
            <thead>
              <tr className="bg-background border-b border-border text-xs text-muted uppercase tracking-wider">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Reason</th>
                <th className="px-4 py-3 font-medium">Requested</th>
                <th className="px-4 py-3 font-medium">Decision</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((a) => (
                <tr key={a.id} id={`approval-${a.id}`} className="hover:bg-backgroundHover transition-colors">
                  <td className="px-4 py-3 text-xs font-mono text-white">#{a.id.slice(0, 8)}</td>
                  <td className="px-4 py-3">
                    <span className={'text-xs px-2 py-0.5 rounded border flex items-center gap-1 w-fit ' + (AGENT_COLORS[a.agent_type] || 'bg-panelHover text-muted border-border')}>
                      <Bot className="w-3 h-3" /> {a.agent_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={'text-xs px-2 py-0.5 rounded border ' + statusBadge(a.status)}>{statusLabel(a.status)}</span>
                    {isHighRisk(a) && a.status === 'pending' && (<AlertTriangle className="w-3 h-3 text-orange-400 inline ml-1" />)}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-300 truncate" title={a.reason}>{a.reason}</td>
                  <td className="px-4 py-3 text-xs text-muted">{relativeTime(a.created_at)}</td>
                  <td className="px-4 py-3 text-xs text-muted">{a.decided_at ? relativeTime(a.decided_at) : '-'}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-1 justify-end flex-nowrap">
                      <button onClick={() => openDetail(a)} className="text-xs bg-background border border-border text-white px-2 py-1 rounded hover:bg-panelHover flex items-center gap-1 whitespace-nowrap">
                        <Eye className="w-3 h-3" /> View
                      </button>
                      {a.status === 'pending' && (
                        <>
                          <button onClick={() => decide(a, 'approve')} disabled={actionLoading === a.id + ':approve'}
                            className="text-xs bg-success/10 text-success border border-success/30 px-2 py-1 rounded hover:bg-success/20 disabled:opacity-50 flex items-center gap-1 whitespace-nowrap">
                            {actionLoading === a.id + ':approve' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                            Approve
                          </button>
                          <button onClick={() => { setDetail(a); setShowRejectForm(true) }} disabled={actionLoading === a.id + ':reject'}
                            className="text-xs bg-danger/10 text-danger border border-danger/30 px-2 py-1 rounded hover:bg-danger/20 disabled:opacity-50 flex items-center gap-1 whitespace-nowrap">
                            <X className="w-3 h-3" /> Reject
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detail && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setDetail(null)}>
          <div className="bg-background border border-border rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-border flex items-start justify-between shrink-0">
              <div>
                <h3 className="text-lg font-semibold text-white">Approval #{detail.id.slice(0, 8)}</h3>
                <p className="text-xs text-muted mt-1">{detail.agent_type} - task #{detail.task_id} - created {relativeTime(detail.created_at)}</p>
              </div>
              <button onClick={() => setDetail(null)} className="text-muted hover:text-white p-1"><X className="w-5 h-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Status</p>
                  <span className={'text-xs px-2 py-0.5 rounded border ' + statusBadge(detail.status)}>{statusLabel(detail.status)}</span>
                </div>
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Agent</p>
                  <p className="text-sm text-white capitalize">{detail.agent_type}</p>
                </div>
                <div className="bg-background border border-border rounded-lg p-3">
                  <p className="text-[10px] text-muted uppercase mb-1">Decided</p>
                  <p className="text-sm text-white">{detail.decided_at ? relativeTime(detail.decided_at) : '-'}</p>
                </div>
              </div>
              <div>
                <p className="text-xs uppercase text-muted mb-1">Reason</p>
                <p className="text-sm text-white">{detail.reason}</p>
              </div>
              {detail.decided_reason && (
                <div>
                  <p className="text-xs uppercase text-muted mb-1">Decision Reason</p>
                  <p className="text-sm text-white">{detail.decided_reason}</p>
                </div>
              )}
              <div>
                <p className="text-xs uppercase text-muted mb-1">Task</p>
                <p className="text-sm text-white">{detail.task_description}</p>
              </div>
              {detailLoading ? (
                <div className="text-center text-sm text-muted py-4"><Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Loading proposed action...</div>
              ) : detail.proposed_action ? (
                <div>
                  <p className="text-xs uppercase text-muted mb-2">Proposed Action</p>
                  <ProposedActionView proposed={detail.proposed_action} />
                </div>
              ) : null}
              {detail.execution_result && Object.keys(detail.execution_result || {}).length > 0 && (
                <div>
                  <p className="text-xs uppercase text-muted mb-2">Execution Result</p>
                  <pre className="p-3 bg-background border border-border rounded-lg text-xs text-success overflow-x-auto max-h-40">
{JSON.stringify(detail.execution_result, null, 2)}
                  </pre>
                </div>
              )}
              {showRejectForm && (
                <div className="bg-danger/5 border border-danger/30 rounded-lg p-3">
                  <p className="text-xs text-danger uppercase mb-2">Reject reason (required)</p>
                  <textarea value={rejectNote} onChange={(e) => setRejectNote(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg p-2 text-sm text-white focus:outline-none focus:border-danger/50"
                    rows={3} placeholder="Why are you rejecting this action?" />
                </div>
              )}
            </div>
            {detail.status === 'pending' && (
              <div className="px-6 py-3 border-t border-border flex gap-2 shrink-0">
                {showRejectForm ? (
                  <>
                    <button onClick={() => decide(detail, 'reject', rejectNote)} disabled={!rejectNote.trim() || actionLoading === detail.id + ':reject'}
                      className="flex-1 bg-danger text-white py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50">Confirm Reject</button>
                    <button onClick={() => { setShowRejectForm(false); setRejectNote('') }} className="px-4 bg-background border border-border text-white py-2 rounded-lg text-sm">Cancel</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => decide(detail, 'approve')} disabled={actionLoading === detail.id + ':approve'}
                      className="flex-1 bg-success text-white py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50">
                      {actionLoading === detail.id + ':approve' ? 'Approving...' : 'Approve'}
                    </button>
                    <button onClick={() => setShowRejectForm(true)} className="flex-1 bg-danger/10 text-danger border border-danger/30 py-2 rounded-lg text-sm font-medium hover:bg-danger/20">Reject</button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {toast && (
        <div className={'fixed bottom-6 right-6 z-50 border rounded-lg px-4 py-3 shadow-lg text-sm text-white ' + (toast.kind === 'ok' ? 'bg-panel border-success/50' : 'bg-panel border-danger/50')}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
