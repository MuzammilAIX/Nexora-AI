import { useState, useEffect, useCallback } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap, useNodesState, useEdgesState, addEdge, Handle, Position
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Play, Settings, Zap, Bot, Database, Send, CheckCircle2, Activity } from 'lucide-react'

const CustomNode = ({ data }: any) => {
  const Icon = data.icon
  return (
    <div className="bg-panel border-2 border-border hover:border-accent/50 rounded-xl shadow-xl min-w-[180px] overflow-hidden transition-colors">
      <div className="bg-panelHover px-3 py-2 border-b border-border flex items-center gap-2">
        <Icon className="w-4 h-4 text-accent" />
        <span className="text-xs font-semibold text-white truncate">{data.label}</span>
      </div>
      <div className="p-3">
        <p className="text-[11px] text-muted">{data.subLabel}</p>
      </div>
      <Handle type="target" position={Position.Left} className="!bg-accent !w-2 !h-2 !border-2 !border-panel" />
      <Handle type="source" position={Position.Right} className="!bg-accent !w-2 !h-2 !border-2 !border-panel" />
    </div>
  )
}

const nodeTypes = { custom: CustomNode }

const initialNodes = [
  { id: '1', type: 'custom', position: { x: 50, y: 150 }, data: { label: 'Webhook', subLabel: 'POST /lead', icon: Zap } },
  { id: '2', type: 'custom', position: { x: 300, y: 150 }, data: { label: 'Set Data', subLabel: 'Manual mapping', icon: Settings } },
  { id: '3', type: 'custom', position: { x: 550, y: 150 }, data: { label: 'OpenAI', subLabel: 'Message Model', icon: Bot } },
  { id: '4', type: 'custom', position: { x: 800, y: 50 }, data: { label: 'Slack', subLabel: 'Send Message', icon: Send } },
  { id: '5', type: 'custom', position: { x: 800, y: 250 }, data: { label: 'Postgres', subLabel: 'Insert Row', icon: Database } },
]

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#8B5CF6', strokeWidth: 2 } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8B5CF6', strokeWidth: 2 } },
  { id: 'e3-4', source: '3', target: '4', style: { stroke: '#8B5CF6', strokeWidth: 2 } },
  { id: 'e3-5', source: '3', target: '5', style: { stroke: '#8B5CF6', strokeWidth: 2 } },
]

export function Workflows() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [runs, setRuns] = useState<any[]>([])

  useEffect(() => {
    async function fetchRuns() {
      try {
        const token = localStorage.getItem('nexora_token')
        const res = await fetch('/api/v1/orchestrator/runs', { headers: { 'Authorization': `Bearer ${token}` } })
        const data = await res.json()
        setRuns(Array.isArray(data) ? data : [])
      } catch (e) {
        console.error(e)
      }
    }
    fetchRuns()
  }, [])

  const onConnect = useCallback((params: any) => setEdges((eds) => addEdge(params, eds)), [setEdges])

  return (
    <div className="flex flex-col bg-background" style={{ height: "calc(100vh - 64px)" }}>
      <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-panel">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-xl font-bold text-white">Lead Qualification Workflow</h2>
            <span className="px-2 py-0.5 rounded-full bg-success/10 text-success text-xs font-medium border border-success/20">Active</span>
          </div>
          <p className="text-xs text-muted font-mono flex items-center gap-2">
            ID: a1b2c3d4-e5f6-7890-abcd-1234567890ab
            <button className="hover:text-white"><Settings className="w-3 h-3" /></button>
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-background border border-border text-white text-sm font-medium rounded-lg hover:bg-panelHover transition-colors">Edit Workflow</button>
          <button className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accentHover transition-colors flex items-center gap-2">
            <Play className="w-4 h-4" /> Execute Workflow
          </button>
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        <div className="flex flex-col min-w-0 border-r border-border" style={{ flex: "1 1 0%", display: "flex", flexDirection: "column" }}>
          <div className="relative bg-[#0B0F19]" style={{ flex: "1 1 0%", minHeight: "400px", width: "100%" }}>
            <ReactFlow style={{ width: "100%", height: "100%", position: "absolute", inset: 0 }}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              className="bg-dot-pattern" proOptions={{ hideAttribution: true }}
            >
              <Background color="#1F2937" gap={16} size={2} />
              <Controls className="!bg-panel !border-border !fill-white" />
              <MiniMap className="!bg-panel !border-border" nodeColor="#8B5CF6" maskColor="rgba(0,0,0,0.7)" />
            </ReactFlow>
          </div>

          <div className="h-64 bg-panel border-t border-border flex flex-col shrink-0">
            <div className="px-4 py-3 border-b border-border flex justify-between items-center bg-panelHover/30">
              <h3 className="text-sm font-semibold text-white">Execution History</h3>
              <button className="text-xs text-accent hover:text-accentHover font-medium">View All Executions</button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-muted bg-background sticky top-0 border-b border-border">
                  <tr>
                    <th className="px-4 py-2 font-medium">ID</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 font-medium">Started At</th>
                    <th className="px-4 py-2 font-medium">Workflow</th>
                    <th className="px-4 py-2 font-medium">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runs.slice(0, 5).map(run => (
                    <tr key={run.id} className="hover:bg-panelHover/50 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-muted">#{run.id.split('-')[0]}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 ${run.status === 'completed' ? 'text-success' : run.status === 'failed' ? 'text-danger' : 'text-warning'}`}>
                          {run.status === 'completed' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Activity className="w-3.5 h-3.5" />}
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted text-xs">{new Date(run.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3 text-white text-xs">Lead Qualification Workflow</td>
                      <td className="px-4 py-3 text-muted text-xs font-mono">1.24s</td>
                    </tr>
                  ))}
                  {runs.length === 0 && (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-muted">No recent executions found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="w-80 bg-panel flex flex-col p-4 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">System Overview</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-background border border-border rounded-lg p-3">
                <p className="text-xs text-muted mb-1">Uptime</p>
                <p className="text-xl font-bold text-success">99.98%</p>
                <div className="h-6 w-full mt-2 opacity-50">
                  <svg viewBox="0 0 100 20" className="w-full h-full stroke-success fill-none" strokeWidth="2">
                    <path d="M0,15 L10,15 L20,14 L30,12 L40,14 L50,8 L60,9 L70,5 L80,7 L90,4 L100,4" />
                  </svg>
                </div>
              </div>
              <div className="bg-background border border-border rounded-lg p-3">
                <p className="text-xs text-muted mb-1">Error Rate</p>
                <p className="text-xl font-bold text-success">0%</p>
                <p className="text-[10px] text-muted mt-2">Last 7 days</p>
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-semibold text-white">Webhook Triggers</h3>
              <button className="text-xs text-accent hover:text-accentHover">View All</button>
            </div>
            <div className="space-y-2">
              {[
                { path: '/lead', name: 'Lead Capture Webhook' },
                { path: '/form-submission', name: 'Form Submission' },
                { path: '/customer-update', name: 'Customer Update' },
              ].map((hook, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 bg-background border border-border rounded-lg">
                  <div className="flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5 text-muted" />
                    <div>
                      <p className="text-xs text-white font-medium">POST {hook.path}</p>
                      <p className="text-[10px] text-muted">{hook.name}</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-medium text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">Active</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-auto pt-4 border-t border-border">
            <h3 className="text-sm font-semibold text-white mb-3">Workflow Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted text-xs">Executions</span><span className="text-white text-xs font-mono">12,543</span></div>
              <div className="flex justify-between"><span className="text-muted text-xs">Success Rate</span><span className="text-success text-xs font-mono">100%</span></div>
              <div className="flex justify-between"><span className="text-muted text-xs">Avg. Duration</span><span className="text-white text-xs font-mono">1.23s</span></div>
              <div className="flex justify-between"><span className="text-muted text-xs">Total Errors</span><span className="text-white text-xs font-mono">0</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
