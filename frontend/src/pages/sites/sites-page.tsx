import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import { TablePagination } from '@/components/table-pagination'
import { RowDeleteButton } from '@/components/row-delete-button'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { getSites, type SitePage, type SiteSummary } from './api'
import { formatValue, siteListAddress } from './format'
import { SiteOverview } from './site-overview'
import { CollectionEditor } from './collection-editor'
import { CollectionDeleteDialog } from './collection-delete-dialog'

type Query = { address: string; page: number; revision: number }
type Result = { key: string; data: SitePage | null; error: boolean }

export function SitesPage() {
  const [query, setQuery] = useState<Query>({
    address: '',
    page: 1,
    revision: 0,
  })
  const [deleting, setDeleting] = useState<{ site: SiteSummary; trigger: HTMLButtonElement } | null>(null)
  const [creating, setCreating] = useState(false)
  const [overviewRevision, setOverviewRevision] = useState(0)
  const createTrigger = useRef<HTMLButtonElement>(null)
  const [result, setResult] = useState<Result | null>(null)
  const key = JSON.stringify(query)
  const current = result?.key === key ? result : null
  const data = current?.data
  const loading = !current
  const hasFilter = !!query.address.trim()

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      getSites(query.page, query.address, controller.signal)
        .then((page) => {
          if (controller.signal.aborted) return
          const lastPage = Math.max(1, Math.ceil(page.total / page.page_size))
          if (query.page > lastPage) {
            setQuery((value) =>
              JSON.stringify(value) === key
                ? { ...value, page: lastPage }
                : value,
            )
            return
          }
          setResult({ key, data: page, error: false })
        })
        .catch(() => {
          if (!controller.signal.aborted)
            setResult({ key, data: null, error: true })
        })
    }, 200)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [query, key])

  function refresh() {
    setQuery((value) => ({ ...value, revision: value.revision + 1 }))
    setOverviewRevision((value) => value + 1)
  }

  function clearFilter() {
    setQuery((value) => ({ ...value, address: '', page: 1 }))
  }

  return (
    <section aria-labelledby="sites-title" className="space-y-6">
      <div>
        <h1 id="sites-title" className="text-2xl font-semibold tracking-tight">
          Šiukšlių surinkimo vietos
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Peržiūrėkite surinkimo vietas ir jų konteinerius.
        </p>
      </div>
      <SiteOverview revision={overviewRevision} />
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 basis-full space-y-2 sm:basis-0 sm:max-w-lg">
          <Label htmlFor="site-address">Paieška pagal adresą</Label>
          <Input
            id="site-address"
            type="search"
            placeholder="Ieškoti surinkimo vietos"
            value={query.address}
            onChange={(event) =>
              setQuery((value) => ({
                ...value,
                address: event.target.value,
                page: 1,
              }))
            }
          />
        </div>
        <Button variant="secondary" onClick={clearFilter}>
          Išvalyti filtrą
        </Button>
        <Button className="ml-auto" ref={createTrigger} onClick={() => setCreating(true)}>Pridėti surinkimo vietą</Button>
      </div>
      <div
        className="overflow-hidden rounded-lg border bg-card"
        aria-busy={loading}
      >
        <div className="flex items-center gap-2 border-b bg-muted/40 pr-3 text-sm font-medium">
          <div className="grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto_1.25rem]">
            <span>Adresas</span>
            <span>Konteineriai</span>
            <span aria-hidden="true" className="hidden sm:block" />
          </div>
          <span className="w-16 shrink-0 text-center text-xs">Veiksmai</span>
        </div>
        {loading ? (
          <p role="status" className="p-5 text-sm text-muted-foreground">
            Kraunamos surinkimo vietos…
          </p>
        ) : current.error ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 p-5">
            <p className="text-sm text-destructive">
              Nepavyko gauti surinkimo vietų.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setQuery((value) => ({
                  ...value,
                  revision: value.revision + 1,
                }))
              }
            >
              Bandyti dar kartą
            </Button>
          </div>
        ) : data?.items.length === 0 ? (
          <div
            role="status"
            className="space-y-3 p-5 text-sm text-muted-foreground"
          >
            <p>
              {hasFilter
                ? 'Pagal pasirinktą adresą surinkimo vietų nerasta.'
                : 'Surinkimo vietų dar nėra.'}
            </p>
            {hasFilter && (
              <Button variant="outline" size="sm" onClick={clearFilter}>
                Išvalyti filtrą
              </Button>
            )}
          </div>
        ) : (
          <ul className="divide-y">
            {data?.items.map((site) => (
              <li key={site.id} className="flex flex-wrap items-center gap-2 pr-3">
                <Link
                  to={`/admin/sites/${site.id}`}
                  className="group grid min-h-12 min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] sm:grid-cols-[minmax(0,1fr)_auto_1.25rem] items-center gap-3 px-4 py-3 text-sm hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
                  aria-label={`${siteListAddress(site.address)} – konteinerių skaičius: ${formatValue(site.bin_count)}`}
                >
                  <span className="break-words">
                    {siteListAddress(site.address)}
                  </span>
                  <span className="tabular-nums">
                    {formatValue(site.bin_count)}
                  </span>
                  <ExternalLink
                    aria-hidden="true"
                    className="hidden size-4 opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 sm:block"
                  />
                </Link>
                <RowDeleteButton recordName={siteListAddress(site.address)} className="my-2 w-16 shrink-0" aria-label={`Ištrinti surinkimo vietą: ${siteListAddress(site.address)}`} onClick={(event) => setDeleting({ site, trigger: event.currentTarget })} />
              </li>
            ))}
          </ul>
        )}
      </div>
      {creating && <CollectionEditor onClose={() => setCreating(false)} restoreFocus={() => createTrigger.current?.focus()}
        onSaved={() => { setCreating(false); refresh() }} />}
      {deleting && <CollectionDeleteDialog kind="site" id={deleting.site.id} label={deleting.site.address} onClose={() => setDeleting(null)}
        onDeleted={() => { setDeleting(null); refresh() }} onRefresh={refresh}
        restoreFocus={() => { if (deleting.trigger.isConnected) deleting.trigger.focus(); else createTrigger.current?.focus() }} />}
      <TablePagination
        page={query.page}
        pageSize={data?.page_size ?? 15}
        total={data?.total ?? null}
        loading={loading}
        disabled={!!current?.error}
        onPageChange={(page) => setQuery((value) => ({ ...value, page }))}
      />
    </section>
  )
}
