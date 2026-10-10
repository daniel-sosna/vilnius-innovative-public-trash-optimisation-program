import type { MapLayerDefinition, LayerSelection } from '@/components/maps/map-layer'
import { landfillsLayer } from './landfills'
import { populationLayer } from './population'

export const mapLayers: readonly MapLayerDefinition[] = [landfillsLayer, populationLayer]

export function getActiveLayers(selection: LayerSelection) {
  return mapLayers.filter(layer => selection[layer.id])
}
