// There's no server-side "list registered OAuth clients" endpoint, and the
// client_secret is shown exactly once in the /oauth/register response. This
// keeps a local, browser-only record of what THIS browser registered - it
// is not a substitute for a real client registry and never stores secrets.
export interface LocalClientRecord {
  client_id: string
  client_name?: string
  redirect_uris: string[]
  token_endpoint_auth_method: string
  issued_at: number
}

function storageKey(apiBaseUrl: string): string {
  return `expense-tracker.oauth-clients.${apiBaseUrl || 'default'}`
}

export function listLocalClients(apiBaseUrl: string): LocalClientRecord[] {
  const raw = localStorage.getItem(storageKey(apiBaseUrl))
  if (!raw) return []
  try {
    return JSON.parse(raw) as LocalClientRecord[]
  } catch {
    return []
  }
}

export function addLocalClient(apiBaseUrl: string, record: LocalClientRecord): void {
  const next = [record, ...listLocalClients(apiBaseUrl)]
  localStorage.setItem(storageKey(apiBaseUrl), JSON.stringify(next))
}

export function removeLocalClient(apiBaseUrl: string, clientId: string): void {
  const next = listLocalClients(apiBaseUrl).filter((c) => c.client_id !== clientId)
  localStorage.setItem(storageKey(apiBaseUrl), JSON.stringify(next))
}
