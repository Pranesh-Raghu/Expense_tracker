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
  listeners.forEach((listener) => listener(cached))
}

export function clearToken(): void {
  cached = null
  localStorage.removeItem(STORAGE_KEY)
  listeners.forEach((listener) => listener(null))
}

export function subscribeToken(listener: (token: StoredToken | null) => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
