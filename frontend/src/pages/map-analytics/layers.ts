import type { MapLayerDefinition, LayerSelection } from '@/components/maps/map-layer'
import { landfillsLayer } from './landfills'
import { binsLayer } from './bins'

export const mapLayers: readonly MapLayerDefinition[] = [landfillsLayer, binsLayer]

export function getActiveLayers(selection: LayerSelection) {
  return mapLayers.filter(layer => selection[layer.id])
}
