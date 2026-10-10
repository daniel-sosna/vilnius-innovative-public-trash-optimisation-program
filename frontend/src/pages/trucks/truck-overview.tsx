import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { truckRequest, type TruckStats } from './api'

type Result = { key: string; data: TruckStats | null; error: boolean }
const averageFormat = new Intl.NumberFormat('lt-LT', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export function TruckOverview({ revision }: { revision: number }) {
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<Result | null>(null)
  const key = `${revision}:${retry}`
  const current = result?.key === key ? result : null

  useEffect(() => {
    const controller = new AbortController()
    truckRequest<TruckStats>('/stats', { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data, error: false })
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setResult({ key, data: null, error: true })
      })
    return () => controller.abort()
  }, [key])

  const data = current?.data
  const ratio = data?.total ? data.available_count / data.total : 0
  const percentage = Math.round(ratio * 100)
  return (
    <section
      aria-label="Viso parko apžvalga"
      aria-busy={!current}
      className="space-y-3"
    >
      <p className="text-sm font-medium text-muted-foreground">
        Viso parko apžvalga
      </p>
      {!current ? (
        <p
          role="status"
          className="rounded-lg border bg-card p-5 text-sm text-muted-foreground"
        >
          Kraunama parko statistika…
        </p>
      ) : current.error ? (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-lg border bg-card p-5"
        >
          <p className="text-sm text-destructive">
            Nepavyko atnaujinti parko statistikos.
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
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col justify-between gap-4 rounded-lg border bg-card p-5">
              <p className="text-sm text-muted-foreground">
                Šiukšliavežių iš viso
              </p>
              <p className="text-3xl font-semibold tabular-nums">
                {data.total}
              </p>
            </div>
            <div className="flex flex-col justify-between gap-4 rounded-lg border bg-card p-5">
              <p className="text-sm text-muted-foreground">
                Vidutinė maksimali talpa
              </p>
              <p className="text-3xl font-semibold tabular-nums">
                {data.average_max_volume_m3 === null
                  ? '—'
                  : `${averageFormat.format(data.average_max_volume_m3)} m³`}
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-5">
              <div className="flex min-w-0 flex-col justify-between gap-4 self-stretch">
                <p className="text-sm text-muted-foreground">
                  Prieinamos šiukšliavežės
                </p>
                <p className="text-3xl font-semibold tabular-nums">
                  {data.available_count} iš {data.total}
                </p>
              </div>
              <div
                className="relative size-24 shrink-0"
                role="img"
                aria-label={`${percentage}% šiukšliavežių prieinamos (${data.available_count} iš ${data.total})`}
              >
                <svg
                  viewBox="0 0 100 100"
                  className="size-full"
                  aria-hidden="true"
                >
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-secondary"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    pathLength="100"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeDasharray={`${ratio * 100} 100`}
                    transform="rotate(-90 50 50)"
                    className="text-primary"
                  />
                </svg>
                <span
                  aria-hidden="true"
                  className="absolute inset-0 flex items-center justify-center text-xl font-semibold tabular-nums"
                >
                  {percentage}%
                </span>
              </div>
            </div>
          </div>
        )
      )}
    </section>
  )
}
