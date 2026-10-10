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

export function MapAnalyticsPage() {
  const { selection, states, toggle, retry } = useLayerSession(mapLayers)
  const bins = states.bins
  const binFilters = useBinFilters(bins?.status === 'ready' ? bins.data as FeatureCollection<Point, BinProperties> : undefined)
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false)
  const renderedData = useMemo(() => ({ bins: binFilters.filteredData }), [binFilters.filteredData])
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
                      <input type="checkbox" className="size-4 shrink-0 accent-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" checked={selected} onChange={event => toggle(layer.id, event.target.checked)} />
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
                  </div>
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
