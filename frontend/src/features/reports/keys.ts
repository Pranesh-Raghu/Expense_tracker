import type { ReportParams } from '@/api/endpoints/reports'

export const reportKeys = {
  all: ['reports'] as const,
  rows: (params: ReportParams) => [...reportKeys.all, 'rows', params] as const,
  total: (params: ReportParams) => [...reportKeys.all, 'total', params] as const,
}
