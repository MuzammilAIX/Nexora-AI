import { useEffect, useState } from 'react'
import { Mail, Clock, AlertCircle, Trash2, RefreshCw } from 'lucide-react'
import {
  listInvitations,
  revokeInvitation,
  type Invitation,
  ApiError,
  AuthError,
} from '../../services/teamApi'

export function InvitationsTab() {
  const [invites, setInvites] = useState<Invitation[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = () => {
    setError(null)
    listInvitations()
      .then(setInvites)
      .catch((e) => {
        if (e instanceof AuthError) { setError('Session expired. Please log in again.'); return }
        if (e instanceof ApiError) { setError(`Failed to load invitations: ${e.message}`); return }
        setError('Failed to load invitations.')
      })
  }

  useEffect(() => { load() }, [])

  const onRevoke = async (id: string) => {
    if (!confirm('Revoke this invitation? The invite link will stop working.')) return
    setBusyId(id)
    try {
      await revokeInvitation(id)
      setInvites((prev) => (prev ? prev.filter((i) => i.id !== id) : prev))
    } catch (e) {
      if (e instanceof AuthError) { setError('Session expired.'); return }
      if (e instanceof ApiError) { setError(`Revoke failed: ${e.message}`); return }
      setError('Revoke failed.')
    } finally {
      setBusyId(null)
    }
  }

  if (error) {
    return (
      <div className="bg-background border border-border rounded-xl p-8 text-center">
        <AlertCircle className="w-12 h-12 text-danger mx-auto mb-4 opacity-70" />
        <p className="text-danger text-sm mb-4">{error}</p>
        <button
          onClick={load}
          className="text-sm text-accent hover:text-white transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (invites === null) {
    return (
      <div className="bg-background border border-border rounded-xl p-8 text-center">
        <RefreshCw className="w-8 h-8 text-muted mx-auto mb-3 opacity-50 animate-spin" />
        <p className="text-muted text-sm">Loading invitations…</p>
      </div>
    )
  }

  if (invites.length === 0) {
    return (
      <div className="bg-background border border-border rounded-xl p-8 text-center">
        <Mail className="w-12 h-12 text-muted mx-auto mb-4 opacity-50" />
        <p className="text-muted text-sm">No pending invitations.</p>
        <p className="text-xs text-muted/60 mt-1">
          Invite a teammate from the Members tab.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-background border border-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Email</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Role</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Status</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Expires</th>
              <th className="text-right px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {invites.map((inv) => {
              const expires = new Date(inv.expires_at)
              const daysLeft = Math.max(0, Math.ceil((expires.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
              return (
                <tr key={inv.id} className="border-b border-border last:border-b-0">
                  <td className="px-5 py-3 text-white">{inv.email}</td>
                  <td className="px-5 py-3 text-muted capitalize">{inv.role_name ?? '—'}</td>
                  <td className="px-5 py-3">
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-warning/10 text-warning border border-warning/20">
                      <Clock className="w-3 h-3" />
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-muted text-xs">
                    {daysLeft > 0 ? `${daysLeft} day${daysLeft === 1 ? '' : 's'} left` : 'expired'}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => onRevoke(inv.id)}
                      disabled={busyId === inv.id}
                      className="inline-flex items-center gap-1 text-xs text-muted hover:text-danger transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      {busyId === inv.id ? 'Revoking…' : 'Revoke'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
