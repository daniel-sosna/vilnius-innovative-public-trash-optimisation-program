import { ArrowLeft, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { wasteLabel } from '@/pages/sites/format'
import type { FillLevel, RouteBin } from './api'
import { FILL_OPTIONS } from './fill-levels'

type Props = {
  address: string | null
  bin: RouteBin
  position: number
  total: number
  chosen: FillLevel | null
  onChoose: (level: FillLevel) => void
  onBack: (() => void) | null
}

export function BinLevelStep({ address, bin, position, total, chosen, onChoose, onBack }: Props) {
  return (
    <div className="fixed inset-0 z-20 flex flex-col bg-background pb-[env(safe-area-inset-bottom)]">
      <header className="flex items-center gap-3 px-4 pt-4">
        {onBack ? (
          <button
            type="button"
            onClick={onBack}
            className="flex h-12 items-center gap-2 rounded-lg border bg-card px-4 text-base font-medium"
          >
            <ArrowLeft className="size-5" aria-hidden="true" /> Atgal
          </button>
        ) : (
          <span className="h-12" />
        )}
        <span className="ml-auto text-lg font-semibold tabular-nums">{position} / {total}</span>
      </header>
      <div className="px-4 pt-3">
        <p className="break-words text-sm text-muted-foreground">{address ?? 'Be adreso'}</p>
        <h1 className="mt-1 text-2xl font-bold">Inventorinis Nr.: {bin.inventory_number ?? '–'}</h1>
        <p className="text-base text-muted-foreground">{wasteLabel(bin.waste_type)}</p>
        <h2 className="mt-4 text-xl font-semibold">Kiek konteineris buvo užpildytas?</h2>
      </div>
      <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto px-4 pb-4 pt-3">
        {FILL_OPTIONS.map((option) => {
          const selected = chosen === option.level
          return (
            <button
              key={option.level}
              type="button"
              aria-pressed={selected}
              onClick={() => onChoose(option.level)}
              className={cn(
                'flex min-h-16 flex-1 items-center gap-4 rounded-xl border-2 px-4 text-left text-xl font-semibold motion-safe:active:scale-[0.99] focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-ring',
                option.color,
                selected ? 'border-foreground ring-4 ring-foreground/30' : 'border-transparent opacity-90',
              )}
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-white/25 text-2xl tabular-nums">
                {option.level}
              </span>
              <span className="flex-1">{option.label}</span>
              {selected && <Check className="size-7" aria-hidden="true" />}
            </button>
          )
        })}
      </div>
    </div>
  )
}
