import { apiFetch } from '../client'
import type { User } from '../types'

export function signup(username: string, password: string): Promise<User> {
  return apiFetch<User>('/users/', { method: 'POST', body: { username, password } })
}

// Requires auth; used to populate the "share with" user picker and the
// admin user table. Individual reads/writes beyond this list are gated
// server-side to self-or-admin.
export function listUsers(): Promise<User[]> {
  return apiFetch<User[]>('/users/')
}
