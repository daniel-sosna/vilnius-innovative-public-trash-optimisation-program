import type { ExpressionSpecification } from 'maplibre-gl'
import { createPolygonLayer } from '@/components/maps/polygon-layer'
import { loadDistricts } from './api'
import type { DistrictProperties } from './api'

// Identity colors for the supplied snapshot, independent of ordering and IDs.
// Review this mapping deliberately when the imported set of names changes.
export const districtColors = {
  'Naujininkai': '#f97316',
  'Paneriai': '#16a34a',
  'Lazdynai': '#3b82f6',
  'Grigiškės': '#ec4899',
  'Vilkpėdė': '#eab308',
  'Senamiestis': '#8b5cf6',
  'Naujamiestis': '#dc2626',
  'Rasos': '#06b6d4',
  'Karoliniškės': '#fb923c',
  'Žvėrynas': '#0ea5e9',
  'Šnipiškės': '#facc15',
  'Viršuliškės': '#a855f7',
  'Naujoji Vilnia': '#65a30d',
  'Šeškinė': '#f43f5e',
  'Justiniškės': '#14b8a6',
  'Pilaitė': '#d946ef',
  'Žirmūnai': '#6366f1',
  'Fabijoniškės': '#d97706',
  'Pašilaičiai': '#84cc16',
  'Antakalnis': '#2563eb',
  'Verkiai': '#0891b2',
} as const

const districtColor: ExpressionSpecification = ['match', ['get', 'district_name'],
  'Naujininkai', districtColors.Naujininkai,
  ...Object.entries(districtColors).filter(([name]) => name !== 'Naujininkai')
    .flatMap(([name, color]) => [name, color]), '#777777']

export const districtsLayer = createPolygonLayer<DistrictProperties>({
  id: 'districts',
  label: 'Seniūnijos',
  meaning: 'Importuotos Vilniaus seniūnijų ribos ir pavadinimai; geografinis kontekstas.',
  order: 10,
  legend: [],
  load: loadDistricts,
  fill: { 'fill-color': districtColor, 'fill-opacity': 0.32 },
  outline: { 'line-color': districtColor, 'line-opacity': 1, 'line-width': 1.8 },
})
