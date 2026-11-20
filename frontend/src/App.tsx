import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  ShieldAlert,
  Bot,
  DollarSign,
  GitBranch,
  ListChecks,
  Plug,
  FileText,
  Settings,
  Bell,
  Search,
  Activity,
} from 'lucide-react'
import { RunsAreaChart, StatusDonutChart } from './components/DashboardCharts'
import { Login } from './components/Login'
import { Overview } from './pages/Overview'
import { MissionControl } from './pages/MissionControl'
import { CRM } from './pages/CRM'
import { Assistant } from './pages/Assistant'
import { Workflows } from './pages/Workflows'
import { Executions } from './pages/Executions'

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/mission-control', label: 'Mission Control', icon: ShieldAlert },
  { to: '/crm', label: 'Sales Pipeline', icon: DollarSign },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/workflows', label: 'Workflows', icon: GitBranch },
  { to: '/executions', label: 'Executions', icon: ListChecks },
  { to: '/integrations', label: 'Integrations', icon: Plug },
  { to: '/activity', label: 'Activity', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function Sidebar() {
  return (
    <aside className="w-64 h-screen bg-panel border-r border-border flex flex-col fixed left-0 top-0">
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-bold text-white tracking-tight">
          Nexora <span className="text-accent">AI</span>
        </h1>
        <p className="text-xs text-muted mt-1">Command Center</p>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ' +
              (isActive ? 'bg-accent/10 text-accent border border-accent/20' : 'text-gray-400 hover:text-white hover:bg-panelHover')
            }
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold">T</div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-white truncate">Test User</p>
            <p className="text-xs text-muted truncate">test@nexora-test.com</p>
          </div>
          <button
            onClick={() => { localStorage.clear(); window.location.reload(); }}
            className="text-xs text-muted hover:text-danger transition-colors"
          >
            Out
          </button>
        </div>
      </div>
    </aside>
  )
}

function Topbar() {
  return (
    <header className="h-16 bg-panel border-b border-border flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative w-96 max-w-full">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search anything..."
            className="w-full bg-background border border-border rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:border-accent/50"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button className="p-2 rounded-lg hover:bg-panelHover text-gray-400 hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
        </button>
      </div>
    </header>
  )
}

function Placeholder({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold text-white mb-1">{title}</h2>
      <p className="text-sm text-muted mb-6">{subtitle}</p>
      <div className="bg-panel border border-border rounded-xl p-8 text-center">
        <Activity className="w-12 h-12 text-muted mx-auto mb-4 opacity-50" />
        <p className="text-muted text-sm">Coming in the next slice.</p>
      </div>
    </div>
  )
}

function App() {
  const [authed, setAuthed] = useState<boolean | null>(null)

  useEffect(() => {
    setAuthed(!!localStorage.getItem('nexora_token'))
  }, [])

  if (authed === null) return <div className="min-h-screen bg-background" />
  if (!authed) return <Login />

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <div className="ml-64">
          <Topbar />
          <main>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/mission-control" element={<MissionControl />} />
              <Route path="/crm" element={<CRM />} />
              <Route path="/assistant" element={<Assistant />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/executions" element={<Executions />} />
              <Route path="/integrations" element={<Placeholder title="Integrations" subtitle="Connected external services" />} />
              <Route path="/activity" element={<Placeholder title="Activity" subtitle="Audit trail of all events" />} />
              <Route path="/settings" element={<Placeholder title="Settings" subtitle="Users, roles, permissions" />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
