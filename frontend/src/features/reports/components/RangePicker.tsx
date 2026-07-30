import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import type { ReportGrain, ReportParams } from '@/api/endpoints/reports'

const now = new Date()

interface RangePickerProps {
  params: ReportParams
  onChange: (params: ReportParams) => void
}

export function RangePicker({ params, onChange }: RangePickerProps) {
  function setGrain(grain: ReportGrain) {
    onChange({
      grain,
      year: params.year,
      month: grain === 'yearly' ? undefined : params.month ?? now.getMonth() + 1,
      day: grain === 'daily' || grain === 'weekly' ? params.day ?? now.getDate() : undefined,
    })
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="w-36">
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Range</label>
        <Select value={params.grain} onChange={(e) => setGrain(e.target.value as ReportGrain)}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="yearly">Yearly</option>
        </Select>
      </div>

      <div className="w-28">
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Year</label>
        <Input
          type="number"
          value={params.year}
          onChange={(e) => onChange({ ...params, year: Number(e.target.value) })}
        />
      </div>

      {params.grain !== 'yearly' && (
        <div className="w-24">
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Month</label>
          <Input
            type="number"
            min={1}
            max={12}
            value={params.month ?? ''}
            onChange={(e) => onChange({ ...params, month: Number(e.target.value) })}
          />
        </div>
      )}

      {(params.grain === 'daily' || params.grain === 'weekly') && (
        <div className="w-24">
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Day</label>
          <Input
            type="number"
            min={1}
            max={31}
            value={params.day ?? ''}
            onChange={(e) => onChange({ ...params, day: Number(e.target.value) })}
          />
        </div>
      )}
    </div>
  )
}
