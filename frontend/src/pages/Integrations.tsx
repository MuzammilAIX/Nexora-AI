import { useState, useEffect } from 'react'
import { Plug, CheckCircle2, XCircle, Mail, Database, Loader2 } from 'lucide-react'

export function Integrations() {
  const [integrations, setIntegrations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState<string | null>(null)
  const [hubspotToken, setHubspotToken] = useState('')

  const token = localStorage.getItem('nexora_token')
  const headers = { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }

  const fetchIntegrations = async () => {
    try {
      const res = await fetch('/api/v1/integrations', { headers })
      const data = await res.json()
      setIntegrations(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchIntegrations() }, [])

  const isConnected = (provider: string) => integrations.some(i => i.provider === provider && i.status === 'connected')

  const handleGmailConnect = async () => {
    setConnecting('gmail')
    try {
      const res = await fetch('/api/v1/integrations/gmail/connect', { headers })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Request failed')
      }
      const data = await res.json()
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      } else {
        throw new Error('No authorization_url returned')
      }
    } catch (err: any) {
      alert('Failed to start Gmail OAuth: ' + (err?.message || err))
    } finally {
      setConnecting(null)
    }
  }

  const handleHubSpotConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!hubspotToken) return
    setConnecting('hubspot')
    try {
      const res = await fetch('/api/v1/integrations/hubspot/connect', {
        method: 'POST',
        headers,
        body: JSON.stringify({ access_token: hubspotToken })
      })
      if (!res.ok) throw new Error('Invalid HubSpot token')
      setHubspotToken('')
      fetchIntegrations()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setConnecting(null)
    }
  }

  const handleDisconnect = async (provider: string) => {
    if (!confirm(`Disconnect ${provider}?`)) return
    try {
      await fetch(`/api/v1/integrations/${provider}/disconnect`, { method: 'DELETE', headers })
      fetchIntegrations()
    } catch (err) {
      alert('Failed to disconnect')
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-white mb-1">Integrations</h2>
      <p className="text-sm text-muted mb-8">Connect external services to power your agents.</p>

      <div className="grid gap-6">
        {/* Gmail Integration Card */}
        <div className="bg-background border border-border rounded-xl p-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-red-500/10 flex items-center justify-center">
              <Mail className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Gmail</h3>
              <p className="text-sm text-muted">Read and send emails on your behalf.</p>
            </div>
          </div>
          <div>
            {isConnected('gmail') ? (
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-2 text-sm text-success"><CheckCircle2 className="w-4 h-4" /> Connected</span>
                <button onClick={() => handleDisconnect('gmail')} className="text-sm text-danger hover:underline">Disconnect</button>
              </div>
            ) : (
              <button onClick={handleGmailConnect} disabled={connecting === 'gmail'} className="bg-background text-white px-4 py-2 rounded-lg font-medium hover:bg-panelHover flex items-center gap-2">
                {connecting === 'gmail' ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Connect Gmail
              </button>
            )}
          </div>
        </div>

        {/* HubSpot Integration Card */}
        <div className="bg-background border border-border rounded-xl p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <Database className="w-6 h-6 text-orange-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">HubSpot</h3>
                <p className="text-sm text-muted">Sync contacts, leads, and create CRM tasks.</p>
              </div>
            </div>
            <div>
              {isConnected('hubspot') ? (
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-2 text-sm text-success"><CheckCircle2 className="w-4 h-4" /> Connected</span>
                  <button onClick={() => handleDisconnect('hubspot')} className="text-sm text-danger hover:underline">Disconnect</button>
                </div>
              ) : (
                <span className="flex items-center gap-2 text-sm text-warning"><XCircle className="w-4 h-4" /> Not connected</span>
              )}
            </div>
          </div>
          
          {!isConnected('hubspot') && (
            <form onSubmit={handleHubSpotConnect} className="flex gap-2 mt-2">
              <input
                type="text"
                placeholder="Paste Private App Access Token (pat-na...)"
                value={hubspotToken}
                onChange={(e) => setHubspotToken(e.target.value)}
                className="flex-1 bg-background border border-border rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
              />
              <button type="submit" disabled={connecting === 'hubspot' || !hubspotToken} className="bg-accent text-white px-4 py-2 rounded-lg font-medium hover:bg-accentHover disabled:opacity-50">
                Save Token
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
