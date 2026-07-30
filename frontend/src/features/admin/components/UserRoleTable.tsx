import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { Badge } from '@/components/ui/Badge'
import { Avatar } from '@/components/ui/Avatar'
import { useAuth } from '@/auth/useAuth'
import * as usersApi from '@/api/endpoints/users'
import * as authApi from '@/api/endpoints/auth'
import { SessionList } from '@/features/settings/components/SessionList'
import type { User } from '@/api/types'

const USERS_QUERY_KEY = ['users']

function UserCard({ user, isMe }: { user: User; isMe: boolean }) {
  const queryClient = useQueryClient()
  const sessionsKey = ['auth', 'admin-sessions', user.id]

  const {
    data: sessions,
    isLoading: sessionsLoading,
    isError: sessionsError,
    error: sessionsErrorObj,
  } = useQuery({ queryKey: sessionsKey, queryFn: () => authApi.listUserSessions(user.id) })

  const grant = useMutation({
    mutationFn: () => authApi.grantAdmin(user.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY }),
  })
  const revoke = useMutation({
    mutationFn: () => authApi.revokeAdmin(user.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY }),
  })
  const revokeSession = useMutation({
    mutationFn: (sessionId: string) => authApi.revokeUserSession(user.id, sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sessionsKey }),
  })

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Avatar username={user.username} avatarUrl={user.avatar_url} size={40} />
          <div>
            <p className="text-sm font-semibold">
              {user.username}
              {isMe && (
                <Badge className="ml-2" tone="brand">
                  You
                </Badge>
              )}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="secondary" disabled={grant.isPending} onClick={() => grant.mutate()}>
            Grant admin
          </Button>
          <Button
            variant="danger"
            disabled={revoke.isPending || isMe}
            title={isMe ? "You can't revoke your own admin access here" : undefined}
            onClick={() => revoke.mutate()}
          >
            Revoke admin
          </Button>
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase text-slate-400">Sessions & devices</h3>
        <SessionList
          sessions={sessions}
          isLoading={sessionsLoading}
          isError={sessionsError}
          error={sessionsErrorObj}
          onRevoke={(sessionId) => revokeSession.mutate(sessionId)}
          isRevoking={revokeSession.isPending}
          revokeError={revokeSession.error}
          emptyDescription="This user has no active OAuth sessions."
        />
      </div>
    </Card>
  )
}

export function UserRoleTable() {
  const { user: me } = useAuth()
  const { data: users, isLoading } = useQuery({ queryKey: USERS_QUERY_KEY, queryFn: usersApi.listUsers })

  if (isLoading) return <Spinner />
  if (!users || users.length === 0) return <EmptyState title="No users found" />

  return (
    <div className="space-y-4">
      {users.map((user) => (
        <UserCard key={user.id} user={user} isMe={user.id === me?.id} />
      ))}
    </div>
  )
}
