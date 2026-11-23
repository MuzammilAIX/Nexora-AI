import { useState, useEffect } from 'react'

export interface Notification {
  id: string
  kind: 'approval' | 'failed_run'
  title: string
  subtitle: string
  link: string
  timestamp: string
}

export function useNotifications() {
  const [items, setItems] = useState<Notification[]>([])
  const [loading, setLoading] = useState(false)

  async function fetchAll() {
    const token = localStorage.getItem('nexora_token')
    if (!token) return
    const h = { Authorization: 'Bearer ' + token }
    setLoading(true)
    try {
      const [appr, runs] = await Promise.allSettled([
        fetch('/api/v1/approvals?status=pending', { headers: h }).then(r => r.ok ? r.json() : []),
        fetch('/api/v1/orchestrator/runs', { headers: h }).then(r => r.ok ? r.json() : []),
      ])
      const next: Notification[] = []
      if (appr.status === 'fulfilled' && Array.isArray(appr.value)) {
        for (const a of appr.value) {
          next.push({
            id: 'appr-' + a.id,
            kind: 'approval',
            title: 'Pending approval: ' + (a.agent_type || 'agent'),
            subtitle: a.task_description || a.reason || '',
            link: '/missioncontrol',
            timestamp: a.created_at || '',
          })
        }
      }
      if (runs.status === 'fulfilled' && Array.isArray(runs.value)) {
        for (const r of runs.value) {
          if (r.status === 'failed') {
            next.push({
              id: 'run-' + r.id,
              kind: 'failed_run',
              title: 'Run failed: ' + (r.user_request || r.id),
              subtitle: r.error || 'Execution failed',
              link: '/executions',
              timestamp: r.created_at || '',
            })
          }
        }
      }
      next.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      setItems(next)
    } catch {
      // silent — never block UI
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    const timer = setInterval(fetchAll, 30000)
    return () => clearInterval(timer)
  }, [])

  return { items, loading, refresh: fetchAll }
}