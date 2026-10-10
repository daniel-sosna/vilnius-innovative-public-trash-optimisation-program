import type { MapLayerDefinition, LayerSelection } from '@/components/maps/map-layer'
import { landfillsLayer } from './landfills'

export const mapLayers: readonly MapLayerDefinition[] = [landfillsLayer]

export function getActiveLayers(selection: LayerSelection) {
  return mapLayers.filter(layer => selection[layer.id])
}
