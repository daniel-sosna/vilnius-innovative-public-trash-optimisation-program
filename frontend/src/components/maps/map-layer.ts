import type { FeatureCollection } from 'geojson'
import type { Map } from 'maplibre-gl'

export type LayerData = FeatureCollection

export type LayerLegendEntry = {
  label: string
  color: string
}

export type LayerRenderer = {
  styleLayerIds?: readonly string[]
  setVisible(visible: boolean): void
  setData?(data: LayerData): void
  dispose(): void
}

export type LayerContext = {
  map: Map
  showDetails(layerId: string, coordinates: [number, number], content: HTMLElement, onClose?: () => void): void
  closeDetails(layerId: string): void
}

// Geometry is deliberately unconstrained here. Only the point helper clusters.
export type MapLayerDefinition = {
  id: string
  label: string
  meaning: string
  kind: string
  polygonOrder?: number
  polygonOutlineOrder?: number
  legend: readonly LayerLegendEntry[]
  load(signal: AbortSignal): Promise<LayerData>
  attach(context: LayerContext, data: LayerData): LayerRenderer
}

export type LayerLoadState =
  | { status: 'idle' | 'loading' | 'error' }
  | { status: 'ready'; data: LayerData }

export type LayerSelection = Record<string, boolean>
export type LayerStates = Record<string, LayerLoadState>
