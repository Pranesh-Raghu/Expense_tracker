import { IntrospectPanel } from '../components/IntrospectPanel'
import { RevokePanel } from '../components/RevokePanel'

export function TokenToolsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Token tools</h1>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <IntrospectPanel />
        <RevokePanel />
      </div>
    </div>
  )
}
