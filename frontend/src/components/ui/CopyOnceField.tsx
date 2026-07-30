import { useState } from 'react'
import { Button } from './Button'

// For secrets the server will never show again (API keys, DCR client
// secrets). Always render inside a visible "shown only once" warning at
// the call site - this component only handles the copy affordance.
export function CopyOnceField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">{label}</label>
      <div className="flex items-center gap-2">
        <code className="flex-1 overflow-x-auto rounded-md bg-slate-100 px-2 py-1.5 text-xs dark:bg-slate-800">
          {value}
        </code>
        <Button type="button" variant="secondary" onClick={handleCopy}>
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
    </div>
  )
}
