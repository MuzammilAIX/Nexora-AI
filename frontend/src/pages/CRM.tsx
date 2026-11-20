import { useState } from 'react'
import {
  Search, Bot, Send, TrendingUp, MoreHorizontal, Plus, X, Sparkles
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'

const initialColumns = {
  'leads': { id: 'leads', title: 'Leads', cards: [
    { id: 'c1', company: 'Acme Corp', value: '$3.00M', probability: '85%', owner: 'Sarah K.', tag: 'Hot' },
    { id: 'c2', company: 'TechWave', value: '$2.30M', probability: '20%', owner: 'Mike T.', tag: 'New' }
  ]},
  'qualified': { id: 'qualified', title: 'Qualified', cards: [
    { id: 'c3', company: 'Global Logistics', value: '$1.20M', probability: '65%', owner: 'Sarah K.', tag: 'Warm' },
    { id: 'c4', company: 'Starlight Media', value: '$1.50M', probability: '70%', owner: 'Alex B.', tag: 'Warm' }
  ]},
  'demo': { id: 'demo', title: 'Demo', cards: [
    { id: 'c5', company: 'FinServe Group', value: '$3.90M', probability: '55%', owner: 'Mike T.', tag: 'Active' }
  ]},
  'proposal': { id: 'proposal', title: 'Proposal', cards: [
    { id: 'c6', company: 'Horizon Retail', value: '$1.30M', probability: '90%', owner: 'Sarah K.', tag: 'Hot' }
  ]},
  'negotiation': { id: 'negotiation', title: 'Negotiation', cards: [
    { id: 'c7', company: 'Nexus Industries', value: '$1.20M', probability: '95%', owner: 'Alex B.', tag: 'Closing' }
  ]},
  'closed': { id: 'closed', title: 'Closed', cards: [] }
}

const chartData = [
  { name: 'Jan', revenue: 12 }, { name: 'Feb', revenue: 19 },
  { name: 'Mar', revenue: 15 }, { name: 'Apr', revenue: 28 },
  { name: 'May', revenue: 24 }, { name: 'Jun', revenue: 42 },
  { name: 'Jul', revenue: 55 },
]

export function CRM() {
  const [columns, setColumns] = useState(initialColumns)
  const [chatOpen, setChatOpen] = useState(true)
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! I am your AI sales assistant. I can help qualify leads, draft emails, or predict deal outcomes. What do you need?' }
  ])
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    setMessages([...messages, { role: 'user', text: input }])
    setInput('')
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: 'I have analyzed your pipeline. You have a high chance of closing Horizon Retail this week. Should I draft an email?' 
      }])
    }, 1000)
  }

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-[#0B0F19] overflow-hidden">
      
      <div className="px-6 py-4 border-b border-border flex justify-between items-center shrink-0">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Sales Pipeline</h2>
          <p className="text-xs text-muted">Manage deals and AI assistance</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input type="text" placeholder="Search deals..." className="bg-panel border border-border rounded-lg pl-9 pr-4 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50 w-64" />
          </div>
          <button className="px-4 py-1.5 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accentHover transition-colors flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add Deal
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-x-auto p-6 flex gap-4">
          {Object.values(columns).map((col) => (
            <div key={col.id} className="w-72 shrink-0 flex flex-col bg-panel/30 rounded-xl border border-border">
              <div className="p-3 border-b border-border flex justify-between items-center">
                <span className="text-sm font-semibold text-white">{col.title}</span>
                <span className="text-xs text-muted bg-background px-2 py-0.5 rounded-full">{col.cards.length}</span>
              </div>
              <div className="flex-1 p-2 space-y-2 overflow-y-auto min-h-[150px]">
                {col.cards.map((card) => (
                  <div key={card.id} className="bg-background border border-border rounded-lg p-3 shadow-sm hover:border-accent/50 transition-colors cursor-grab">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="text-sm font-semibold text-white">{card.company}</h4>
                      <MoreHorizontal className="w-4 h-4 text-muted" />
                    </div>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-lg font-bold text-white">{card.value}</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-success bg-success/10 px-2 py-0.5 rounded flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> {card.probability}
                      </span>
                      <span className="text-muted flex items-center gap-1">
                        <div className="w-4 h-4 rounded-full bg-accent/20 flex items-center justify-center text-[8px] text-accent font-bold">
                          {card.owner.split(' ').map(n => n[0]).join('')}
                        </div>
                        {card.owner}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {chatOpen && (
          <div className="w-80 border-l border-border bg-panel flex flex-col shrink-0">
            <div className="p-4 border-b border-border flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold text-white">AI Assistant</h3>
              </div>
              <button onClick={() => setChatOpen(false)} className="text-muted hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  {msg.role === 'ai' && (
                    <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center shrink-0">
                      <Bot className="w-3.5 h-3.5 text-accent" />
                    </div>
                  )}
                  <div className={`p-3 rounded-lg text-sm max-w-[85%] ${msg.role === 'user' ? 'bg-accent text-white rounded-tr-none' : 'bg-background border border-border text-gray-300 rounded-tl-none'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3 border-t border-border">
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask AI about your pipeline..."
                  className="w-full bg-background border border-border rounded-lg pl-3 pr-10 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
                />
                <button onClick={handleSend} className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-accent hover:text-white transition-colors">
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="h-48 bg-panel border-t border-border p-4 shrink-0">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-sm font-semibold text-white">Revenue Growth</h3>
          <div className="flex items-center gap-4 text-xs">
            <span className="text-success flex items-center gap-1"><Sparkles className="w-3 h-3" /> AI Predicts +15%</span>
          </div>
        </div>
        <div className="h-32 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
              <XAxis dataKey="name" stroke="#6B7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis hide />
              <RechartsTooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="revenue" stroke="#8B5CF6" strokeWidth={2} fillOpacity={1} fill="url(#colorRev)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  )
}
