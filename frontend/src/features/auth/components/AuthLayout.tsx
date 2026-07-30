import type { ReactNode } from 'react'
import { Card } from '@/components/ui/Card'
import { ThemeToggle } from '@/components/ThemeToggle'

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="relative flex h-full items-center justify-center p-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-sm">
        <h1 className="mb-4 text-lg font-semibold">{title}</h1>
        {children}
      </Card>
    </div>
  )
}
