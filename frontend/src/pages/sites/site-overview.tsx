import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { getSiteStats, type SiteStats, type WasteTypeCount } from './api'
import { formatCapacity, formatValue, wasteLabel } from './format'

type Result = { key: string; data: SiteStats | null; error: boolean }
const wasteColors: Record<string, string> = {
  'Mixed municipal waste': '#92400e',
  'Paper/plastic waste': '#2563eb',
  'Glass waste': '#15803d',
}

function wasteColor(key: string): string {
  // Unknown source keys retain their text and a deterministic color.
  let hash = 0
  for (const character of key)
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  return wasteColors[key] ?? `hsl(${hash % 360} 45% 40%)`
}

function WasteDonut({ groups, totalBins }: { groups: WasteTypeCount[]; totalBins: number }) {
  const total = groups.reduce((sum, group) => sum + group.count, 0)
  if (total === 0)
    return (
      <div className="flex items-end gap-4">
        <p className="text-3xl font-semibold tabular-nums">{formatValue(totalBins)}</p>
        <p className="text-sm text-muted-foreground">Konteinerių pagal atliekų rūšį dar nėra.</p>
      </div>
    )

  const segments = groups.map((group, index) => ({
    ...group,
    offset:
      (groups.slice(0, index).reduce((sum, item) => sum + item.count, 0) /
        total) *
      100,
    percentage: (group.count / total) * 100,
    color: wasteColor(group.waste_type),
  }))

  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 space-y-4">
        <p className="break-words text-3xl font-semibold tabular-nums">{formatValue(totalBins)}</p>
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-4">
        <ul className="space-y-2 text-sm">
          {segments.map((segment) => (
            <li key={segment.waste_type} className="flex items-start gap-2">
              <span aria-hidden="true" className="mt-1 size-3 shrink-0 rounded-full"
                style={{ backgroundColor: segment.color }} />
              <span className="min-w-0 break-words">
                {wasteLabel(segment.waste_type)}:{' '}
                <span className="font-medium tabular-nums">{formatValue(segment.count)}</span>
              </span>
            </li>
          ))}
        </ul>
        <svg
          viewBox="0 0 100 100"
          className="size-24 shrink-0"
          role="img"
          aria-label="Konteinerių pasiskirstymas pagal atliekų rūšį"
        >
          <title>
            {groups
              .map(
                (group) =>
                  `${wasteLabel(group.waste_type)}: ${formatValue(group.count)}`,
              )
              .join('; ')}
          </title>
          {segments.map((segment) => (
            <circle
              key={segment.waste_type}
              cx="50"
              cy="50"
              r="40"
              pathLength="100"
              fill="none"
              stroke={segment.color}
              strokeWidth="12"
              strokeDasharray={`${segment.percentage} ${100 - segment.percentage}`}
              strokeDashoffset={-segment.offset}
              transform="rotate(-90 50 50)"
            />
          ))}
        </svg>
      </div>
    </div>
  )
}

export function SiteOverview({ revision = 0 }: { revision?: number }) {
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<Result | null>(null)
  const key = JSON.stringify([retry, revision])
  const current = result?.key === key ? result : null

  useEffect(() => {
    const controller = new AbortController()
    getSiteStats(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setResult({ key, data, error: false })
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setResult({ key, data: null, error: true })
      })
    return () => controller.abort()
  }, [key])

  const data = current?.data
  return (
    <section
      aria-label="Visų surinkimo vietų apžvalga"
      aria-busy={!current}
      className="space-y-3"
    >
      <p className="text-sm font-medium text-muted-foreground">
        Visų surinkimo vietų apžvalga
      </p>
      {!current ? (
        <p
          role="status"
          className="rounded-lg border bg-card p-5 text-sm text-muted-foreground"
        >
          Kraunama surinkimo vietų statistika…
        </p>
      ) : current.error ? (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-lg border bg-card p-5"
        >
          <p className="text-sm text-destructive">
            Nepavyko gauti surinkimo vietų statistikos.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRetry((value) => value + 1)}
          >
            Bandyti dar kartą
          </Button>
        </div>
      ) : (
        data && (
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_minmax(0,1fr)]">
            <div className="flex flex-col justify-between gap-4 rounded-lg border bg-card p-5">
              <p className="text-sm text-muted-foreground">Surinkimo vietos</p>
              <p className="text-3xl font-semibold tabular-nums">
                {formatValue(data.total_sites)}
              </p>
            </div>
            <div className="flex flex-col justify-between gap-4 rounded-lg border bg-card p-5">
              <p className="text-sm text-muted-foreground">Konteineriai</p>
              <WasteDonut groups={data.bins_by_waste_type} totalBins={data.total_bins} />
            </div>
            <div className="flex flex-col justify-between gap-4 rounded-lg border bg-card p-5">
              <p className="text-sm text-muted-foreground">Bendra talpa</p>
              <p className="break-words text-3xl font-semibold tabular-nums">
                {formatCapacity(data.total_capacity_m3)}
              </p>
            </div>
          </div>
        )
      )}
    </section>
  )
}
