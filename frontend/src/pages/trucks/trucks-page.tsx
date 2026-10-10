import { useEffect, useRef, useState } from 'react'
import { Check, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { TablePagination } from '@/components/table-pagination'
import { RowDeleteButton } from '@/components/row-delete-button'
import { TruckOverview } from './truck-overview'
import { useToast } from '@/components/ui/toast-context'
import { TruckEditor } from './truck-editor'
import { TruckDeleteDialog } from './truck-delete-dialog'
import { formatVolume, isVolumeInput, parseVolume, truckRequest, wasteCarriers, type Truck, type TruckPage } from './api'

type Query = {
  name: string
  availability: string
  minimum: string
  maximum: string
  carrier: string
  page: number
  revision: number
}
const initialQuery: Query = {
  name: '',
  availability: 'all',
  minimum: '',
  maximum: '',
  carrier: 'all',
  page: 1,
  revision: 0,
}
type Result = { key: string; data: TruckPage | null; error: boolean }

export function TrucksPage() {
  const notify = useToast()
  const [query, setQuery] = useState(initialQuery)
  const [result, setResult] = useState<Result | null>(null)
  const [editor, setEditor] = useState<Truck | 'new' | null>(null)
  const [deletion, setDeletion] = useState<Truck | null>(null)
  const [notice, setNotice] = useState('')
  const [statsRevision, setStatsRevision] = useState(0)
  const addButton = useRef<HTMLButtonElement>(null)
  const lastFocus = useRef<HTMLElement | null>(null)
  const key = JSON.stringify(query)
  const minimum = parseVolume(query.minimum)
  const maximum = parseVolume(query.maximum)
  const filterError =
    (query.minimum && minimum === null) ||
    (query.maximum && maximum === null)
      ? 'Įveskite skaičių, didesnį už nulį.'
      : minimum !== null && maximum !== null && minimum > maximum
        ? 'Mažiausia reikšmė negali viršyti didžiausios.'
        : ''
  const current = result?.key === key ? result : null
  const loading = !filterError && !current
  const data = current?.data
  const hasFilters =
    !!query.name.trim() ||
    query.availability !== 'all' ||
    !!query.minimum ||
    !!query.maximum ||
    query.carrier !== 'all'

  useEffect(() => {
    if (filterError) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ page: String(query.page) })
      if (query.name.trim()) params.set('name', query.name.trim())
      if (query.availability !== 'all')
        params.set('available', query.availability)
      if (query.minimum)
        params.set('min_max_volume_m3', String(minimum))
      if (query.maximum)
        params.set('max_max_volume_m3', String(maximum))
      if (query.carrier !== 'all') params.set('waste_carrier', query.carrier)
      truckRequest<TruckPage>(`?${params}`, { signal: controller.signal })
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
  }, [query, key, filterError, minimum, maximum])

  function changeFilter(
    field: 'name' | 'availability' | 'minimum' | 'maximum' | 'carrier',
    value: string,
  ) {
    setNotice('')
    setQuery((previous) => ({ ...previous, [field]: value, page: 1 }))
  }
  function refresh(message = '', mutation = false) {
    if (mutation) setStatsRevision((value) => value + 1)
    setNotice(message)
    setQuery((previous) => ({ ...previous, revision: previous.revision + 1 }))
  }
  function rememberFocus() {
    lastFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
  }
  function restoreFocus() {
    window.requestAnimationFrame(() => {
      const target = lastFocus.current
      if (
        target?.isConnected &&
        !target.closest('[role="dialog"], [role="alertdialog"]')
      )
        target.focus()
      else addButton.current?.focus()
    })
  }
  function openEditor(truck: Truck | 'new') {
    rememberFocus()
    setEditor(truck)
  }
  const paginationDisabled =
    loading || !!filterError || !!current?.error || !data?.total

  return (
    <section aria-labelledby="trucks-title" className="space-y-6">
      <div>
        <h1 id="trucks-title" className="text-2xl font-semibold tracking-tight">
          Šiukšliavežės
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Tvarkykite šiukšliavežes ir jų prieinamumą.
        </p>
      </div>
      <TruckOverview revision={statsRevision} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1.5fr_1fr_1fr]">
        <div className="space-y-2">
          <Label htmlFor="truck-search">Paieška pagal pavadinimą</Label>
          <Input
            id="truck-search"
            type="search"
            placeholder="Ieškoti šiukšliavežės"
            value={query.name}
            onChange={(e) => changeFilter('name', e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="availability-filter">Prieinamumas</Label>
          <Select
            value={query.availability}
            onValueChange={(value) => changeFilter('availability', value)}
          >
            <SelectTrigger id="availability-filter" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Visos</SelectItem>
              <SelectItem value="true">Prieinamos</SelectItem>
              <SelectItem value="false">Neprieinamos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="carrier-filter">Atliekų vežėjas</Label>
          <Select
            value={query.carrier}
            onValueChange={(value) => changeFilter('carrier', value)}
          >
            <SelectTrigger id="carrier-filter" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Visi vežėjai</SelectItem>
              {wasteCarriers.map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="volume-min">Talpa nuo (m³)</Label>
          <Input
            id="volume-min"
            inputMode="decimal"
            value={query.minimum}
            onChange={(e) => {
              if (isVolumeInput(e.target.value))
                changeFilter('minimum', e.target.value)
            }}
            aria-invalid={!!filterError}
            aria-describedby={filterError ? 'filter-error' : undefined}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="volume-max">Talpa iki (m³)</Label>
          <Input
            id="volume-max"
            inputMode="decimal"
            value={query.maximum}
            onChange={(e) => {
              if (isVolumeInput(e.target.value))
                changeFilter('maximum', e.target.value)
            }}
            aria-invalid={!!filterError}
            aria-describedby={filterError ? 'filter-error' : undefined}
          />
        </div>
      </div>
      <div className="flex justify-end">
        <div className="grid w-full grid-cols-1 gap-2 sm:w-auto sm:grid-cols-2">
          <Button
            className="px-4 has-[>svg]:px-4"
            ref={addButton}
            onClick={() => openEditor('new')}
          >
            <Plus aria-hidden="true" />
            Pridėti šiukšliavežę
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setNotice('')
              setQuery((previous) => ({
                ...initialQuery,
                revision: previous.revision + 1,
              }))
            }}
          >
            Išvalyti filtrus
          </Button>
        </div>
      </div>
      {filterError && (
        <p id="filter-error" role="alert" className="text-sm text-destructive">
          {filterError}
        </p>
      )}
      {notice && (
        <p role="status" className="text-sm text-primary">
          {notice}
        </p>
      )}
      <div aria-busy={loading} className="border-y bg-card">
        {loading ? (
          <p
            role="status"
            className="px-4 py-10 text-center text-sm text-muted-foreground"
          >
            Kraunama…
          </p>
        ) : current?.error ? (
          <div role="alert" className="space-y-3 px-4 py-8 text-center">
            <p className="text-sm text-destructive">
              Nepavyko atnaujinti sąrašo.
            </p>
            <Button variant="outline" onClick={() => refresh(notice)}>
              Bandyti dar kartą
            </Button>
          </div>
        ) : filterError ? (
          <p className="px-4 py-8 text-sm text-muted-foreground">
            Patikrinkite filtrų reikšmes.
          </p>
        ) : data?.total === 0 ? (
          <p
            role="status"
            className="px-4 py-10 text-center text-sm text-muted-foreground"
          >
            {hasFilters
              ? 'Pagal pasirinktus filtrus šiukšliavežių nerasta.'
              : 'Šiukšliavežių dar nėra.'}
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Šiukšliavežių sąrašas</caption>
            <thead className="hidden border-b text-muted-foreground sm:table-header-group">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Pavadinimas
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Maksimali talpa
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Atliekų vežėjas
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Prieinamumas
                </th>
                <th scope="col" className="px-4 py-3">
                  <span className="sr-only">Veiksmai</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((truck) => (
                <tr
                  key={truck.id}
                  className="grid cursor-pointer grid-cols-[1fr_auto] gap-x-3 gap-y-2 border-b px-4 py-4 last:border-b-0 hover:bg-muted/60 sm:table-row"
                  onClick={() => openEditor(truck)}
                >
                  <td className="col-span-2 row-start-1 min-w-0 sm:max-w-xs sm:px-4 sm:py-3">
                    <Button
                      variant="link"
                      className="h-auto max-w-full justify-start whitespace-normal break-words p-0 text-left text-sm font-medium text-foreground"
                      onClick={(e) => {
                        e.stopPropagation()
                        openEditor(truck)
                      }}
                    >
                      <span className="min-w-0 break-words">{truck.name}</span>
                    </Button>
                  </td>
                  <td className="col-start-1 row-start-2 min-w-0 break-words text-muted-foreground sm:px-4 sm:py-3 sm:text-foreground">
                    <span className="sm:hidden">Maksimali talpa: </span>
                    {formatVolume(truck.max_volume_m3)}
                  </td>
                  <td className="col-span-2 row-start-3 min-w-0 break-words text-muted-foreground sm:max-w-xs sm:px-4 sm:py-3 sm:text-foreground">
                    <span className="sm:hidden">Atliekų vežėjas: </span>
                    {truck.waste_carrier}
                  </td>
                  <td className="col-start-2 row-start-2 sm:px-4 sm:py-3">
                    <span className="inline-flex items-center gap-2">
                      <span
                        aria-hidden="true"
                        className={`inline-flex size-5 items-center justify-center rounded-full text-white ${truck.available ? 'bg-green-700' : 'bg-red-700'}`}
                      >
                        {truck.available ? (
                          <Check className="size-3.5" strokeWidth={3} />
                        ) : (
                          <X className="size-3.5" strokeWidth={3} />
                        )}
                      </span>
                      <span className="sr-only sm:not-sr-only">
                        {truck.available ? 'Prieinamas' : 'Neprieinamas'}
                      </span>
                    </span>
                  </td>
                  <td className="col-span-2 row-start-4 sm:px-4 sm:py-3 sm:text-right">
                    <RowDeleteButton
                      recordName={truck.name}
                      onClick={(e) => {
                        e.stopPropagation()
                        rememberFocus()
                        setDeletion(truck)
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <TablePagination
        key={JSON.stringify([
          query.name,
          query.availability,
          query.minimum,
          query.maximum,
          query.carrier,
          query.revision,
        ])}
        page={query.page}
        pageSize={data?.page_size ?? 10}
        total={data?.total ?? null}
        disabled={!!paginationDisabled}
        loading={loading}
        onPageChange={(page) => setQuery((previous) => ({ ...previous, page }))}
      />
      {editor !== null && (
        <TruckEditor
          truck={editor === 'new' ? null : editor}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null)
            notify({ message: 'Šiukšliavežė išsaugota.', variant: 'success' })
            refresh('', true)
          }}
          onRefresh={() => refresh()}
          restoreFocus={restoreFocus}
        />
      )}
      {deletion && (
        <TruckDeleteDialog
          truck={deletion}
          onClose={() => setDeletion(null)}
          onDeleted={() => {
            setDeletion(null)
            refresh('Šiukšliavežė ištrinta.', true)
          }}
          restoreFocus={restoreFocus}
        />
      )}
    </section>
  )
}
