export type TokenKind = 'jwt' | 'apikey'

export interface StoredToken {
  token: string
  kind: TokenKind
}

const STORAGE_KEY = 'expense-tracker.auth'

let cached: StoredToken | null = readFromStorage()
const listeners = new Set<(token: StoredToken | null) => void>()

function readFromStorage(): StoredToken | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredToken
  } catch {
    return null
  }
}

// Keeps multiple tabs in sync: logging out in one tab logs out the others.
// The native `storage` event only ever fires in OTHER tabs, never the one
// that made the change - that's exactly what we want here, since the tab
// that calls setToken/clearToken already handles its own state update
// inline (see AuthProvider's login/logout). Also notifying listeners
// directly from setToken/clearToken (as this used to do) double-fired
// that handling for the owning tab and raced with it - e.g. logging out
// while a request was in flight could bounce back to "/login?reason=expired"
// right after the deliberate logout, since the redundant listener call
// re-ran refreshMe()/scheduleExpiryTimers() concurrently with logout's own.
window.addEventListener('storage', (event) => {
  if (event.key !== STORAGE_KEY) return
  cached = readFromStorage()
  listeners.forEach((listener) => listener(cached))
})

export function getToken(): StoredToken | null {
  return cached
}

export function setToken(next: StoredToken): void {
  cached = next
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}

export function clearToken(): void {
  cached = null
  localStorage.removeItem(STORAGE_KEY)
}

export function subscribeToken(listener: (token: StoredToken | null) => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
