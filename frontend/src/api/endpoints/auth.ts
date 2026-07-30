import { apiFetch } from '../client'
import type {
  ApiKeyCreateResponse,
  ApiKeyInfo,
  Me,
  SessionInfo,
  Token,
  WebhookCreateResponse,
  WebhookInfo,
} from '../types'

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

// Admin-only, enforced server-side. The signing secret is shown once, in
// the create response - it's needed to verify the HMAC signature on each
// delivery, and isn't retrievable again after this.
export function createWebhook(url: string, events: string[]): Promise<WebhookCreateResponse> {
  return apiFetch<WebhookCreateResponse>('/auth/webhooks', { method: 'POST', body: { url, events } })
}

export function listWebhooks(): Promise<WebhookInfo[]> {
  return apiFetch<WebhookInfo[]>('/auth/webhooks')
}

export function deleteWebhook(id: number): Promise<void> {
  return apiFetch<void>(`/auth/webhooks/${id}`, { method: 'DELETE' })
}
