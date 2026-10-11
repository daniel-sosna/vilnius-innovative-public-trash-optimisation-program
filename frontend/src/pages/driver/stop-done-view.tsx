import { ArrowLeft, CheckCircle2, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { FillLevel, RouteStop } from './api'
import { FILL_OPTIONS, fillLabel } from './fill-levels'

type Props = {
  stop: RouteStop
  levels: FillLevel[]
  saving: boolean
  onBack: () => void
  onConfirm: () => void
}

export function StopDoneView({ stop, levels, saving, onBack, onConfirm }: Props) {
  return (
    <div className="fixed inset-0 z-20 flex flex-col bg-background">
      <header className="px-4 pt-4">
        <button
          type="button"
          onClick={onBack}
          disabled={saving}
          className="flex h-12 items-center gap-2 rounded-lg border bg-card px-4 text-base font-medium disabled:opacity-50"
        >
          <ArrowLeft className="size-5" aria-hidden="true" /> Atgal
        </button>
      </header>
      <div className="px-4 pt-4">
        <CheckCircle2 className="size-12 text-primary" aria-hidden="true" />
        <h1 className="mt-2 text-2xl font-bold">Visi konteineriai pažymėti</h1>
        <p className="truncate text-sm text-muted-foreground">{stop.address ?? 'Be adreso'}</p>
      </div>
      <ul className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
        {stop.bins.map((bin, index) => (
          <li key={bin.bin_id} className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3">
            <span
              className={cn(
                'flex size-9 shrink-0 items-center justify-center rounded-full text-lg font-semibold text-white',
                FILL_OPTIONS[levels[index]].color,
              )}
            >
              {levels[index]}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-base font-medium">{bin.inventory_number ?? '–'}</span>
              <span className="block text-sm text-muted-foreground">{fillLabel(levels[index])}</span>
            </span>
          </li>
        ))}
      </ul>
      <div className="p-4">
        <Button onClick={onConfirm} disabled={saving} className="h-16 w-full text-xl">
          {saving ? (
            <>
              <LoaderCircle className="size-6 animate-spin" aria-hidden="true" /> Saugoma...
            </>
          ) : (
            'Patvirtinti'
          )}
        </Button>
      </div>
    </div>
  )
}
