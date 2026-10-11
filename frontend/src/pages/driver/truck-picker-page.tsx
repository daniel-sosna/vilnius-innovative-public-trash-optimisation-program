import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { loadTrucks, type TruckSummary } from './api'

export function TruckPickerPage() {
  const [trucks, setTrucks] = useState<TruckSummary[] | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    loadTrucks(controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) setTrucks(items.filter((truck) => truck.available))
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true)
      })
    return () => controller.abort()
  }, [])

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 px-4 py-6">
      <h1 className="text-2xl font-semibold">Pasirinkite šiukšliavežę</h1>
      {failed ? (
        <p role="alert" className="text-destructive">Nepavyko įkelti šiukšliavežių. Bandykite dar kartą.</p>
      ) : trucks === null ? (
        <LoaderCircle className="mx-auto size-8 animate-spin text-primary" aria-label="Kraunama" />
      ) : trucks.length === 0 ? (
        <p>Šiukšliavežių nėra.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {trucks.map((truck) => (
            <li key={truck.id}>
              <Link
                to={`/driver/${truck.id}`}
                className="flex min-h-16 items-center justify-between rounded-xl border bg-card px-4 text-lg font-medium"
              >
                <span>
                  {truck.name}
                  <span className="block text-sm font-normal text-muted-foreground">{truck.waste_carrier}</span>
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
