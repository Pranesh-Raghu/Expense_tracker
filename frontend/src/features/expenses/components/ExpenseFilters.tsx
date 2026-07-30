import { Select } from '@/components/ui/Select'
import { toLabel } from '@/lib/format'
import type { ExpenseFilters as Filters } from '@/api/endpoints/expenses'
import { useCategories, useTransactionTypes } from '../api/queries'

interface ExpenseFiltersProps {
  filters: Filters
  onChange: (filters: Filters) => void
}

// The API only supports one filter dimension per call, so picking a
// category clears the transaction filter and vice versa - see
// api/endpoints/expenses.ts for how listExpenses() reflects this.
export function ExpenseFilters({ filters, onChange }: ExpenseFiltersProps) {
  const { data: categories } = useCategories()
  const { data: transactionTypes } = useTransactionTypes()

  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <div className="w-full sm:w-48">
        <Select
          value={filters.category ?? ''}
          onChange={(e) => onChange(e.target.value ? { category: e.target.value as Filters['category'] } : {})}
        >
          <option value="">All categories</option>
          {categories?.map((category) => (
            <option key={category} value={category}>
              {toLabel(category)}
            </option>
          ))}
        </Select>
      </div>

      <div className="w-full sm:w-48">
        <Select
          value={filters.transaction ?? ''}
          onChange={(e) =>
            onChange(e.target.value ? { transaction: e.target.value as Filters['transaction'] } : {})
          }
        >
          <option value="">All transaction types</option>
          {transactionTypes?.map((type) => (
            <option key={type} value={type}>
              {toLabel(type)}
            </option>
          ))}
        </Select>
      </div>
    </div>
  )
}
