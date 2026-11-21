import { useState, useEffect } from 'react'
import { Search, Plus, Mail, Building } from 'lucide-react'

export function CRM() {
  const [contacts, setContacts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    async function fetchContacts() {
      try {
        const token = localStorage.getItem('nexora_token')
        const res = await fetch('/api/v1/integrations/hubspot/contacts', {
          headers: { 'Authorization': 'Bearer ' + token }
        })
        
        if (!res.ok) {
          if (res.status === 400 || res.status === 404) {
            throw new Error('HubSpot is not connected. Please connect it in the Integrations tab.')
          }
          throw new Error('Failed to fetch contacts')
        }
        
        const data = await res.json()
        setContacts(Array.isArray(data) ? data : [])
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchContacts()
  }, [])

  const filtered = contacts.filter(c => {
    const props = c.properties || {}
    const name = `${props.firstname || ''} ${props.lastname || ''}`.toLowerCase()
    const email = (props.email || '').toLowerCase()
    return name.includes(search.toLowerCase()) || email.includes(search.toLowerCase())
  })

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col bg-background">
      <div className="flex justify-between items-center mb-6 shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">Sales Pipeline</h2>
          <p className="text-sm text-muted">Manage deals and AI assistance</p>
        </div>
        <div className="flex gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              placeholder="Search contacts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-panel border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-white focus:outline-none focus:border-accent/50 w-64"
            />
          </div>
          <button className="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 hover:bg-accentHover transition-colors">
            <Plus className="w-4 h-4" /> Add Deal
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-4 h-full min-w-max pb-4">
          <div className="w-80 bg-panel border border-border rounded-xl flex flex-col">
            <div className="p-4 border-b border-border flex justify-between items-center bg-[#111827] rounded-t-xl">
              <h3 className="font-semibold text-white">HubSpot Leads</h3>
              <span className="bg-background text-muted text-xs px-2 py-0.5 rounded-full">{filtered.length}</span>
            </div>
            
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {loading ? (
                <div className="text-center text-muted text-sm py-8">Loading contacts...</div>
              ) : filtered.length === 0 ? (
                <div className="text-center text-muted text-sm py-8">No contacts found.</div>
              ) : (
                filtered.map((contact, i) => {
                  const props = contact.properties || {}
                  const firstname = props.firstname || ''
                  const lastname = props.lastname || ''
                  const email = props.email || ''
                  const company = props.company || ''
                  
                  return (
                    <div key={i} className="bg-background border border-border rounded-lg p-3 hover:border-accent/50 transition-colors cursor-pointer">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent text-xs font-bold">
                            {(firstname[0] || '') + (lastname[0] || '') || '?'}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{firstname} {lastname}</p>
                            <p className="text-xs text-muted flex items-center gap-1"><Building className="w-3 h-3" /> {company || 'No company'}</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted mt-2">
                        <Mail className="w-3 h-3" /> {email || 'No email'}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
          
          {['Qualified', 'Demo', 'Proposal', 'Negotiation', 'Closed'].map((col) => (
             <div key={col} className="w-80 bg-panel/50 border border-border rounded-xl flex flex-col opacity-50">
               <div className="p-4 border-b border-border flex justify-between items-center bg-[#111827]/50 rounded-t-xl">
                 <h3 className="font-semibold text-white">{col}</h3>
                 <span className="bg-background text-muted text-xs px-2 py-0.5 rounded-full">0</span>
               </div>
               <div className="flex-1 p-3">
                  <div className="border-2 border-dashed border-border rounded-lg h-24 flex items-center justify-center text-xs text-muted">
                    Drag here
                  </div>
               </div>
             </div>
          ))}
        </div>
      </div>
    </div>
  )
}
