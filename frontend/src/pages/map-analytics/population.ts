import type { Feature, Polygon } from 'geojson'
import type { ExpressionSpecification, FilterSpecification } from 'maplibre-gl'
import { createPolygonLayer } from '@/components/maps/polygon-layer'
import { loadPopulation } from './api'
import type { PopulationProperties } from './api'

export const populationBands = [
  { minimum: 0, label: '<11', color: '#f2e5ff' },
  { minimum: 11, label: '11–49', color: '#dac2ef' },
  { minimum: 50, label: '50–99', color: '#b88bd9' },
  { minimum: 100, label: '100–199', color: '#8d50b6' },
  { minimum: 200, label: '200+', color: '#602080' },
] as const

const knownDensity: FilterSpecification = ['any',
  ['==', ['get', 'suppressed'], true],
  ['==', ['typeof', ['get', 'density_per_ha']], 'number'],
]
const densityColor: ExpressionSpecification = ['case',
  ['==', ['get', 'suppressed'], true], populationBands[0].color,
  ['step', ['number', ['get', 'density_per_ha'], 0], populationBands[0].color,
    ...populationBands.slice(1).flatMap(band => [band.minimum, band.color])],
]

const densityFormat = new Intl.NumberFormat('lt-LT')
const areaFormat = new Intl.NumberFormat('lt-LT', { maximumFractionDigits: 2 })
const residentFormat = new Intl.NumberFormat('lt-LT', { maximumFractionDigits: 1 })

export function populationDetails(feature: Feature<Polygon, PopulationProperties>): HTMLElement {
  const { density_per_ha: density, suppressed, area_ha: area, residents } = feature.properties
  const content = document.createElement('div')
  content.className = 'analytics-details'
  const heading = document.createElement('h2')
  heading.className = 'mb-3 pr-4 text-sm font-semibold'
  heading.textContent = 'Gyventojų tankumas'
  content.append(heading)
  const details = document.createElement('dl')
  details.className = 'space-y-2 text-sm'
  const fields = [
    ['Tankumas (gyv./ha)', suppressed ? '<11' : density === null ? 'N/A' : densityFormat.format(density)],
    ['Plotas (ha)', areaFormat.format(area)],
    ['Apytikslis gyventojų skaičius', residents === null ? 'N/A' : residentFormat.format(residents)],
  ] as const
  for (const [label, value] of fields) {
    const group = document.createElement('div')
    const term = document.createElement('dt')
    term.className = 'font-medium text-muted-foreground'
    term.textContent = label
    const description = document.createElement('dd')
    description.textContent = value
    group.append(term, description)
    details.append(group)
  }
  content.append(details)
  if (suppressed) {
    const assumption = document.createElement('p')
    assumption.className = 'mt-3 text-xs text-muted-foreground'
    assumption.textContent = area > 0 && residents !== null
      ? `Skaičiavimui taikyta: ${areaFormat.format(residents / area)} gyv./ha.`
      : 'Gyventojų skaičius apskaičiuotas taikant prielaidą; kai plotas lygus nuliui, taikytas tankumas nenurodomas.'
    content.append(assumption)
  }
  const explanation = document.createElement('p')
  explanation.className = 'mt-3 text-xs text-muted-foreground'
  explanation.textContent = 'Pagal deklaruotą gyvenamąją vietą. Gyventojų skaičius yra įvertis.'
  content.append(explanation)
  return content
}

export const populationLayer = createPolygonLayer<PopulationProperties>({
  id: 'population',
  label: 'Gyventojų tankumas',
  meaning: 'Gyventojų tankumas pagal deklaruotą gyvenamąją vietą šaltinio poligonuose; gyventojų skaičius yra įvertis.',
  order: 20,
  legend: [
    ...populationBands.map(band => ({ label: `Gyventojų tankumas: ${band.label} gyv./ha`, color: band.color })),
    { label: 'Gyventojų tankumas: Duomenų nėra (skaidru)', color: 'transparent' },
  ],
  load: loadPopulation,
  filter: knownDensity,
  fill: { 'fill-color': densityColor, 'fill-opacity': 0.45 },
  outline: { 'line-color': '#602080', 'line-opacity': 0.2, 'line-width': 0.5 },
  interaction: {
    details: populationDetails,
    canInspect: feature => feature.properties.density_per_ha !== null || feature.properties.suppressed,
  },
})
