import { useState, useEffect, useMemo } from 'react'
import { Search, Building2, Briefcase, ExternalLink, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  useDraggable,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'

interface HubSpotContact {
  id: string
  properties: {
    firstname?: string
    lastname?: string
    email?: string
    company?: string
    jobtitle?: string
    lifecyclestage?: string
    hs_lead_status?: string
    hubspot_owner_id?: string
    createdate?: string
    lastmodifieddate?: string
  }
  createdAt?: string
  updatedAt?: string
  url?: string
}

const STAGES: { key: string; label: string; matches: string[] }[] = [
  { key: 'new',         label: 'New Leads',       matches: ['lead', 'subscriber', ''] },
  { key: 'qualified',   label: 'Qualified',       matches: ['marketingqualifiedlead', 'mql'] },
  { key: 'contacted',   label: 'Contacted',       matches: ['salesqualifiedlead', 'sql'] },
  { key: 'demo',        label: 'Demo Scheduled',  matches: ['opportunity'] },
  { key: 'proposal',    label: 'Proposal',        matches: ['proposal'] },
  { key: 'negotiation', label: 'Negotiation',     matches: ['negotiation'] },
  { key: 'won',         label: 'Won',             matches: ['customer', 'evangelist'] },
  { key: 'lost',        label: 'Lost',            matches: ['other', 'unqualified'] },
]

const STAGE_OVERRIDE_KEY = 'nexora_crm_stage_overrides'

function loadOverrides(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STAGE_OVERRIDE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveOverrides(o: Record<string, string>) {
  localStorage.setItem(STAGE_OVERRIDE_KEY, JSON.stringify(o))
}

function stageFor(stage: string | undefined, override?: string): string {
  if (override && STAGES.some((s) => s.key === override)) return override
  const s = (stage || '').toLowerCase()
  for (const def of STAGES) {
    if (def.matches.includes(s)) return def.key
  }
  return 'new'
}

function fullName(c: HubSpotContact): string {
  const f = c.properties.firstname || ''
  const l = c.properties.lastname || ''
  const name = (f + ' ' + l).trim()
  return name || c.properties.email || `Contact ${c.id.slice(-6)}`
}

function initials(name: string): string {
  return name.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]?.toUpperCase()).join('') || '?'
}

function timeAgo(iso: string | undefined): string {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 0) return 'just now'
  const min = Math.floor(ms / 60000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min}m ago`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

function scoreFor(c: HubSpotContact): number {
  const p = c.properties
  let score = 40
  const lc = (p.lifecyclestage || '').toLowerCase()
  if (['marketingqualifiedlead', 'mql'].includes(lc)) score += 20
  else if (['salesqualifiedlead', 'sql'].includes(lc)) score += 30
  else if (lc === 'opportunity') score += 40
  else if (['customer', 'evangelist'].includes(lc)) score += 50
  if (p.jobtitle) score += 5
  if (p.company) score += 5
  if (p.email) score += 5
  const last = p.lastmodifieddate || c.updatedAt
  if (last) {
    const days = (Date.now() - new Date(last).getTime()) / 86400000
    if (days < 7) score += 5
    else if (days > 30) score -= 5
  }
  return Math.max(0, Math.min(100, score))
}

function DraggableCard({ contact }: { contact: HubSpotContact }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: contact.id })
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined
  const name = fullName(contact)
  const p = contact.properties
  const score = scoreFor(contact)
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`bg-background border border-border rounded-lg p-3 hover:border-accent/40 transition-colors cursor-grab active:cursor-grabbing ${isDragging ? 'opacity-50' : ''}`}
    >
      <div className="flex items-start gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-semibold shrink-0">
          {initials(name)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate">{name}</p>
          {p.jobtitle && (
            <p className="text-[11px] text-muted truncate flex items-center gap-1">
              <Briefcase className="w-3 h-3 shrink-0" /> {p.jobtitle}
            </p>
          )}
        </div>
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${score >= 70 ? 'bg-green-500/20 text-green-400' : score >= 50 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-500/20 text-gray-400'}`}>
          {score}
        </span>
      </div>
      {p.company && (
        <p className="text-xs text-gray-300 mb-1 flex items-center gap-1 truncate">
          <Building2 className="w-3 h-3 text-muted shrink-0" /> {p.company}
        </p>
      )}
      {p.email && <p className="text-xs text-muted mb-2 truncate">{p.email}</p>}
      <div className="flex items-center justify-between pt-2 border-t border-border">
        <span className="text-[10px] text-muted uppercase">{p.lifecyclestage || 'lead'}</span>
        <span className="text-[10px] text-muted">{timeAgo(p.lastmodifieddate || contact.updatedAt)}</span>
      </div>
      {contact.url && (
        <a
          href={contact.url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-2 text-[11px] text-accent hover:underline flex items-center gap-1"
        >
          Open in HubSpot <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  )
}

function DroppableColumn({
  stage,
  items,
  activeId,
}: {
  stage: { key: string; label: string }
  items: HubSpotContact[]
  activeId: string | null
}) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.key })
  return (
    <div
      ref={setNodeRef}
      className={`w-72 bg-background border rounded-xl flex flex-col overflow-hidden ${isOver ? 'border-accent' : 'border-border'}`}
    >
      <div className="px-4 py-3 border-b border-border bg-background flex items-center justify-between shrink-0">
        <h3 className="text-sm font-semibold text-white">{stage.label}</h3>
        <span className="text-xs text-muted bg-background px-2 py-0.5 rounded">{items.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {items.length === 0 ? (
          <div className="text-xs text-muted text-center py-6">
            {activeId ? 'Drop here' : 'No contacts'}
          </div>
        ) : (
          items.map((c) => <DraggableCard key={c.id} contact={c} />)
        )}
      </div>
    </div>
  )
}

export function CRM() {
  const [contacts, setContacts] = useState<HubSpotContact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState<string>('all')
  const [ownerFilter, setOwnerFilter] = useState<string>('all')
  const [overrides, setOverrides] = useState<Record<string, string>>(() => loadOverrides())
  const [activeId, setActiveId] = useState<string | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const token = () => localStorage.getItem('nexora_token')

  async function fetchContacts() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/v1/integrations/hubspot/contacts', {
        headers: { Authorization: 'Bearer ' + token() },
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const list = Array.isArray(data) ? data : []
      setContacts(list)
      alert(`Synced ${list.length} contact${list.length === 1 ? '' : 's'} from HubSpot`)
    } catch (err: any) {
      setError(err.message || 'Failed to load contacts')
      alert('Refresh failed: ' + (err.message || 'Unknown error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchContacts() }, [])

  const owners = useMemo(() => {
    const set = new Set<string>()
    for (const c of contacts) {
      const o = c.properties.hubspot_owner_id
      if (o) set.add(o)
    }
    return Array.from(set)
  }, [contacts])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    return contacts.filter((c) => {
      const p = c.properties
      if (ownerFilter !== 'all' && p.hubspot_owner_id !== ownerFilter) return false
      if (stageFilter !== 'all') {
        const s = stageFor(p.lifecyclestage, overrides[c.id])
        if (s !== stageFilter) return false
      }
      if (!q) return true
      return (
        fullName(c).toLowerCase().includes(q) ||
        (p.company || '').toLowerCase().includes(q) ||
        (p.email || '').toLowerCase().includes(q) ||
        (p.jobtitle || '').toLowerCase().includes(q)
      )
    })
  }, [contacts, search, stageFilter, ownerFilter, overrides])

  const grouped = useMemo(() => {
    const g: Record<string, HubSpotContact[]> = {}
    for (const def of STAGES) g[def.key] = []
    for (const c of filtered) {
      const stage = stageFor(c.properties.lifecyclestage, overrides[c.id])
      g[stage].push(c)
    }
    return g
  }, [filtered, overrides])

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id))
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null)
    const { active, over } = event
    if (!over) return
    const contactId = String(active.id)
    const newStage = String(over.id)
    if (!STAGES.some((s) => s.key === newStage)) return
    const currentStage = stageFor(
      contacts.find((c) => c.id === contactId)?.properties.lifecyclestage,
      overrides[contactId]
    )
    if (currentStage === newStage) return
    const next = { ...overrides, [contactId]: newStage }
    setOverrides(next)
    saveOverrides(next)
  }

  const totalContacts = contacts.length
  const activeContact = activeId ? contacts.find((c) => c.id === activeId) : null

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col bg-background">
      <div className="mb-6 flex items-start justify-between shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">Sales Pipeline</h2>
          <p className="text-sm text-muted">
            {loading ? 'Loading...' : `${totalContacts} contact${totalContacts === 1 ? '' : 's'} synced from HubSpot`}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchContacts}
            disabled={loading}
            className="bg-background border border-border text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2 hover:bg-panelHover transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <Link
            to="/integrations"
            className="bg-background border border-border text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2 hover:bg-panelHover transition-colors"
          >
            <ExternalLink className="w-4 h-4" /> Manage HubSpot
          </Link>
        </div>
      </div>

      <div className="mb-4 shrink-0 flex flex-wrap gap-3 items-center">
        <div className="relative max-w-md flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, company, email..."
            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
          />
        </div>
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
        >
          <option value="all">All stages</option>
          {STAGES.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <select
          value={ownerFilter}
          onChange={(e) => setOwnerFilter(e.target.value)}
          className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
        >
          <option value="all">All owners</option>
          {owners.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mb-4 bg-danger/10 border border-danger/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-danger shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-danger font-medium mb-1">Failed to load HubSpot contacts</p>
            <p className="text-xs text-danger/80 mb-3">{error}</p>
            <div className="flex gap-2">
              <button
                onClick={fetchContacts}
                className="text-xs bg-danger/20 text-danger px-3 py-1.5 rounded hover:bg-danger/30 transition-colors"
              >
                Retry
              </button>
              <Link
                to="/integrations"
                className="text-xs bg-background border border-border text-white px-3 py-1.5 rounded hover:bg-panelHover transition-colors"
              >
                Check Integrations
              </Link>
            </div>
          </div>
        </div>
      )}

      {loading && contacts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-6 h-6 text-accent animate-spin mx-auto mb-2" />
            <p className="text-sm text-muted">Loading contacts from HubSpot...</p>
          </div>
        </div>
      ) : !loading && contacts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 bg-background border border-border rounded-xl flex items-center justify-center mx-auto mb-4">
              <Building2 className="w-8 h-8 text-muted" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No contacts yet</h3>
            <p className="text-sm text-muted mb-4">
              HubSpot is connected but has no contacts, or the connection needs to be refreshed.
            </p>
            <div className="flex gap-2 justify-center">
              <Link
                to="/integrations"
                className="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-accentHover"
              >
                Manage HubSpot
              </Link>
              <button
                onClick={fetchContacts}
                className="bg-background border border-border text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-panelHover"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      ) : (
        <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <div className="flex-1 overflow-x-auto overflow-y-hidden">
            <div className="flex gap-4 h-full min-w-max">
              {STAGES.map((stage) => (
                <DroppableColumn
                  key={stage.key}
                  stage={stage}
                  items={grouped[stage.key] || []}
                  activeId={activeId}
                />
              ))}
            </div>
          </div>
          <DragOverlay>
            {activeContact ? (
              <div className="bg-background border border-accent rounded-lg p-3 w-72 opacity-90">
                <p className="text-sm font-medium text-white truncate">{fullName(activeContact)}</p>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  )
}
