import { apiFetch } from '../client'
import type { ApiKeyCreateResponse, ApiKeyInfo, Me, Token } from '../types'

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
