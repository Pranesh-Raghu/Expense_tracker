import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { Badge } from '@/components/ui/Badge'
import { useAuth } from '@/auth/useAuth'
import * as usersApi from '@/api/endpoints/users'
import * as authApi from '@/api/endpoints/auth'

const USERS_QUERY_KEY = ['users']

export function UserRoleTable() {
  const queryClient = useQueryClient()
  const { user: me } = useAuth()
  const { data: users, isLoading } = useQuery({ queryKey: USERS_QUERY_KEY, queryFn: usersApi.listUsers })

  const grant = useMutation({
    mutationFn: (id: number) => authApi.grantAdmin(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY }),
  })
  const revoke = useMutation({
    mutationFn: (id: number) => authApi.revokeAdmin(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY }),
  })

  if (isLoading) return <Spinner />
  if (!users || users.length === 0) return <EmptyState title="No users found" />

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase text-slate-400 dark:border-slate-800">
          <th className="py-2 pr-4 font-medium">Username</th>
          <th className="py-2 font-medium" />
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
        {users.map((user) => (
          <tr key={user.id}>
            <td className="py-2 pr-4">
              {user.username}
              {user.id === me?.id && (
                <Badge className="ml-2" tone="brand">
                  You
                </Badge>
              )}
            </td>
            <td className="py-2 text-right">
              <Button
                variant="secondary"
                disabled={grant.isPending}
                onClick={() => grant.mutate(user.id)}
                className="mr-2"
              >
                Grant admin
              </Button>
              <Button
                variant="danger"
                disabled={revoke.isPending || user.id === me?.id}
                title={user.id === me?.id ? "You can't revoke your own admin access here" : undefined}
                onClick={() => revoke.mutate(user.id)}
              >
                Revoke admin
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
