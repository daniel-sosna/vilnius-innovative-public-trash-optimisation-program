import { useMemo, useState } from 'react'
import type { FeatureCollection, Point } from 'geojson'
import type { BinProperties } from './api'
import { binCategories, binCategory, knownBinCategories } from './bin-categories'
import type { BinCategoryId } from './bin-categories'

const emptyBins: FeatureCollection<Point, BinProperties> = { type: 'FeatureCollection', features: [] }

export function useBinFilters(data: FeatureCollection<Point, BinProperties> | undefined) {
  const [categories, setCategories] = useState<Record<BinCategoryId, boolean>>({
    'paper-plastic': true, glass: true, mixed: true, other: true,
  })
  const index = useMemo(() => data?.features.map(feature => ({
    feature, category: binCategory(feature.properties.waste_type).id,
  })) ?? [], [data])
  const hasOther = useMemo(() => index.some(item => item.category === 'other'), [index])
  const availableCategories = hasOther ? binCategories : knownBinCategories
  const filteredData = useMemo(() => {
    if (!data) return undefined
    if (binCategories.every(category => categories[category.id])) return data
    const features = index.filter(item => categories[item.category]).map(item => item.feature)
    if (features.length === data.features.length) return data
    return features.length ? { type: 'FeatureCollection' as const, features } : emptyBins
  }, [data, index, categories])

  function toggleCategory(id: BinCategoryId, selected: boolean) {
    setCategories(previous => ({ ...previous, [id]: selected }))
  }

  return {
    categories, availableCategories, filteredData, toggleCategory,
    noneSelected: availableCategories.every(category => !categories[category.id]),
  }
}
