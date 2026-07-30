import type { ReactNode } from 'react'
import { Card } from '@/components/ui/Card'
import { ThemeToggle } from '@/components/ThemeToggle'
import { PennywiseIcon } from '@/components/ui/PennywiseIcon'

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="relative flex h-full items-center justify-center p-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-sm">
        <div className="mb-4 flex items-center gap-2">
          <PennywiseIcon size={28} />
          <h1 className="text-lg font-semibold">{title}</h1>
        </div>
        {children}
      </Card>
    </div>
  )
}
