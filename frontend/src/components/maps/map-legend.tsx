import type { MapLayerDefinition } from './map-layer'

export function MapLegend({ definitions }: { definitions: readonly MapLayerDefinition[] }) {
  return (
    <section aria-label="Legenda" className="min-w-0">
      <h2 className="mb-3 font-semibold">Legenda</h2>
      <ul className="flex flex-wrap gap-x-6 gap-y-2">
        {definitions.flatMap(layer => layer.legend.map((entry, index) => (
          <li key={`${layer.id}-${index}`} className="flex min-w-0 items-center gap-2 text-sm">
            <span aria-hidden="true" className="size-3 shrink-0 rounded-sm border border-black/10" style={{ backgroundColor: entry.color }} />
            <span className="break-words">{entry.label}</span>
          </li>
        )))}
      </ul>
    </section>
  )
}
