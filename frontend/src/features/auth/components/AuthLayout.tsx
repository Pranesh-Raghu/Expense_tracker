import type { ReactNode } from 'react'
import { Card } from '@/components/ui/Card'

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-4 text-lg font-semibold">{title}</h1>
        {children}
      </Card>
    </div>
  )
}
