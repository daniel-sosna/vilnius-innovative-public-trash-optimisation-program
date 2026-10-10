import type { Feature, Point } from 'geojson'
import { createPointLayer } from '@/components/maps/point-layer'
import { loadBins } from './api'
import type { BinProperties } from './api'
import { binCategory, binGroupColor, binLegend, binPointColor } from './bin-categories'

export function binDetails(feature: Feature<Point, BinProperties>): HTMLElement {
  const content = document.createElement('div')
  content.className = 'analytics-details'
  const details = document.createElement('dl')
  details.className = 'space-y-2 pr-4 text-sm'
  const fields = [
    ['Inventorinis numeris', feature.properties.inventory_number],
    ['Atliekų rūšis', binCategory(feature.properties.waste_type).label],
    ['Talpa (m³)', feature.properties.capacity_m3],
  ] as const
  for (const [label, value] of fields) {
    const group = document.createElement('div')
    const term = document.createElement('dt')
    term.className = 'font-medium text-muted-foreground'
    term.textContent = label
    const description = document.createElement('dd')
    description.textContent = value === null ? 'N/A' : String(value)
    group.append(term, description)
    details.append(group)
  }
  content.append(details)
  return content
}

export function binGroupDetails(features: Feature<Point, BinProperties>[], isCurrent: () => boolean): HTMLElement {
  const content = document.createElement('div')
  const heading = document.createElement('h2')
  heading.className = 'mb-3 pr-4 text-sm font-semibold'
  heading.textContent = `Konteineriai (${features.length})`
  const list = document.createElement('ul')
  list.className = 'analytics-group-list'
  for (const feature of features) {
    const item = document.createElement('li')
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'analytics-group-button'
    const inventory = document.createElement('span')
    inventory.className = 'block font-medium'
    inventory.textContent = feature.properties.inventory_number ?? 'N/A'
    const waste = document.createElement('span')
    waste.className = 'block text-xs text-muted-foreground'
    waste.textContent = binCategory(feature.properties.waste_type).label
    button.append(inventory, waste)
    button.addEventListener('click', () => {
      if (!isCurrent()) return
      const details = binDetails(feature)
      const back = document.createElement('button')
      back.type = 'button'
      back.className = 'analytics-group-button mt-3'
      back.textContent = 'Atgal į sąrašą'
      back.addEventListener('click', () => {
        if (!isCurrent()) return
        content.replaceChildren(heading, list)
        button.focus()
      })
      content.replaceChildren(details, back)
      back.focus()
    })
    item.append(button)
    list.append(item)
  }
  content.append(heading, list)
  // The point helper focuses the first list button after the asynchronous read.
  return content
}

export const binsLayer = createPointLayer({
  id: 'bins',
  label: 'Konteineriai',
  meaning: 'Registruoti konteineriai, jų atliekų rūšys ir užfiksuotos koordinatės.',
  legend: binLegend,
  load: loadBins,
  appearance: { color: binPointColor, clusterColor: binGroupColor },
  details: binDetails,
  clustering: { radius: 20, throughMaxZoom: true, avoidOverlap: true },
  overlapGroup: { minZoom: 15, details: binGroupDetails },
})
