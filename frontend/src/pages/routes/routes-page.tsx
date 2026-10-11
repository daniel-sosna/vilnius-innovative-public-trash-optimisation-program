import { useEffect, useState } from 'react'
import {
  loadAvailablePlans,
  loadRoutePlan,
  truckColor,
  type AvailablePlan,
  type Figures,
  type RoutePlan,
} from './api'
import { RouteMap } from './route-map'

const COMMAND = 'docker compose exec backend uv run python -m app.interfaces.route_plan --carrier <vežėjas> --date <data>'

const number = (value: number, digits = 0) =>
  value.toLocaleString('lt-LT', { minimumFractionDigits: digits, maximumFractionDigits: digits })

const key = (plan: AvailablePlan) => `${plan.date}|${plan.waste_carrier}`

type Loaded =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; plans: AvailablePlan[] }

export function RoutesPage() {
  const [available, setAvailable] = useState<Loaded>({ status: 'loading' })
  const [chosen, setChosen] = useState<string | null>(null)
  const [plan, setPlan] = useState<{ key: string; value: RoutePlan } | 'error' | null>(null)
  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    loadAvailablePlans(controller.signal)
      .then((plans) => {
        setAvailable({ status: 'ready', plans })
        setChosen((current) => current ?? (plans[0] ? key(plans[0]) : null))
      })
      .catch(() => !controller.signal.aborted && setAvailable({ status: 'error' }))
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!chosen || available.status !== 'ready') return
    const target = available.plans.find((p) => key(p) === chosen)
    if (!target) return
    const controller = new AbortController()
    loadRoutePlan(target, controller.signal)
      .then((value) => {
        setPlan({ key: chosen, value })
        const first = value.trucks.findIndex((t) => t.trips.length > 0)
        setSelected(first >= 0 ? first : null)
      })
      .catch(() => !controller.signal.aborted && setPlan('error'))
    return () => controller.abort()
  }, [chosen, available])

  if (available.status === 'loading')
    return <p role="status" className="p-6 text-sm">Kraunami maršrutai…</p>
  if (available.status === 'error')
    return <p role="alert" className="p-6 text-sm text-destructive">Nepavyko įkelti maršrutų. Bandykite dar kartą.</p>
  if (available.plans.length === 0)
    return (
      <section className="mx-auto max-w-2xl p-6">
        <h1 className="mb-2 text-xl font-semibold">Maršrutai</h1>
        <p className="text-sm">Maršrutų planų dar nėra. Sukurkite planą komanda:</p>
        <pre className="mt-3 overflow-x-auto rounded-lg border bg-muted/40 p-3 text-xs">{COMMAND}</pre>
      </section>
    )

  const current = plan && plan !== 'error' && plan.key === chosen ? plan.value : null

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col md:flex-row">
      <aside className="w-full shrink-0 space-y-4 overflow-y-auto border-b bg-card p-4 md:w-96 md:border-b-0 md:border-r">
        <div>
          <label htmlFor="plan-select" className="mb-1 block text-sm font-medium">Maršrutų planas</label>
          <select
            id="plan-select"
            value={chosen ?? ''}
            onChange={(event) => { setPlan(null); setChosen(event.target.value) }}
            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
          >
            {available.plans.map((p) => (
              <option key={key(p)} value={key(p)}>{p.date} · {p.waste_carrier}</option>
            ))}
          </select>
        </div>
        {plan === 'error' && <p role="alert" className="text-sm text-destructive">Nepavyko įkelti plano.</p>}
        {!current && plan !== 'error' && <p role="status" className="text-sm">Kraunamas planas…</p>}
        {current && <PlanPanel plan={current} selected={selected} onSelect={setSelected} />}
      </aside>
      {current ? <RouteMap plan={current} selected={selected} /> : <div className="flex-1" />}
    </div>
  )
}

function Row({ label, a, b }: { label: string; a: string; b: string }) {
  return (
    <tr className="border-t">
      <th scope="row" className="py-1 pr-2 text-left font-normal">{label}</th>
      <td className="py-1 pr-2 text-right tabular-nums">{a}</td>
      <td className="py-1 text-right tabular-nums">{b}</td>
    </tr>
  )
}

function PlanPanel({ plan, selected, onSelect }: { plan: RoutePlan; selected: number | null; onSelect(index: number | null): void }) {
  const { summary } = plan
  const fig = (f: Figures) => ({
    km: number(f.distance_km, 1), trips: number(f.trips), trucks: number(f.trucks_used), ot: number(f.overtime_min),
  })
  const o = fig(summary.optimised)
  const b = fig(summary.baseline)
  const used = plan.trucks.map((t, index) => ({ t, index })).filter(({ t }) => t.trips.length > 0)
  const idle = plan.trucks.filter((t) => t.trips.length === 0)
  const truck = selected !== null ? plan.trucks[selected] : null
  const share = summary.stops_total ? (100 * summary.unserved_stops) / summary.stops_total : 0

  return (
    <>
      <section aria-labelledby="savings">
        <h2 id="savings" className="mb-1 text-sm font-semibold">Sutaupyta palyginus su paprastu planu</h2>
        <p className="mb-2 text-2xl font-semibold tabular-nums">
          {number(summary.saved_km, 1)} km <span className="text-base font-normal">({number(summary.saved_percent, 1)} %)</span>
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th className="text-left font-normal"><span className="sr-only">Rodiklis</span></th>
              <th className="text-right font-normal">Optimizuotas</th>
              <th className="text-right font-normal">Paprastas*</th>
            </tr>
          </thead>
          <tbody>
            <Row label="Atstumas, km" a={o.km} b={b.km} />
            <Row label="Reisai" a={o.trips} b={b.trips} />
            <Row label="Naudota šiukšliavežių" a={o.trucks} b={b.trucks} />
            <Row label="Viršvalandžiai, min" a={o.ot} b={b.ot} />
          </tbody>
        </table>
        <p className="mt-1 text-xs text-muted-foreground">
          *Artimiausio kaimyno planas tiems patiems sustojimams ir toms pačioms šiukšliavežėms. Taupymas rodomas kartu su viršvalandžiais.
        </p>
      </section>

      <section aria-labelledby="warnings" className="space-y-1 text-sm">
        <h2 id="warnings" className="sr-only">Pastabos</h2>
        <p>Aptarnauta sustojimų: {number(summary.optimised.stops_served)} iš {number(summary.stops_total)}.</p>
        {plan.unserved.length > 0 && (
          <div role="status" className="rounded-md border border-destructive/40 p-2">
            <p className="font-medium">Neaptarnauta sustojimų: {plan.unserved.length} ({number(share, 1)} %)</p>
            <ul className="mt-1 list-disc pl-5 text-xs">
              {plan.unserved.map((s) => (
                <li key={s.site_id}>{s.address ?? `Vieta ${s.site_id}`}: krūvis {number(s.load_m3, 1)} m³ viršija kiekvienos šiukšliavežės talpą</li>
              ))}
            </ul>
          </div>
        )}
        {plan.excluded_trucks > 0 && <p>Neįtrauktų šiukšliavežių (be sąvartyno): {plan.excluded_trucks}.</p>}
      </section>

      <section aria-labelledby="trucks">
        <h2 id="trucks" className="mb-1 text-sm font-semibold">Šiukšliavežės ({used.length})</h2>
        <ul className="space-y-1">
          {used.map(({ t, index }) => (
            <li key={t.truck_id}>
              <button
                type="button"
                onClick={() => onSelect(selected === index ? null : index)}
                aria-pressed={selected === index}
                className={`flex w-full items-center gap-2 rounded-md border px-2 py-1 text-left text-sm focus-visible:outline-2 focus-visible:outline-ring ${selected === index ? 'bg-muted' : ''}`}
              >
                <span aria-hidden="true" className="size-3 shrink-0 rounded-full" style={{ background: truckColor(index) }} />
                <span className="min-w-0 flex-1 truncate">{t.name}</span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {t.trips.length} reis. · {number(t.trips.reduce((sum, trip) => sum + trip.distance_km, 0), 0)} km
                </span>
              </button>
            </li>
          ))}
        </ul>
        {idle.length > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            Nenaudojamos šiukšliavežės ({idle.length}): {idle.map((t) => t.name).join(', ')}
          </p>
        )}
      </section>

      {truck && (
        <section aria-labelledby="trips">
          <h2 id="trips" className="mb-1 text-sm font-semibold">{truck.name} · {truck.landfill.name} · {number(truck.max_volume_m3, 1)} m³</h2>
          <ol className="space-y-1 text-sm">
            {truck.trips.map((trip, i) => (
              <li key={i} className="rounded-md border px-2 py-1">
                <span className="font-medium">Reisas {i + 1}</span>: {trip.stops.length} sust., {number(trip.load_m3, 1)} m³,
                {' '}{number(trip.distance_km, 1)} km, {number(trip.duration_min)} min
              </li>
            ))}
          </ol>
        </section>
      )}

      <p className="text-xs text-muted-foreground">
        Kiekiai prognozuoti pagal sintetinius istorinius duomenis. Atstumai yra įvertis pagal tiesią liniją, todėl maršrutai žemėlapyje rodomi tiesiomis linijomis.
      </p>
    </>
  )
}
