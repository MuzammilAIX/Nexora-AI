import { useState, useEffect } from 'react'
import { LifeBuoy, CheckCircle2, Clock, AlertCircle } from 'lucide-react'

interface Ticket {
  id: string
  user_id: string
  subject: string
  description: string
  status: string
  priority: string
  created_at: string
}

export function SupportInbox() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function fetchTickets() {
    try {
      const token = localStorage.getItem('nexora_token')
      const res = await fetch('/api/v1/support/tickets', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to fetch tickets')
      const data = await res.json()
      setTickets(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTickets()
  }, [])

  async function resolveTicket(id: string) {
    try {
      const token = localStorage.getItem('nexora_token')
      const res = await fetch(`/api/v1/support/tickets/${id}/resolve`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to resolve')
      fetchTickets() // Refresh the list
    } catch (err: any) {
      alert(err.message)
    }
  }

  if (loading) return <div className="p-8 text-muted">Loading tickets...</div>
  if (error) return <div className="p-8 text-danger">Error: {error}</div>

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-accent/10 rounded-lg">
          <LifeBuoy className="w-6 h-6 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Help & Support</h1>
          <p className="text-sm text-muted">Manage customer issues and support tickets</p>
        </div>
      </div>

      <div className="bg-panel border border-border rounded-xl shadow-sm overflow-hidden">
        {tickets.length === 0 ? (
          <div className="p-12 text-center text-muted">
            <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-success opacity-50" />
            <h3 className="text-lg font-medium text-white mb-1">All caught up!</h3>
            <p>There are no open support tickets.</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-panelHover">
                <th className="px-6 py-4 text-xs font-semibold text-muted uppercase">Ticket ID</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted uppercase">Subject</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted uppercase">Description</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted uppercase">Priority</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted uppercase">Status</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tickets.map((t) => (
                <tr key={t.id} className="hover:bg-panelHover transition-colors">
                  <td className="px-6 py-4 text-sm text-muted font-mono">#{t.id.slice(0, 8)}</td>
                  <td className="px-6 py-4 text-sm font-medium text-white">{t.subject}</td>
                  <td className="px-6 py-4 text-sm text-secondary max-w-xs truncate">{t.description}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                      t.priority === 'high' ? 'bg-danger/10 text-danger' : 
                      t.priority === 'urgent' ? 'bg-warning/10 text-warning' : 
                      'bg-accent/10 text-accent'
                    }`}>
                      {t.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                      t.status === 'resolved' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                    }`}>
                      {t.status === 'resolved' ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                      {t.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {t.status !== 'resolved' && (
                      <button 
                        onClick={() => resolveTicket(t.id)}
                        className="text-accent hover:text-accentHover font-medium transition-colors"
                      >
                        Mark Resolved
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}