import { useState, useEffect } from 'react'
import { Activity as ActivityIcon, CheckCircle2, AlertCircle, Clock } from 'lucide-react'

export function Activity() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchEvents() {
      try {
        const token = localStorage.getItem('nexora_token')
        const res = await fetch('/api/v1/audit', {
          headers: { 'Authorization': 'Bearer ' + token }
        })
        const data = await res.json()
        setEvents(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchEvents()
  }, [])

  const getIcon = (type: string) => {
    if (type.includes('failed')) return <AlertCircle className="w-4 h-4 text-danger" />
    if (type.includes('approval')) return <Clock className="w-4 h-4 text-warning" />
    return <CheckCircle2 className="w-4 h-4 text-success" />
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-white mb-1">Activity Log</h2>
      <p className="text-sm text-muted mb-8">Audit trail of all agent actions and system events.</p>

      <div className="bg-background border border-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-muted">Loading events...</div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center text-muted">No audit events found.</div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-background border-b border-border text-xs text-muted uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">Event</th>
                <th className="px-6 py-4 font-medium">Subject ID</th>
                <th className="px-6 py-4 font-medium">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {events.map((e, i) => (
                <tr key={i} className="hover:bg-backgroundHover transition-colors">
                  <td className="px-6 py-4 text-sm text-white flex items-center gap-2">
                    {getIcon(e.event_type)}
                    {e.event_type}
                  </td>
                  <td className="px-6 py-4 text-xs font-mono text-muted">
                    {e.subject_id ? e.subject_id.slice(0, 8) + '...' : '-'}
                  </td>
                  <td className="px-6 py-4 text-xs text-muted">
                    {new Date(e.created_at).toLocaleString()}
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
