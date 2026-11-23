// src/services/teamApi.ts
// Thin typed wrapper for the /api/v1/team and /api/v1/audit endpoints.
// Matches the existing inline-fetch pattern used across src/pages/*.tsx
// but centralizes token handling and error normalization.

const API_BASE = '/api/v1'

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export class AuthError extends ApiError {
  constructor(body: unknown) {
    super(401, 'Not authenticated', body)
    this.name = 'AuthError'
  }
}

export class ConflictError extends ApiError {
  constructor(body: unknown) {
    super(409, 'Conflict', body)
    this.name = 'ConflictError'
  }
}

function getToken(): string | null {
  return localStorage.getItem('nexora_token')
}

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<T> {
  const token = getToken()
  if (!token) {
    throw new AuthError({ detail: 'Missing token' })
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (res.status === 401) {
    // Clear stale token so the next render is forced to the login page.
    localStorage.removeItem('nexora_token')
    throw new AuthError(await safeJson(res))
  }
  if (res.status === 409) {
    throw new ConflictError(await safeJson(res))
  }
  if (!res.ok) {
    const errBody = await safeJson(res)
    const detail =
      (errBody && typeof errBody === 'object' && 'detail' in errBody
        ? String((errBody as { detail: unknown }).detail)
        : res.statusText) || `HTTP ${res.status}`
    throw new ApiError(res.status, detail, errBody)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

async function safeJson(res: Response): Promise<unknown> {
  try {
    return await res.json()
  } catch {
    return null
  }
}

// ---------- Types ----------

export interface TeamMember {
  id: string
  email: string
  full_name: string | null
  role_id: string | null
  role_name: string | null
  status: 'active' | 'invited' | 'suspended' | string
  last_login_at: string | null
  created_at: string
}

export interface TeamRole {
  id: string
  name: string
  description: string | null
  is_system: boolean
  permissions: Record<string, boolean>
}

export interface Invitation {
  id: string
  email: string
  role_id: string
  role_name: string | null
  status: 'pending' | 'accepted' | 'revoked' | 'expired' | string
  expires_at: string
  created_at: string
  invited_by: string | null
  debug_token?: string | null
}

export interface InviteResponse {
  invitation_id: string
  email: string
  role_id: string
  expires_at: string
  debug_token?: string | null
}

// ---------- Endpoints ----------

export function listMembers(): Promise<TeamMember[]> {
  return request<TeamMember[]>('GET', '/team/members')
}

export function listRoles(): Promise<TeamRole[]> {
  return request<TeamRole[]>('GET', '/team/roles')
}

export function listInvitations(): Promise<Invitation[]> {
  return request<Invitation[]>('GET', '/team/invitations')
}

export function inviteMember(email: string, role_id: string): Promise<InviteResponse> {
  return request<InviteResponse>('POST', '/team/invite', { email, role_id })
}

export function changeRole(userId: string, role_id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('PATCH', `/team/members/${userId}/role`, { role_id })
}

export function suspendMember(userId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('PATCH', `/team/members/${userId}/suspend`)
}

export function reactivateMember(userId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('PATCH', `/team/members/${userId}/reactivate`)
}

export function removeMember(userId: string): Promise<void> {
  return request<void>('DELETE', `/team/members/${userId}`)
}

export function revokeInvitation(invitationId: string): Promise<void> {
  return request<void>('DELETE', `/team/invitations/${invitationId}`)
}
