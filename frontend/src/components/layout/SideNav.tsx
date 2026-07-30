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

interface SideNavProps {
  // Below md, the nav renders as an off-canvas drawer instead of a static
  // column - open/onClose let AppShell's hamburger button and the
  // backdrop control it.
  open: boolean
  onClose: () => void
}

function NavLinks({ onNavigate }: { onNavigate: () => void }) {
  const { isAdmin } = useAuth()

  return (
    <>
      <NavLink to="/" end className={LINK_CLASS} onClick={onNavigate}>
        Dashboard
      </NavLink>
      <NavLink to="/reports" className={LINK_CLASS} onClick={onNavigate}>
        Reports
      </NavLink>
      <NavLink to="/settings/profile" className={LINK_CLASS} onClick={onNavigate}>
        Profile
      </NavLink>
      <NavLink to="/settings/sessions" className={LINK_CLASS} onClick={onNavigate}>
        Sessions & devices
      </NavLink>
      <NavLink to="/settings/api-keys" className={LINK_CLASS} onClick={onNavigate}>
        API keys
      </NavLink>

      {isAdmin && (
        <>
          <p className="mt-4 px-3 text-xs font-semibold uppercase text-slate-400">Admin</p>
          <NavLink to="/admin/oauth-clients" className={LINK_CLASS} onClick={onNavigate}>
            OAuth clients
          </NavLink>
          <NavLink to="/admin/tokens" className={LINK_CLASS} onClick={onNavigate}>
            Token tools
          </NavLink>
          <NavLink to="/admin/users" className={LINK_CLASS} onClick={onNavigate}>
            Users
          </NavLink>
        </>
      )}
    </>
  )
}

export function SideNav({ open, onClose }: SideNavProps) {
  return (
    <>
      {/* md+: static column, always visible */}
      <nav className="hidden w-56 shrink-0 flex-col gap-1 border-r border-slate-200 p-4 dark:border-slate-800 md:flex">
        <NavLinks onNavigate={() => {}} />
      </nav>

      {/* below md: off-canvas drawer over a backdrop */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
          <nav className="absolute inset-y-0 left-0 flex w-64 flex-col gap-1 overflow-y-auto bg-white p-4 shadow-xl dark:bg-slate-900">
            <NavLinks onNavigate={onClose} />
          </nav>
        </div>
      )}
    </>
  )
}
