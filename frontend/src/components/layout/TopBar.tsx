import { useAuth } from '@/auth/useAuth'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

export function TopBar() {
  const { user, kind, logout } = useAuth()

  return (
    <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
      <span className="text-sm font-semibold">Expense Tracker</span>
      <div className="flex items-center gap-3">
        {kind === 'apikey' && <Badge tone="brand">API key session</Badge>}
        {user && <span className="text-sm text-slate-600 dark:text-slate-300">{user.username}</span>}
        <Button variant="secondary" onClick={logout}>
          Log out
        </Button>
      </div>
    </header>
  )
}
