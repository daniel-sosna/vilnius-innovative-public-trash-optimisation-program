import { useEffect, useState } from 'react'
import { TablePagination } from '@/components/table-pagination'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { getBinHistory, type BinSummary, type HistoryPage } from './api'
import { formatCapacity, formatHistoryDate, formatPercentage, formatValue, wasteLabel } from './format'

type Props = { bin: BinSummary; onClose: () => void; onRestoreFocus: () => void }
type Result = { key: string; data: HistoryPage | null; error: boolean }

export function BinHistoryDialog({ bin, onClose, onRestoreFocus }: Props) {
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<Result | null>(null)
  const key = JSON.stringify([bin.id, page, revision])
  const current = result?.key === key ? result : null
  const data = current?.data

  useEffect(() => {
    const controller = new AbortController()
    getBinHistory(bin.id, page, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        const lastPage = Math.max(1, Math.ceil(data.total / data.page_size))
        if (page > lastPage) { setPage(lastPage); return }
        setResult({ key, data, error: false })
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ key, data: null, error: true })
      })
    // Closing unmounts this component; selection remounts it with page 1.
    return () => controller.abort()
  }, [bin.id, page, revision, key])

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] flex-col overflow-hidden p-4 sm:max-w-[1024px] sm:p-6"
        onCloseAutoFocus={(event) => { event.preventDefault(); onRestoreFocus() }}>
        <DialogHeader className="max-h-[25dvh] shrink-0 overflow-y-auto pr-6 text-left">
          <DialogTitle className="break-words leading-snug">Konteineris {formatValue(bin.inventory_number)}</DialogTitle>
          <DialogDescription className="break-words">{wasteLabel(bin.waste_type)} · {formatCapacity(bin.capacity_m3)}</DialogDescription>
        </DialogHeader>
        {!current ? (
          <p role="status" className="text-sm text-muted-foreground">Kraunama aptarnavimo istorija…</p>
        ) : current.error ? (
          <div role="alert" className="space-y-3">
            <p className="text-sm text-destructive">Nepavyko gauti aptarnavimo istorijos.</p>
            <Button variant="outline" size="sm" onClick={() => setRevision((value) => value + 1)}>Bandyti dar kartą</Button>
          </div>
        ) : data?.total === 0 ? (
          <p role="status" className="text-sm text-muted-foreground">Šio konteinerio aptarnavimo istorijos nėra.</p>
        ) : data && (
          <>
            <div className="shrink-0 space-y-3">
              <PercentageBar label="Sėkmingi aptarnavimai" value={data.successful_service_percentage} color="bg-emerald-600" />
            </div>
            <div role="region" aria-label="Aptarnavimo istorija" tabIndex={0}
              className="min-h-0 flex-1 overflow-auto overscroll-contain rounded-md border focus-visible:outline-2 focus-visible:outline-ring">
              <ul className="divide-y">
                {data.items.map((entry) => (
                  <li key={entry.id} className="min-w-[48rem] p-3 text-sm">
                    <dl className="grid grid-cols-[11rem_9rem_minmax(12rem,1fr)_8rem] gap-x-4">
                      <HistoryField label="Data"><time dateTime={entry.date}>{formatHistoryDate(entry.date)}</time></HistoryField>
                      <HistoryField label="Aptarnavimas">{entry.was_serviced ? 'Aptarnautas' : 'Neaptarnautas'}</HistoryField>
                      <HistoryField label="Neaptarnavimo priežastis">{formatValue(entry.non_serviced_reason)}</HistoryField>
                      <HistoryField label="Užpildymo lygis">{formatValue(entry.fill_level)}</HistoryField>
                    </dl>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
        {data && data.total > data.page_size && (
          <div className="max-h-[35dvh] shrink-0 overflow-y-auto border-t pt-3">
          <TablePagination page={page} pageSize={data?.page_size ?? 20} total={data?.total ?? null}
            loading={!current} disabled={!!current?.error} onPageChange={setPage} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function PercentageBar({ label, value, color }: { label: string; value: number | null; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap justify-between gap-x-2 text-sm">
        <span>{label}</span><span className="font-medium tabular-nums">{formatPercentage(value)}</span>
      </div>
      <div role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={value ?? undefined} aria-valuetext={formatPercentage(value)} className="h-2 overflow-hidden rounded-full bg-muted">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value ?? 0}%` }} />
      </div>
    </div>
  )
}

function HistoryField({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="break-words tabular-nums">{children}</dd></div>
}
