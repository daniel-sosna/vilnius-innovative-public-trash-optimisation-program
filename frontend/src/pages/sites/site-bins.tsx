import { useEffect, useState } from 'react'
import { ChevronRight } from 'lucide-react'
import { TablePagination } from '@/components/table-pagination'
import { Button } from '@/components/ui/button'
import { getSiteBins, type BinPage, type BinSummary } from './api'
import { formatCapacity, formatValue, wasteLabel } from './format'
import { BinHistoryDialog } from './bin-history-dialog'

type Result = { key: string; data: BinPage | null; error: boolean }
type Selection = { bin: BinSummary; trigger: HTMLButtonElement }

export function SiteBins({ siteId }: { siteId: string }) {
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<Result | null>(null)
  const [selected, setSelected] = useState<Selection | null>(null)
  const key = JSON.stringify([siteId, page, revision])
  const current = result?.key === key ? result : null
  const data = current?.data

  useEffect(() => {
    const controller = new AbortController()
    getSiteBins(siteId, page, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        const lastPage = Math.max(1, Math.ceil(data.total / data.page_size))
        if (page > lastPage) { setPage(lastPage); return }
        setResult({ key, data, error: false })
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ key, data: null, error: true })
      })
    return () => controller.abort()
  }, [siteId, page, revision, key])

  return (
    <section aria-labelledby="site-bins-title" className="space-y-4">
      <h2 id="site-bins-title" className="text-lg font-semibold">Konteineriai</h2>
      <div className="overflow-hidden rounded-lg border bg-card" aria-busy={!current}>
        {!current ? (
          <p role="status" className="p-5 text-sm text-muted-foreground">Kraunami konteineriai…</p>
        ) : current.error ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 p-5">
            <p className="text-sm text-destructive">Nepavyko gauti konteinerių.</p>
            <Button variant="outline" size="sm" onClick={() => setRevision((value) => value + 1)}>
              Bandyti dar kartą
            </Button>
          </div>
        ) : data?.items.length === 0 ? (
          <p role="status" className="p-5 text-sm text-muted-foreground">Šioje surinkimo vietoje konteinerių nėra.</p>
        ) : (
          <ul className="divide-y">
            {data?.items.map((bin) => (
              <li key={bin.id}>
                <button
                  type="button"
                  aria-haspopup="dialog"
                  aria-label={`Konteineris ${formatValue(bin.inventory_number)}, ${wasteLabel(bin.waste_type)}, ${formatCapacity(bin.capacity_m3)}`}
                  onClick={(event) => setSelected({ bin, trigger: event.currentTarget })}
                  className="grid w-full grid-cols-[minmax(0,1fr)_1rem] items-center gap-3 px-4 py-3 text-left text-sm hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_6rem_1rem]"
                >
                  <span className="col-start-1 row-start-1 min-w-0 break-words">
                    <span className="block text-xs text-muted-foreground">Inventorinis numeris</span>
                    {formatValue(bin.inventory_number)}
                  </span>
                  <span className="col-start-1 row-start-2 min-w-0 break-words sm:col-start-2 sm:row-start-1">{wasteLabel(bin.waste_type)}</span>
                  <span className="col-start-1 row-start-3 whitespace-nowrap tabular-nums sm:col-start-3 sm:row-start-1">{formatCapacity(bin.capacity_m3)}</span>
                  <ChevronRight aria-hidden="true" className="col-start-2 row-start-1 size-4 sm:col-start-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <TablePagination page={page} pageSize={data?.page_size ?? 10} total={data?.total ?? null}
        loading={!current} disabled={!!current?.error} onPageChange={setPage} />
      {selected && (
        <BinHistoryDialog key={selected.bin.id} bin={selected.bin}
          onClose={() => setSelected(null)}
          onRestoreFocus={() => {
            if (selected.trigger.isConnected) selected.trigger.focus()
          }} />
      )}
    </section>
  )
}
