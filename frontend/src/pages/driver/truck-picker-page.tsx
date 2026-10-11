import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { forecastDate, useProjectDate } from '@/lib/project-date/context'
import { loadTruckRoutes, type TruckRoute } from './api'

export function TruckPickerPage() {
  const { projectDate } = useProjectDate()
  const [result, setResult] = useState<{ date: string; trucks: TruckRoute[] | null; failed: boolean } | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    loadTruckRoutes(projectDate, controller.signal)
      .then((trucks) => {
        if (!controller.signal.aborted) setResult({ date: projectDate, trucks, failed: false })
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ date: projectDate, trucks: null, failed: true })
      })
    return () => controller.abort()
  }, [projectDate])
  const current = result?.date === projectDate ? result : null

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 px-4 py-6">
      <div>
        <h1 className="text-2xl font-semibold">Pasirinkite šiukšliavežę</h1>
        <p className="text-muted-foreground">Maršruto diena: <span className="tabular-nums">{forecastDate(projectDate)}</span></p>
      </div>
      {current?.failed ? (
        <p role="alert" className="text-destructive">Nepavyko įkelti šiukšliavežių. Bandykite dar kartą.</p>
      ) : !current ? (
        <LoaderCircle className="mx-auto size-8 animate-spin text-primary" aria-label="Kraunama" />
      ) : current.trucks?.length === 0 ? (
        <p role="status" className="text-lg">Šiai dienai paruošto maršruto duomenų nėra.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {current.trucks?.map((truck) => (
            <li key={truck.truck_id}>
              <Link
                to={`/driver/${truck.truck_id}`}
                className="flex min-h-16 items-center justify-between rounded-xl border bg-card px-4 text-lg font-medium"
              >
                <span>
                  {truck.truck_name}
                  <span className="block text-sm font-normal text-muted-foreground">Sustojimų: {truck.stop_count}</span>
                </span>
                <ChevronRight className="size-6" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <Button variant="outline" asChild className="h-14 text-lg">
        <Link to="/">Atgal</Link>
      </Button>
    </main>
  )
}
