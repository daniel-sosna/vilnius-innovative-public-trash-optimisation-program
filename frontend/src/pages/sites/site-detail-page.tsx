import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LocationMap } from '@/components/maps/location-map'
import { getSite, SiteReadError, type SiteDetail } from './api'
import { formatCapacity, formatValue } from './format'
import { SiteBins } from './site-bins'

type Result = { key: string; data: SiteDetail | null; error: 'missing' | 'failed' | null }

export function SiteDetailPage() {
  const { id = '' } = useParams()
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<Result | null>(null)
  const key = JSON.stringify([id, revision])
  const current = result?.key === key ? result : null
  const site = current?.data

  useEffect(() => {
    const controller = new AbortController()
    getSite(id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data, error: null })
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setResult({
          key, data: null,
          error: error instanceof SiteReadError && error.status === 404 ? 'missing' : 'failed',
        })
      })
    return () => controller.abort()
  }, [id, revision, key])

  return (
    <section aria-labelledby="site-detail-title" className="space-y-6">
      <div className="space-y-3">
        <Button asChild variant="outline" size="sm">
          <Link to="/admin/sites"><ArrowLeft aria-hidden="true" /> Grįžti į vietų sąrašą</Link>
        </Button>
        <h1 id="site-detail-title" className="break-words text-2xl font-semibold tracking-tight">
          {site ? formatValue(site.address) : 'Surinkimo vieta'}
        </h1>
      </div>
      {!current ? (
        <p role="status" className="text-sm text-muted-foreground">Kraunami vietos duomenys…</p>
      ) : current.error ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border bg-card p-5">
          <p className="text-sm text-destructive">
            {current.error === 'missing' ? 'Surinkimo vieta nerasta.' : 'Nepavyko gauti surinkimo vietos duomenų.'}
          </p>
          {current.error === 'failed' && (
            <Button variant="outline" size="sm" onClick={() => setRevision((value) => value + 1)}>
              Bandyti dar kartą
            </Button>
          )}
        </div>
      ) : site && (
        <>
          <LocationMap latitude={site.latitude} longitude={site.longitude} zoom={15.5} interactive />
          <SiteStatistics site={site} />
          <SiteBins key={id} siteId={id} />
        </>
      )}
    </section>
  )
}

function SiteStatistics({ site }: { site: SiteDetail }) {
  const fields = [
    ['Seniūnija', formatValue(site.sub_district)],
    ['Gatvė', formatValue(site.street)],
    ['Namo numeris', formatValue(site.house_number)],
    ['Pašto kodas', formatValue(site.postal_code)],
    ['Konteinerių skaičius', formatValue(site.bin_count)],
    ['Naudotojai', site.object_groups.length ? site.object_groups.join(',') : 'N/A'],
    ['Bendra talpa', formatCapacity(site.total_capacity_m3)],
    ['Atliekų vežėjas', site.waste_carriers.length ? site.waste_carriers.join(', ') : 'N/A'],
  ]
  return (
    <div className="rounded-lg border bg-card p-4 sm:p-5">
      <h2 className="mb-4 text-lg font-semibold">Vietos duomenys</h2>
      <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
        {fields.map(([label, value]) => (
          <div key={label} className="min-w-0 space-y-1">
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="break-words text-sm font-medium tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
