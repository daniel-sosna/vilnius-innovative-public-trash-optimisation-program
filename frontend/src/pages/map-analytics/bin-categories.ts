import type { DataDrivenPropertyValueSpecification } from 'maplibre-gl'

export const binCategories = [
  { id: 'paper-plastic', source: 'Paper/plastic waste', label: 'Popieriaus ir plastiko atliekos', color: '#2563eb' },
  { id: 'glass', source: 'Glass waste', label: 'Stiklo atliekos', color: '#15803d' },
  { id: 'mixed', source: 'Mixed municipal waste', label: 'Mišrios komunalinės atliekos', color: '#92400e' },
  { id: 'other', source: null, label: 'Kitos atliekų rūšys', color: '#6b7280' },
] as const

export type BinCategoryId = typeof binCategories[number]['id']

const fallbackCategory = binCategories[3]
export const knownBinCategories = binCategories.filter(category => category.source !== null)

export function binCategory(wasteType: string) {
  return knownBinCategories.find(category => category.source === wasteType) ?? fallbackCategory
}

export const binPointColor: DataDrivenPropertyValueSpecification<string> = [
  'match', ['get', 'waste_type'],
  knownBinCategories[0].source, knownBinCategories[0].color,
  ...knownBinCategories.slice(1).flatMap(category => [category.source, category.color]),
  fallbackCategory.color,
]

export const binGroupColor = '#64748b'
export const binLegend = [
  ...binCategories.map(({ label, color }) => ({ label, color })),
  { label: 'Konteinerių grupė', color: binGroupColor },
]
