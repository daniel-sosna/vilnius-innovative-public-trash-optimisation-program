import { AnalyticsMap } from '@/components/maps/analytics-map'
import { MapLegend } from '@/components/maps/map-legend'
import { Button } from '@/components/ui/button'
import { getActiveLayers, mapLayers } from './layers'
import { useLayerSession } from './use-layer-session'

export function MapAnalyticsPage() {
  const { selection, states, toggle, retry } = useLayerSession(mapLayers)
  const activeLayers = getActiveLayers(selection)

  return (
    <section className="analytics-layout min-w-0 space-y-4" aria-labelledby="analytics-title" data-active-layers={activeLayers.map(layer => layer.id).join(' ')}>
      <h1 id="analytics-title" className="text-2xl font-semibold">Žemėlapio analitika</h1>
      <AnalyticsMap definitions={mapLayers} selection={selection} states={states} />
      <div className="min-w-0 space-y-5 rounded-lg border bg-card p-4">
        <section aria-label="Žemėlapio sluoksniai">
          <h2 className="mb-3 font-semibold">Sluoksniai</h2>
          <div role="group" aria-label="Sluoksnių sąrašas" tabIndex={0} className="max-h-56 space-y-4 overflow-y-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            {mapLayers.map(layer => {
              const state = states[layer.id]
              const selected = !!selection[layer.id]
              return (
                <div key={layer.id} className="space-y-2">
                  <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                    <input type="checkbox" className="size-4 shrink-0 accent-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" checked={selected} onChange={event => toggle(layer.id, event.target.checked)} />
                    {layer.label}
                  </label>
                  {selected && state?.status === 'loading' && <p role="status" className="text-xs">Kraunami duomenys…</p>}
                  {selected && state?.status === 'ready' && state.data.features.length === 0 && <p role="status" className="text-xs">Duomenų nėra.</p>}
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
