import { useMemo, useState } from 'react'
import type { FeatureCollection, Point } from 'geojson'
import { ChevronDown } from 'lucide-react'
import { AnalyticsMap } from '@/components/maps/analytics-map'
import { MapLegend } from '@/components/maps/map-legend'
import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { getActiveLayers, mapLayers } from './layers'
import { useLayerSession } from './use-layer-session'
import { useBinFilters } from './use-bin-filters'
import type { BinProperties } from './api'
import { adequacyMonthLabel, adequacyWasteTypes, type AdequacyData } from './adequacy'
import { useAdequacy } from './use-adequacy'

export function MapAnalyticsPage() {
  const adequacy = useAdequacy()
  const { selection, states, toggle, retry } = useLayerSession(mapLayers, adequacy.requests)
  const bins = states.bins
  const binFilters = useBinFilters(bins?.status === 'ready' ? bins.data as FeatureCollection<Point, BinProperties> : undefined)
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false)
  const adequacyState = states.adequacy
  const analysisData = adequacyState?.status === 'ready' ? adequacyState.data as AdequacyData : undefined
  const renderedData = useMemo(() => ({
    bins: binFilters.filteredData,
    adequacy: analysisData ? { ...analysisData, features: analysisData.features.filter(f => f.properties.waste_type === adequacy.wasteType) } : undefined,
  }), [binFilters.filteredData, analysisData, adequacy.wasteType])
  const activeLayers = getActiveLayers(selection)

  return (
    <section className="analytics-layout min-w-0 space-y-4" aria-labelledby="analytics-title" data-active-layers={activeLayers.map(layer => layer.id).join(' ')}>
      <h1 id="analytics-title" className="text-2xl font-semibold">Žemėlapio analitika</h1>
      <AnalyticsMap definitions={mapLayers} selection={selection} states={states} renderedData={renderedData} />
      <div className="min-w-0 space-y-5 rounded-lg border bg-card p-4">
        <section aria-label="Žemėlapio sluoksniai">
          <h2 className="mb-3 font-semibold">Sluoksniai</h2>
          <div role="group" aria-label="Sluoksnių sąrašas" tabIndex={0} className="flex max-h-56 flex-wrap items-start gap-x-4 gap-y-3 overflow-y-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            {mapLayers.map(layer => {
              const state = states[layer.id]
              const selected = !!selection[layer.id]
              return (
                <div key={layer.id} className="space-y-2">
                  <div className="flex min-h-7 items-center gap-1">
                    <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                      <input type="checkbox" className="size-4 shrink-0 accent-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" checked={selected} onChange={event => {
                        if (layer.id === 'adequacy' && event.target.checked && adequacy.status === 'idle') adequacy.refresh()
                        toggle(layer.id, event.target.checked)
                      }} />
                      {layer.label}
                    </label>
                    {layer.id === 'bins' && (
                      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="size-7 shrink-0" aria-label="Atliekų rūšys" title="Atliekų rūšys">
                            <ChevronDown className="size-4" aria-hidden="true" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-sm">
                          <DialogHeader>
                            <DialogTitle>Atliekų rūšys</DialogTitle>
                            <DialogDescription>Pasirinkite žemėlapyje rodomų konteinerių atliekų rūšis.</DialogDescription>
                          </DialogHeader>
                          <div role="group" aria-label="Konteinerių atliekų rūšys" className="space-y-4">
                            {binFilters.availableCategories.map(category => (
                              <label key={category.id} className="flex cursor-pointer items-start gap-3 text-sm">
                                <input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" checked={binFilters.categories[category.id]} onChange={event => binFilters.toggleCategory(category.id, event.target.checked)} />
                                <span>{category.label}</span>
                              </label>
                            ))}
                          </div>
                          <DialogFooter>
                            <DialogClose asChild><Button variant="outline">Uždaryti</Button></DialogClose>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                    )}
                    {layer.id === 'adequacy' && (
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="size-7 shrink-0" aria-label="Pakankamumo analizės" title="Pakankamumo analizės"><ChevronDown className="size-4" aria-hidden="true" /></Button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-sm">
                          <DialogHeader>
                            <DialogTitle>Pakankamumo analizės</DialogTitle>
                            <DialogDescription>Pasirinkite mėnesį ir atliekų rūšį.</DialogDescription>
                          </DialogHeader>
                          <div className="space-y-4">
                            <label className="grid gap-2 text-sm font-medium">Mėnuo
                              <select aria-label="Analizės mėnuo" className="min-w-0 w-full rounded-md border bg-background p-2 text-sm" value={adequacy.analysisId} onChange={event => adequacy.setAnalysisId(event.target.value)} disabled={!adequacy.catalog.length}>
                                {!adequacy.catalog.length && <option value="">Analizių nėra</option>}
                                {adequacy.catalog.map(entry => <option key={entry.id} value={entry.id}>{adequacyMonthLabel(entry.month)}</option>)}
                              </select>
                            </label>
                            <label className="grid gap-2 text-sm font-medium">Atliekų rūšis
                              <select aria-label="Analizės atliekų rūšis" className="min-w-0 w-full rounded-md border bg-background p-2 text-sm" value={adequacy.wasteType} onChange={event => adequacy.setWasteType(event.target.value)}>
                                {adequacyWasteTypes.map(w => <option key={w.value} value={w.value}>{w.label}</option>)}
                              </select>
                            </label>
                            <Button variant="outline" size="sm" onClick={adequacy.refresh} disabled={adequacy.status === 'loading'}>{adequacy.status === 'error' ? 'Bandyti dar kartą' : 'Atnaujinti analizių sąrašą'}</Button>
                            {adequacy.status === 'loading' && <p role="status" className="text-xs">Kraunami duomenys…</p>}
                            {adequacy.status === 'error' && <p role="alert" className="text-xs text-destructive">Nepavyko įkelti sluoksnio.</p>}
                          </div>
                          <DialogFooter><DialogClose asChild><Button variant="outline">Uždaryti</Button></DialogClose></DialogFooter>
                        </DialogContent>
                      </Dialog>
                    )}
                  </div>
                  {layer.id === 'adequacy' && selected && (
                    <div className="max-w-72 space-y-2 text-xs">
                      {adequacy.status === 'loading' && <p role="status">Kraunami duomenys…</p>}
                      {adequacy.status === 'ready' && !adequacy.catalog.length && <p role="status">Duomenų nėra.</p>}
                      {adequacy.selected && <p>{adequacy.selected.period_start} – {adequacy.selected.period_end}<br />{adequacyWasteTypes.find(w => w.value === adequacy.wasteType)?.label}</p>}
                      {adequacy.status === 'error' && <><p role="alert" className="text-destructive">Nepavyko įkelti sluoksnio.</p><Button variant="outline" size="sm" onClick={adequacy.refresh}>Bandyti dar kartą</Button></>}
                    </div>
                  )}
                  {selected && state?.status === 'loading' && <p role="status" className="text-xs">Kraunami duomenys…</p>}
                  {selected && state?.status === 'ready' && state.data.features.length === 0 && <p role="status" className="text-xs">Duomenų nėra.</p>}
                  {layer.id === 'bins' && selected && state?.status === 'ready' && state.data.features.length > 0 && binFilters.noneSelected && <p role="status" className="text-xs">Nepasirinkta atliekų rūšių.</p>}
                  {selected && state?.status === 'error' && (
                    <div className="space-y-2">
                      <p role="alert" className="text-xs text-destructive">Nepavyko įkelti sluoksnio.</p>
                      <Button variant="outline" size="sm" aria-label={`Bandyti dar kartą: ${layer.label}`} onClick={() => retry(layer.id)}>Bandyti dar kartą</Button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
        <MapLegend definitions={mapLayers} />
      </div>
    </section>
  )
}
