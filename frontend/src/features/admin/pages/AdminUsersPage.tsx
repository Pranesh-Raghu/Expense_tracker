import { UserRoleTable } from '../components/UserRoleTable'

export function AdminUsersPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Users</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400">Grant or revoke organization admin access.</p>
      <UserRoleTable />
    </div>
  )
}
