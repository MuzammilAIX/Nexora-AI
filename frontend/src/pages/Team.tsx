import { useEffect, useState } from 'react'
import { Users, UserCheck, Mail, Shield, Plus, AlertCircle, RefreshCw } from 'lucide-react'
import {
  listMembers,
  listRoles,
  listInvitations,
  type TeamMember,
  type TeamRole,
  type Invitation,
  ApiError,
  AuthError,
} from '../services/teamApi'
import { RolesTab } from './Team/RolesTab'
import { InvitationsTab } from './Team/InvitationsTab'
import { InviteModal } from './Team/InviteModal'

type TabKey = 'members' | 'roles' | 'invitations'

export function Team() {
  const [tab, setTab] = useState<TabKey>('members')
  const [members, setMembers] = useState<TeamMember[] | null>(null)
  const [roles, setRoles] = useState<TeamRole[] | null>(null)
  const [invites, setInvites] = useState<Invitation[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [inviteOpen, setInviteOpen] = useState(false)

  const loadAll = () => {
    setError(null)
    Promise.all([listMembers(), listRoles(), listInvitations()])
      .then(([m, r, i]) => {
        setMembers(m)
        setRoles(r)
        setInvites(i)
      })
      .catch((e) => {
        if (e instanceof AuthError) { setError('Session expired. Please log in again.'); return }
        if (e instanceof ApiError) { setError(`Failed to load team data: ${e.message}`); return }
        setError('Failed to load team data.')
      })
  }

  useEffect(() => { loadAll() }, [])

  // Reload invitations when a new one is sent (from modal), so the tab + KPI update.
  const handleInvited = () => {
    listInvitations().then(setInvites).catch(() => {})
    listMembers().then(setMembers).catch(() => {})
  }

  const kpis = [
    {
      label: 'Total Members',
      value: members?.length ?? '—',
      icon: Users,
      color: 'text-accent',
      bg: 'bg-accent/10 border-accent/20',
    },
    {
      label: 'Active',
      value: members?.filter((m) => m.status === 'active').length ?? '—',
      icon: UserCheck,
      color: 'text-success',
      bg: 'bg-success/10 border-success/20',
    },
    {
      label: 'Pending Invites',
      value: invites?.length ?? '—',
      icon: Mail,
      color: 'text-warning',
      bg: 'bg-warning/10 border-warning/20',
    },
    {
      label: 'Roles',
      value: roles?.length ?? '—',
      icon: Shield,
      color: 'text-white',
      bg: 'bg-panel/5 border-white/10',
    },
  ]

  return (
    <div className="p-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">Team & Permissions</h2>
          <p className="text-sm text-muted">
            Manage who has access to Nexora, what they can do, and what's pending.
          </p>
        </div>
        <button
          onClick={() => setInviteOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Invite member
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-sm text-danger bg-danger/10 border border-danger/20 rounded-xl p-4 mb-6">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div>{error}</div>
            <button onClick={loadAll} className="mt-2 text-xs text-accent hover:text-white transition-colors">
              Retry
            </button>
          </div>
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {kpis.map((k) => (
          <div key={k.label} className="bg-background border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted font-medium">{k.label}</span>
              <div className={`w-8 h-8 rounded-lg border flex items-center justify-center ${k.bg}`}>
                <k.icon className={`w-4 h-4 ${k.color}`} />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">{k.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-6">
          {(
            [
              { key: 'members', label: 'Members' },
              { key: 'roles', label: 'Roles & Permissions' },
              { key: 'invitations', label: `Invitations${invites ? ` (${invites.length})` : ''}` },
            ] as { key: TabKey; label: string }[]
          ).map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={
                'pb-3 text-sm font-medium border-b-2 transition-colors -mb-px ' +
                (tab === t.key
                  ? 'text-white border-accent'
                  : 'text-muted border-transparent hover:text-white')
              }
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'members' && (
        <MembersTable members={members} loading={members === null} onRefresh={loadAll} roles={roles} />
      )}
      {tab === 'roles' && <RolesTab />}
      {tab === 'invitations' && <InvitationsTab />}

      <InviteModal open={inviteOpen} onClose={() => setInviteOpen(false)} onInvited={handleInvited} />
    </div>
  )
}

function MembersTable({
  members,
  loading,
  onRefresh,
  roles,
}: {
  members: TeamMember[] | null
  loading: boolean
  onRefresh: () => void
  roles: TeamRole[] | null
}) {
  if (loading) {
    return (
      <div className="bg-background border border-border rounded-xl p-8 text-center">
        <RefreshCw className="w-8 h-8 text-muted mx-auto mb-3 opacity-50 animate-spin" />
        <p className="text-muted text-sm">Loading members…</p>
      </div>
    )
  }
  if (!members || members.length === 0) {
    return (
      <div className="bg-background border border-border rounded-xl p-8 text-center">
        <Users className="w-12 h-12 text-muted mx-auto mb-4 opacity-50" />
        <p className="text-muted text-sm">No members yet.</p>
      </div>
    )
  }

  const roleName = (id: string | null) => roles?.find((r) => r.id === id)?.name ?? '—'

  return (
    <div className="bg-background border border-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <h3 className="text-white font-semibold text-sm">Members</h3>
        <button
          onClick={onRefresh}
          className="text-xs text-muted hover:text-white transition-colors"
        >
          Refresh
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Member</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Role</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Status</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-muted uppercase tracking-wider">Last login</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-b border-border last:border-b-0">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-accent text-xs font-bold">
                      {(m.email[0] || '?').toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="text-white truncate">{m.full_name ?? m.email.split('@')[0]}</div>
                      <div className="text-xs text-muted truncate">{m.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span className="capitalize text-white">{roleName(m.role_id) ?? m.role_name ?? '—'}</span>
                </td>
                <td className="px-5 py-3">
                  <span
                    className={
                      'inline-flex items-center text-xs px-2 py-1 rounded-md border ' +
                      (m.status === 'active'
                        ? 'bg-success/10 text-success border-success/20'
                        : m.status === 'suspended'
                        ? 'bg-danger/10 text-danger border-danger/20'
                        : 'bg-warning/10 text-warning border-warning/20')
                    }
                  >
                    {m.status}
                  </span>
                </td>
                <td className="px-5 py-3 text-muted text-xs">
                  {m.last_login_at ? new Date(m.last_login_at).toLocaleString() : 'Never'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
