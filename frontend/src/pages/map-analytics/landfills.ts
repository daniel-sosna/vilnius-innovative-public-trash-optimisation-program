import type { Feature, Point } from 'geojson'
import { createPointLayer } from '@/components/maps/point-layer'
import { loadLandfills } from './api'
import type { LandfillProperties } from './api'

const presentation: Record<string, string> = {
  'Ecoservice Gariūnų waste reception and sorting site': 'Ecoservice Gariūnų atliekų priėmimo ir rūšiavimo aikštelė',
  'Ekobazė Lentvario waste treatment site': 'Ekobazės Lentvario atliekų tvarkymo aikštelė',
  'Vilnius regional mechanical-biological treatment facility (MBA)': 'Vilniaus regiono mechaninio biologinio atliekų apdorojimo įrenginiai (MBA)',
  'VAATC facility; current operating arrangements require confirmation': 'VAATC įrenginiai; dabartinę veiklos tvarką reikia patvirtinti',
  'Gariūnų g. 71, Vilnius, Lithuania': 'Gariūnų g. 71, Vilnius, Lietuva',
  'Lentvario g. 13A, Vilnius, Lithuania': 'Lentvario g. 13A, Vilnius, Lietuva',
  'Jočionių g. 13, Vilnius, Lithuania': 'Jočionių g. 13, Vilnius, Lietuva',
}

export function landfillDetails(feature: Feature<Point, LandfillProperties>): HTMLElement {
  const content = document.createElement('div')
  content.className = 'analytics-details'
  const heading = document.createElement('h2')
  heading.className = 'mb-3 pr-4 text-sm font-semibold'
  heading.textContent = presentation[feature.properties.name] ?? feature.properties.name
  content.append(heading)
  const details = document.createElement('dl')
  details.className = 'space-y-2 text-sm'
  const fields = [
    ['Operatorius', feature.properties.operator],
    ['Adresas', feature.properties.address],
  ] as const
  for (const [label, value] of fields) {
    const group = document.createElement('div')
    const term = document.createElement('dt')
    term.className = 'font-medium text-muted-foreground'
    term.textContent = label
    const description = document.createElement('dd')
    description.textContent = value === null ? 'N/A' : presentation[value] ?? value
    group.append(term, description)
    details.append(group)
  }
  content.append(details)
  return content
}

const landfillColor = '#000000'

export const landfillsLayer = createPointLayer({
  id: 'landfills',
  label: 'Sąvartynai',
  meaning: 'Registruotos atliekų priėmimo ir tvarkymo vietos bei jų užfiksuotos koordinatės.',
  legend: [{ label: 'Sąvartynai', color: landfillColor }],
  load: loadLandfills,
  appearance: { color: landfillColor },
  details: landfillDetails,
})
