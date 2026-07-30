import type { ReactNode } from 'react'
import { SessionExpiryBanner } from '@/auth/SessionExpiryBanner'
import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full flex-col">
      <SessionExpiryBanner />
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <SideNav />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
