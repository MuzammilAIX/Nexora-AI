import { Mail, AlertTriangle, Tag, TrendingUp } from 'lucide-react'

function classifyKind(proposed: any): string {
  if (!proposed) return 'unknown'
  if (proposed.action_kind) return proposed.action_kind
  if (proposed.proposed_email) return 'send_email'
  if (proposed.proposed_order) return 'create_order'
  if (proposed.proposed_flag) return 'flag_customer'
  if (proposed.proposed_tasks) return 'create_tasks'
  return 'unknown'
}

function priorityColor(p: string | undefined): string {
  if (!p) return 'bg-panelHover text-muted border-border'
  const lp = p.toLowerCase()
  if (lp === 'high' || lp === 'urgent') return 'bg-danger/10 text-danger border-danger/30'
  if (lp === 'medium' || lp === 'normal') return 'bg-warning/10 text-warning border-warning/30'
  return 'bg-success/10 text-success border-success/30'
}

function confidenceColor(c: number): string {
  if (c >= 75) return 'text-success'
  if (c >= 50) return 'text-warning'
  return 'text-danger'
}

export function ProposedActionView({ proposed }: { proposed: any }) {
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
      {summary && (
        <div>
          <p className="text-xs uppercase text-muted mb-1">Summary</p>
          <p className="text-sm text-white">{summary}</p>
        </div>
      )}

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

      {(proposed.proposed_tasks || prepared.proposed_tasks) && (
        <div className="bg-background border border-border rounded-lg p-3">
          <p className="text-xs uppercase text-muted mb-2">Proposed Tasks</p>
          <ul className="space-y-1 text-sm text-white">
            {(proposed.proposed_tasks || prepared.proposed_tasks).map((t: any, i: number) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-accent mt-0.5">•</span>
                <span>{typeof t === 'string' ? t : (t.title || t.subject || JSON.stringify(t))}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {gaps.length > 0 && (
        <div className="bg-warning/10 border border-warning/30 rounded-lg p-3">
          <p className="text-xs uppercase text-warning mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Gaps to review
          </p>
          <ul className="space-y-1 text-xs text-warning/90">
            {gaps.map((g: string, i: number) => <li key={i}>• {g}</li>)}
          </ul>
        </div>
      )}

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