import type { MapLayerDefinition, LayerSelection } from '@/components/maps/map-layer'
import { landfillsLayer } from './landfills'
import { populationLayer } from './population'
import { binsLayer } from './bins'
import { serviceZonesLayer } from './service-zones'

export const mapLayers: readonly MapLayerDefinition[] = [landfillsLayer, binsLayer, populationLayer, serviceZonesLayer]

export function getActiveLayers(selection: LayerSelection) {
  return mapLayers.filter(layer => selection[layer.id])
}
