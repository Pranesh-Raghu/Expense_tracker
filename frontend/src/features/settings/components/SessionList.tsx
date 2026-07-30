import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { Badge } from '@/components/ui/Badge'
import { ApiError } from '@/api/errors'
import type { SessionInfo } from '@/api/types'
import { formatDateTime } from '@/lib/format'
import { parseUserAgent } from '@/lib/userAgent'
import { DeviceIcon } from './DeviceIcon'

// Matches oauth/service.py's WEB_SESSION_CLIENT_ID - password/Google/
// passwordless logins are recorded under this fixed client_id so they
// share the same sessions list/revoke UI as real OAuth-client logins.
function clientLabel(clientId: string): string {
  return clientId === 'expense-tracker-web' ? 'This app (web)' : clientId
}

interface SessionListProps {
  sessions: SessionInfo[] | undefined
  isLoading: boolean
  isError: boolean
  error: unknown
  onRevoke: (sessionId: string) => void
  isRevoking: boolean
  revokeError?: unknown
  emptyDescription?: string
}

export function SessionList({
  sessions,
  isLoading,
  isError,
  error,
  onRevoke,
  isRevoking,
  revokeError,
  emptyDescription,
}: SessionListProps) {
  if (isLoading) return <Spinner />
  if (isError) return <ErrorState message={error instanceof ApiError ? error.detail : 'Failed to load sessions'} />
  if (!sessions || sessions.length === 0) {
    return <EmptyState title="No active sessions" description={emptyDescription} />
  }

  return (
    <div className="space-y-3">
      {sessions.map((session) => {
        const { browser, os, deviceType } = parseUserAgent(session.user_agent)
        return (
          <Card key={session.session_id} className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-slate-400">
                <DeviceIcon deviceType={deviceType} />
              </div>
              <div>
                <p className="text-sm font-medium">
                  {browser} on {os}
                </p>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                  <Badge>{clientLabel(session.client_id)}</Badge>
                  {session.city && <span>{session.city}</span>}
                  {session.ip_address && <span>{session.ip_address}</span>}
                </div>
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                  First seen {formatDateTime(session.created_at)} · Last used {formatDateTime(session.last_used_at)}
                </p>
                {session.user_agent && (
                  <p
                    className="mt-1 max-w-md truncate text-xs text-slate-400 dark:text-slate-500"
                    title={session.user_agent}
                  >
                    {session.user_agent}
                  </p>
                )}
              </div>
            </div>
            <Button variant="danger" disabled={isRevoking} onClick={() => onRevoke(session.session_id)}>
              Revoke
            </Button>
          </Card>
        )
      })}
      {revokeError ? (
        <ErrorState message={revokeError instanceof ApiError ? revokeError.detail : 'Failed to revoke session'} />
      ) : null}
    </div>
  )
}
