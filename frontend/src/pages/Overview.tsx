import { useState, useEffect } from 'react'
import { RunsAreaChart, StatusDonutChart } from '../components/DashboardCharts'

export function Overview() {
  const [data, setData] = useState({ approvals: 0, integrations: 0, runs: 0, success: 0 })
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const token = localStorage.getItem('nexora_token')
        const headers = { 'Authorization': 'Bearer ' + token }
        const results = await Promise.allSettled([
          fetch('/api/v1/approvals?status=pending', { headers }),
          fetch('/api/v1/integrations', { headers }),
          fetch('/api/v1/orchestrator/runs', { headers })
        ])

        let approvals: any = []
        let integrations: any = []
        let runsData: any = []

        if (results[0].status === 'fulfilled' && results[0].value.ok) {
          approvals = await results[0].value.json()
        }
        if (results[1].status === 'fulfilled' && results[1].value.ok) {
          integrations = await results[1].value.json()
        }
        if (results[2].status === 'fulfilled' && results[2].value.ok) {
          runsData = await results[2].value.json()
        }

        const runsArray = Array.isArray(runsData) ? runsData : []
        const completed = runsArray.filter((r: any) => r.status === 'completed').length
        const successRate = runsArray.length ? Math.round((completed / runsArray.length) * 100) : 0
        const newData = {
          approvals: Array.isArray(approvals) ? approvals.length : 0,
          integrations: Array.isArray(integrations) ? integrations.length : 0,
          runs: runsArray.length,
          success: successRate
        }
        setData(newData)
        setRuns(runsArray)
      } catch (err) {
        console.error('[Overview] FETCH ERROR:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold text-white mb-1">Overview</h2>
      <p className="text-sm text-muted mb-6">Business KPIs and recent automation</p>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Pending Approvals', value: loading ? '...' : data.approvals, change: 'Awaiting review' },
          { label: 'Connected Integrations', value: loading ? '...' : data.integrations, change: 'Active services' },
          { label: 'Total Runs', value: loading ? '...' : data.runs, change: 'All time' },
          { label: 'Success Rate', value: loading ? '...' : data.success + '%', change: 'Completed / total' },
        ].map((kpi, i) => (
          <div key={i} className="bg-background border border-border rounded-xl p-5">
            <p className="text-xs text-muted mb-2">{kpi.label}</p>
            <p className="text-3xl font-bold text-white mb-1">{kpi.value}</p>
            <p className="text-xs text-muted">{kpi.change}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-background border border-border rounded-xl p-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-semibold text-white">Workflow Activity</h3>
            <span className="text-xs text-muted bg-background px-2 py-1 rounded border border-border">Last 7 Days</span>
          </div>
          <RunsAreaChart runs={runs} />
        </div>

        <div className="col-span-1 bg-background border border-border rounded-xl p-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-semibold text-white">Run Status</h3>
          </div>
          <StatusDonutChart runs={runs} />
        </div>
      </div>
    </div>
  )
}