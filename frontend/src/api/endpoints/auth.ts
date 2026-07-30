import { apiFetch } from '../client'
import type { ApiKeyCreateResponse, ApiKeyInfo, Me, SessionInfo, Token } from '../types'

export function login(username: string, password: string): Promise<Token> {
  return apiFetch<Token>('/auth/token', { method: 'POST', form: { username, password } })
}

export function getMe(): Promise<Me> {
  return apiFetch<Me>('/auth/me')
}

export function createApiKey(name?: string): Promise<ApiKeyCreateResponse> {
  return apiFetch<ApiKeyCreateResponse>('/auth/api-keys', { method: 'POST', body: { name } })
}

export function listApiKeys(): Promise<ApiKeyInfo[]> {
  return apiFetch<ApiKeyInfo[]>('/auth/api-keys')
}

export function revokeApiKey(keyId: string): Promise<void> {
  return apiFetch<void>(`/auth/api-keys/${keyId}`, { method: 'DELETE' })
}

export function grantAdmin(targetUserId: number): Promise<void> {
  return apiFetch<void>(`/auth/admin/${targetUserId}`, { method: 'POST' })
}

export function revokeAdmin(targetUserId: number): Promise<void> {
  return apiFetch<void>(`/auth/admin/${targetUserId}`, { method: 'DELETE' })
}

// One row per issued OAuth refresh token - sessions from the plain
// password-login flow (POST /auth/token) never appear here, since that
// flow issues only a stateless JWT with no refresh token/session row.
export function listSessions(): Promise<SessionInfo[]> {
  return apiFetch<SessionInfo[]>('/auth/sessions')
}

export function revokeSession(sessionId: string): Promise<void> {
  return apiFetch<void>(`/auth/sessions/${sessionId}`, { method: 'DELETE' })
}

// Admin-only: view/revoke any user's sessions, not just your own.
export function listUserSessions(targetUserId: number): Promise<SessionInfo[]> {
  return apiFetch<SessionInfo[]>(`/auth/admin/${targetUserId}/sessions`)
}

export function revokeUserSession(targetUserId: number, sessionId: string): Promise<void> {
  return apiFetch<void>(`/auth/admin/${targetUserId}/sessions/${sessionId}`, { method: 'DELETE' })
}
