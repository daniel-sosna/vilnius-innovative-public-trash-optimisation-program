import type { Feature, FeatureCollection, Polygon } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import { createPolygonLayer } from '@/components/maps/polygon-layer'

export const adequacyWasteTypes = [
  { value: 'Mixed municipal waste', label: 'Mišrios komunalinės atliekos' },
  { value: 'Paper/plastic waste', label: 'Popieriaus ir plastiko atliekos' },
  { value: 'Glass waste', label: 'Stiklo atliekos' },
] as const
const monthFormat = new Intl.DateTimeFormat('lt-LT', { year: 'numeric', month: 'long', timeZone: 'UTC' })
export const adequacyPeriodLabel = (entry: Pick<AdequacyEntry, 'period_start' | 'period_end' | 'complete'>) =>
  `${entry.period_start} – ${entry.period_end} (${entry.complete ? 'visas mėnuo' : 'dalinis mėnuo'})`
export const adequacyMonthLabel = (month: string) => monthFormat.format(new Date(`${month}-01T00:00:00Z`))
export const adequacyCategories = {
  priority_shortage: { label: 'Didelė rizika', color: '#dc2626', conclusion: 'Patikrinkite talpą ir surinkimo dažnį.' },
  potential_shortage: { label: 'Galima stoka', color: '#d97706', conclusion: 'Patikrinkite talpą arba pasiekiamumą.' },
  overflow_without_pressure: { label: 'Dažnas 4 lygis', color: '#7c3aed', conclusion: 'Patikrinkite surinkimo dažnį.' },
  ordinary: { label: 'Įprasta', color: '#6b9278', conclusion: 'Padidėjusių signalų nenustatyta.' },
  insufficient_evidence: { label: 'Mažai vertinimų', color: '#9ca3af', conclusion: 'Laikotarpio išvadai trūksta vertinimų.' },
  unavailable: { label: 'Nėra įverčio', color: '#d1d5db', conclusion: 'Patikrinkite aptarnavimo duomenis.' },
} as const
export type AdequacyCategory = keyof typeof adequacyCategories
export type AdequacyEntry = {
  id: string; month: string; period_start: string; period_end: string; complete: boolean
  revision: string; schema_version: string; method_version: string; fill_provenance: 'synthetic' | 'observed'
}
export type AdequacyMetadata = Omit<AdequacyEntry, 'revision'> & {
  policy: { pressure_quantile: number; access_distance_m: number; excess_rate: number; min_assessments: number; min_assessed_days: number; min_bin_coverage: number; exceedance_probability: number }
  pressure_thresholds: Record<string, number | null>
  priors: Record<string, { mean: number } | null>
}
export type AdequacyProperties = {
  population_cell_id: number; waste_type: string; category: AdequacyCategory; reasons: string[]
  residents: number | null; attributed_capacity_m3: number | null; point_id: number | null
  point_capacity_m3: number | null; point_residents: number | null; point_bin_count: number
  pressure: number | null; distance_m: number | null; suppressed: boolean; population_known: boolean
  high_pressure: boolean; long_access: boolean; assessments: number; level4_count: number
  assessed_days: number; assessed_bins: number; bin_coverage: number
  raw_frequency: number | null; smoothed_frequency: number | null; interval_low: number | null
  interval_high: number | null; exceedance_probability: number | null; sufficient_evidence: boolean
}
export type AdequacyData = FeatureCollection<Polygon, AdequacyProperties> & { analysis: AdequacyMetadata }

export async function loadAdequacy(entry: AdequacyEntry, signal: AbortSignal): Promise<AdequacyData> {
  const response = await fetch(`/api/map-analytics/adequacy-analyses/${encodeURIComponent(entry.id)}?revision=${entry.revision}`, { signal, cache: 'no-store' })
  if (!response.ok) throw new Error('Adequacy read failed')
  const data = await response.json() as AdequacyData
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features) || data.analysis?.id !== entry.id
    || data.analysis.schema_version !== entry.schema_version || data.analysis.method_version !== entry.method_version
    || data.analysis.complete !== entry.complete || data.analysis.period_start !== entry.period_start
    || data.analysis.period_end !== entry.period_end) throw new Error('Invalid adequacy result')
  const tag = response.headers.get('ETag')
  if (tag && tag !== `"${entry.revision}"`) throw new Error('Artifact changed; refresh catalog')
  return data
}

const numeric = new Intl.NumberFormat('lt-LT', { maximumFractionDigits: 1 })
const percent = new Intl.NumberFormat('lt-LT', { style: 'percent', maximumFractionDigits: 1 })
const n = (value: number | null) => value === null ? 'N/A' : numeric.format(value)
const pct = (value: number | null) => value === null ? 'N/A' : percent.format(value)

export function adequacyDetails(feature: Feature<Polygon, AdequacyProperties>, collection: FeatureCollection): HTMLElement {
  const p = feature.properties
  const meta = (collection as AdequacyData).analysis
  const category = adequacyCategories[p.category]
  const content = document.createElement('div')
  content.className = 'analytics-details w-56 max-w-full'
  const heading = document.createElement('h2')
  heading.className = 'mb-3 pr-4 text-sm font-semibold'
  heading.textContent = category.label
  content.append(heading)
  const dl = document.createElement('dl')
  dl.className = 'space-y-1 text-xs'
  const fields = [
    ['Laikotarpis', adequacyPeriodLabel(meta)],
    ['Atliekos', adequacyWasteTypes.find(w => w.value === p.waste_type)?.label ?? p.waste_type],
    ['Gyventojai (apytiksliai)', n(p.residents)],
    ['Vietos konteineriai', p.point_id === null ? 'N/A' : `${p.point_bin_count}`],
    ['Apkrova / riba (gyv./m³)', `${n(p.pressure)} / ${n(meta.pressure_thresholds[p.waste_type])}`],
    ['Atstumas tiesiai (m)', n(p.distance_m)],
    ['4 lygis / vertinimai', `${p.level4_count} / ${p.assessments} (${pct(p.raw_frequency)})`],
  ]
  for (const [label, value] of fields) {
    const group = document.createElement('div'), term = document.createElement('dt'), description = document.createElement('dd')
    group.className = 'flex items-baseline justify-between gap-3'
    term.className = 'font-medium text-muted-foreground'
    description.className = 'text-right'
    term.textContent = label; description.textContent = value
    group.append(term, description); dl.append(group)
  }
  content.append(dl)
  const notes = [p.reasons.includes('no_serving_point') ? 'Nėra aptarnaujančios vietos.' : category.conclusion]
  for (const note of notes) {
    const paragraph = document.createElement('p')
    paragraph.className = 'mt-3 text-xs text-muted-foreground'; paragraph.textContent = note; content.append(paragraph)
  }
  return content
}

const colors: ExpressionSpecification = ['match', ['get', 'category'],
  'priority_shortage', adequacyCategories.priority_shortage.color,
  'potential_shortage', adequacyCategories.potential_shortage.color,
  'overflow_without_pressure', adequacyCategories.overflow_without_pressure.color,
  'ordinary', adequacyCategories.ordinary.color,
  'insufficient_evidence', adequacyCategories.insufficient_evidence.color,
  adequacyCategories.unavailable.color]
export const adequacyLayer = createPolygonLayer<AdequacyProperties>({
  id: 'adequacy', label: 'Konteinerių pakankamumas', order: 25,
  meaning: 'Gyventojų, talpos ir pasirinkto laikotarpio 4 lygio vertinimų analizė.',
  legend: [...Object.values(adequacyCategories).map(c => ({ label: `Pakankamumas: ${c.label}`, color: c.color })),
    { label: 'Pakankamumas: gyventojų duomenų nėra (skaidru)', color: 'transparent' }],
  load: async () => { throw new Error('Select a saved analysis') },
  filter: ['all', ['==', ['get', 'population_known'], true], ['>', ['get', 'residents'], 0]],
  fill: { 'fill-color': colors, 'fill-opacity': .60 },
  outline: { 'line-color': colors, 'line-opacity': .55, 'line-width': .5 },
  interaction: { details: adequacyDetails },
})
