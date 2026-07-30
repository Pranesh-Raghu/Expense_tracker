import { useAuth } from '@/auth/useAuth'
import { Badge } from '@/components/ui/Badge'
import { ThemeToggle } from '@/components/ThemeToggle'
import { AccountMenu } from './AccountMenu'

export function TopBar({ onOpenNav }: { onOpenNav: () => void }) {
  const { kind } = useAuth()

  return (
    <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onOpenNav}
          aria-label="Open navigation"
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 md:hidden"
        >
          <svg viewBox="0 0 24 24" width={20} height={20} fill="none" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span className="text-sm font-semibold">
          <span className="text-brand-600 dark:text-brand-500">E</span>xpense{' '}
          <span className="text-brand-600 dark:text-brand-500">T</span>racker
        </span>
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        {kind === 'apikey' && <Badge tone="brand" className="hidden sm:inline-flex">API key session</Badge>}
        <ThemeToggle />
        <AccountMenu />
      </div>
    </header>
  )
}
