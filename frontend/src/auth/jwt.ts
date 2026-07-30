// Decodes the `exp` claim for client-side expiry timers only - this is not
// signature verification, and must never be treated as one. The server is
// always the real authority on whether a token is valid.
export function decodeExpMs(jwt: string): number | null {
  const parts = jwt.split('.')
  if (parts.length !== 3) return null

  try {
    const payloadJson = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(payloadJson) as { exp?: number }
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}
