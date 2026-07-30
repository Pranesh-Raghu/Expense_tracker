import { useState, type ReactNode } from 'react'
import { SessionExpiryBanner } from '@/auth/SessionExpiryBanner'
import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

export function AppShell({ children }: { children: ReactNode }) {
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="flex h-full flex-col">
      <SessionExpiryBanner />
      <TopBar onOpenNav={() => setNavOpen(true)} />
      <div className="flex min-h-0 flex-1">
        <SideNav open={navOpen} onClose={() => setNavOpen(false)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  )
}
