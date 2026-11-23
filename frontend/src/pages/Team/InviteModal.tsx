import { useEffect, useState } from 'react'
import { X, Mail, AlertCircle, CheckCircle2 } from 'lucide-react'
import {
  listRoles,
  inviteMember,
  type TeamRole,
  ApiError,
  AuthError,
  ConflictError,
} from '../../services/teamApi'

interface Props {
  open: boolean
  onClose: () => void
  onInvited: () => void
}

export function InviteModal({ open, onClose, onInvited }: Props) {
  const [roles, setRoles] = useState<TeamRole[]>([])
  const [email, setEmail] = useState('')
  const [roleId, setRoleId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setSuccess(null)
    listRoles()
      .then((r) => {
        setRoles(r)
        const defaultRole = r.find((x) => x.name === 'viewer') ?? r[0]
        if (defaultRole) setRoleId(defaultRole.id)
      })
      .catch(() => setError('Could not load roles.'))
  }, [open])

  if (!open) return null

  const valid = email.trim().length > 3 && email.includes('@') && roleId.length > 0

  const onSubmit = async () => {
    if (!valid || busy) return
    setBusy(true)
    setError(null)
    setSuccess(null)
    try {
      const resp = await inviteMember(email.trim(), roleId)
      setSuccess(`Invitation sent to ${resp.email}`)
      setEmail('')
      onInvited()
      setTimeout(onClose, 1200)
    } catch (e) {
      if (e instanceof ConflictError) {
        setError('This email already has a pending invitation or is already a member.')
      } else if (e instanceof AuthError) {
        setError('Session expired. Please log in again.')
      } else if (e instanceof ApiError) {
        setError(e.message)
      } else {
        setError('Invitation failed. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-background border border-border rounded-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
              <Mail className="w-4 h-4 text-accent" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-sm">Invite team member</h2>
              <p className="text-xs text-muted">They'll receive an email with a signup link.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={busy}
            className="p-1.5 rounded-md hover:bg-backgroundHover text-muted hover:text-white transition-colors disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">Email address</label>
            <input
              type="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@company.com"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:border-accent/50"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">Role</label>
            <select
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/50"
            >
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} — {Object.values(r.permissions || {}).filter(Boolean).length} perms
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="flex items-start gap-2 text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-start gap-2 text-xs text-success bg-success/10 border border-success/20 rounded-lg p-3">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 p-5 border-t border-border">
          <button
            onClick={onClose}
            disabled={busy}
            className="px-3 py-2 text-sm text-muted hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={!valid || busy}
            className="px-4 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? 'Sending…' : 'Send invitation'}
          </button>
        </div>
      </div>
    </div>
  )
}
