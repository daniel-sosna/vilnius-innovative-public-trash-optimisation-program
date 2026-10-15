import { wasteLabel } from '@/pages/sites/format'
import type { RouteStop } from './api'

const SHOWN_BINS = 3

export function NextStopPanel({ stop, serviced, total }: { stop: RouteStop; serviced: number; total: number }) {
  const hidden = stop.bins.length - SHOWN_BINS
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-10 p-3">
      <div className="rounded-lg border bg-card p-4 text-card-foreground shadow-lg">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h1 className="text-sm font-semibold uppercase tracking-wide text-primary">Kitas konteineris</h1>
          <span className="text-lg font-bold tabular-nums">{serviced} / {total} konteinerių</span>
        </div>
        <p className="mt-1 break-words text-lg font-semibold">{stop.address ?? 'Be adreso'}</p>
        <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
          {stop.bins.slice(0, SHOWN_BINS).map((bin) => (
            <li key={bin.bin_id} className="truncate">
              Inventorinis Nr.: {bin.inventory_number ?? '–'} · Atliekų tipas: {wasteLabel(bin.waste_type)}
            </li>
          ))}
          {hidden > 0 && <li>+ dar {hidden}</li>}
        </ul>
      </div>
    </div>
  )
}
