import { cn } from '@/lib/cn'

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        'h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600',
        className,
      )}
    />
  )
}
