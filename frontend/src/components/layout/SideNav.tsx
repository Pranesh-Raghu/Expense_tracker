import { NavLink } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { cn } from '@/lib/cn'

const LINK_CLASS = ({ isActive }: { isActive: boolean }) =>
  cn(
    'block rounded-md px-3 py-1.5 text-sm font-medium',
    isActive
      ? 'bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-100'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
  )

export function SideNav() {
  const { isAdmin } = useAuth()

  return (
    <nav className="flex w-56 shrink-0 flex-col gap-1 border-r border-slate-200 p-4 dark:border-slate-800">
      <NavLink to="/" end className={LINK_CLASS}>
        Dashboard
      </NavLink>
      <NavLink to="/reports" className={LINK_CLASS}>
        Reports
      </NavLink>
      <NavLink to="/settings/api-keys" className={LINK_CLASS}>
        API keys
      </NavLink>

      {isAdmin && (
        <>
          <p className="mt-4 px-3 text-xs font-semibold uppercase text-slate-400">Admin</p>
          <NavLink to="/admin/oauth-clients" className={LINK_CLASS}>
            OAuth clients
          </NavLink>
          <NavLink to="/admin/tokens" className={LINK_CLASS}>
            Token tools
          </NavLink>
          <NavLink to="/admin/users" className={LINK_CLASS}>
            Users
          </NavLink>
        </>
      )}
    </nav>
  )
}
