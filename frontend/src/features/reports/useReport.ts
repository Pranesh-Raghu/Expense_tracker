import { useQuery } from '@tanstack/react-query'
import { getReportRows, getReportTotal, paramsAreComplete, type ReportParams } from '@/api/endpoints/reports'
import { reportKeys } from './keys'

export function useReport(params: ReportParams) {
  return useQuery({
    queryKey: reportKeys.rows(params),
    queryFn: () => getReportRows(params),
    enabled: paramsAreComplete(params),
  })
}

export function useReportTotal(params: ReportParams) {
  return useQuery({
    queryKey: reportKeys.total(params),
    queryFn: () => getReportTotal(params),
    enabled: paramsAreComplete(params),
  })
}
